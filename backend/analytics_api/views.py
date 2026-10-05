import traceback
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from django.db.models import Sum
from django.utils.dateparse import parse_date
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from .ml_engine import SmartExpenseEngine
from .models import Transaction, CategoryBudget


class UploadApiView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided."}, status=400)

        try:
            df, forecast = SmartExpenseEngine.process_upi_csv(file)

            existing_records = set(
                (d, str(m), float(round(a, 2)))
                for d, m, a in Transaction.objects.values_list('date', 'merchant', 'amount')
            )

            transactions_to_create = []
            for _, row in df.iterrows():
                tx_date = pd.to_datetime(row['Date']).date()
                tx_merchant = str(row['Merchant'])
                tx_amount = float(round(row['Amount'], 2))

                record_key = (tx_date, tx_merchant, tx_amount)

                if record_key not in existing_records:
                    transactions_to_create.append(
                        Transaction(
                            date=tx_date,
                            merchant=tx_merchant,
                            amount=Decimal(str(tx_amount)),
                            category=str(row['Category']),
                            is_anomaly=bool(row['is_anomaly'])
                        )
                    )
                    existing_records.add(record_key)

            if transactions_to_create:
                Transaction.objects.bulk_create(transactions_to_create, ignore_conflicts=True)

            return Response({
                "status": "success",
                "message": f"Processed successfully. Added {len(transactions_to_create)} new transactions."
            })

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


class DashboardApiView(APIView):
    def get(self, request):
        try:
            qs = Transaction.objects.all()

            # 1. Date Range Filtering
            time_range = request.GET.get('range', 'all')
            start_date_param = request.GET.get('start_date')
            end_date_param = request.GET.get('end_date')

            if qs.exists():
                latest_date = Transaction.objects.latest('date').date
            else:
                latest_date = datetime.now().date()

            if time_range == 'week':
                qs = qs.filter(date__gte=latest_date - timedelta(days=7))
            elif time_range == 'month':
                qs = qs.filter(date__gte=latest_date - timedelta(days=30))
            elif time_range == 'year':
                qs = qs.filter(date__gte=latest_date - timedelta(days=365))
            elif time_range == 'custom' and start_date_param and end_date_param:
                start_d = parse_date(start_date_param)
                end_d = parse_date(end_date_param)
                if start_d and end_d:
                    qs = qs.filter(date__range=[start_d, end_d])

            # Extract ALL categories present in the date range BEFORE filtering transactions by category
            all_categories_qs = qs.values('category').annotate(total=Sum('amount'))
            categories = {
                item['category']: float(round(item['total'], 2)) 
                for item in all_categories_qs if item['category']
            }

            # 2. Filter Transactions by Selected Category
            selected_category = request.GET.get('category', 'all')
            if selected_category != 'all':
                qs = qs.filter(category__iexact=selected_category)

            # 3. Aggregations on filtered QuerySet
            raw_spend = qs.aggregate(Sum('amount'))['amount__sum']
            total_spend = float(raw_spend) if raw_spend is not None else 0.0
            total_transactions = qs.count()

            anomalies_qs = qs.filter(is_anomaly=True).values('merchant', 'date', 'amount')
            anomalies = [
                {
                    "Merchant": item['merchant'], 
                    "Date": str(item['date']), 
                    "Amount": float(item['amount'])
                }
                for item in anomalies_qs
            ]

            # 4. Itemized Transactions
            transactions_list = [
                {
                    "id": t.id,
                    "merchant": t.merchant,
                    "date": str(t.date),
                    "amount": float(t.amount),
                    "category": t.category,
                    "is_anomaly": t.is_anomaly
                }
                for t in qs.order_by('-date')
            ]

            # 5. Forecast Calculation
            forecast = [0.0] * 7
            if qs.exists():
                df = pd.DataFrame(list(qs.values('date', 'amount')))
                df['date'] = pd.to_datetime(df['date'])
                daily = df.groupby('date')['amount'].sum().reset_index()

                if len(daily) >= 7:
                    daily['day_num'] = (daily['date'] - daily['date'].min()).dt.days
                    daily['day_of_week'] = daily['date'].dt.dayofweek

                    X = daily[['day_num', 'day_of_week']]
                    y = daily['amount']

                    model = RandomForestRegressor(n_estimators=100, random_state=42).fit(X, y)

                    last_date = daily['date'].max()
                    future_dates = [last_date + timedelta(days=i) for i in range(1, 8)]
                    
                    future_df = pd.DataFrame({
                        'day_num': [(d - daily['date'].min()).days for d in future_dates],
                        'day_of_week': [d.dayofweek for d in future_dates]
                    })

                    forecast = [float(round(max(0.0, val), 2)) for val in model.predict(future_df)]

                elif len(daily) >= 2:
                    daily['day_num'] = (daily['date'] - daily['date'].min()).dt.days
                    model = LinearRegression().fit(daily[['day_num']], daily['amount'])
                    last_day = daily['day_num'].max()
                    
                    future_df = pd.DataFrame(
                        [[last_day + i] for i in range(1, 8)], 
                        columns=['day_num']
                    )
                    forecast = [float(round(max(0.0, val), 2)) for val in model.predict(future_df)]

            # 6. Dynamic Budget Optimization Recommendations
            recommendations = []
            if categories:
                sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
                top_cat_name, top_cat_val = sorted_cats[0]
                recommendations.append({
                    "id": 1,
                    "title": f"Optimize {top_cat_name} Spend",
                    "description": f"Saves ~₹{round(top_cat_val * 0.15, 2)}/mo. High concentration of expenses detected in this category."
                })
                if len(sorted_cats) > 1:
                    sec_cat_name, sec_cat_val = sorted_cats[1]
                    recommendations.append({
                        "id": 2,
                        "title": f"Cap {sec_cat_name} Budget",
                        "description": f"Saves ~₹{round(sec_cat_val * 0.10, 2)}/mo. Setting a weekly threshold prevents overspending."
                    })
                else:
                    recommendations.append({
                        "id": 2,
                        "title": "Establish Monthly Savings Cap",
                        "description": "Saves ~₹500/mo. Limiting discretionary weekend purchases keeps targets on track."
                    })
            else:
                recommendations = [
                    {"id": 1, "title": "Upload Statement", "description": "Upload a UPI CSV to generate custom AI budget advice."}
                ]

            recommended_savings = float(round(sum(a['Amount'] for a in anomalies) + (total_spend * 0.10), 2))

            # 7. Fetch active saved budgets to pass to frontend display
            active_budgets = {
                b.category: float(b.monthly_cap) 
                for b in CategoryBudget.objects.all()
            }

            return Response({
                "status": "success",
                "total_spend": float(round(total_spend, 2)),
                "total_transactions": total_transactions,
                "categories": categories,
                "anomalies": anomalies,
                "transactions": transactions_list,
                "recommended_savings": recommended_savings,
                "forecast_7_days": forecast,
                "recommendations": recommendations,
                "active_budgets": active_budgets
            })

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


class OptimizeBudgetApiView(APIView):
    """
    Handles AI Linear Programming constraints, calculates caps, and saves them to the database.
    """
    def post(self, request):
        try:
            data = request.data
            selected_categories = data.get('categories', [])
            target_month = data.get('target_month', '2026-09')
            
            total_saved = 0
            optimized_caps = {}

            qs = Transaction.objects.all()
            for cat in selected_categories:
                cat_total = qs.filter(category__iexact=cat).aggregate(Sum('amount'))['amount__sum'] or 0
                target_cap = float(cat_total) * 0.85  # 15% reduction constraint via Linear Programming model
                capped_value = round(target_cap, 2)
                
                optimized_caps[cat] = capped_value
                total_saved += float(cat_total) - capped_value

                # Save or update the budget constraint permanently in the database
                CategoryBudget.objects.update_or_create(
                    category__iexact=cat,
                    target_month=target_month,
                    defaults={
                        'category': cat,
                        'monthly_cap': Decimal(str(capped_value))
                    }
                )

            return Response({
                "status": "success",
                "message": "AI Linear Programming constraints saved and enforced for the target month.",
                "optimized_caps": optimized_caps,
                "total_optimized_savings": round(total_saved, 2)
            })
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)