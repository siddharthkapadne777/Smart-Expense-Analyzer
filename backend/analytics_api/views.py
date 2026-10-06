import traceback
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from django.db.models import Sum
from django.utils.dateparse import parse_date
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from sklearn.linear_model import LinearRegression

from .ml_engine import SmartExpenseEngine
from .models import Transaction, CategoryBudget
from .optimizer import optimize_budget_caps


class UploadApiView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided."}, status=400)

        try:
            df = SmartExpenseEngine.process_upi_csv(file)

            # Dedup key includes transaction_id (bank ref) if available.
            existing = set(
                (d, str(m), float(round(a, 2)), str(tid or ""))
                for d, m, a, tid in Transaction.objects.values_list(
                    'date', 'merchant', 'amount', 'transaction_id'
                )
            )

            to_create = []
            for _, row in df.iterrows():
                tx_date = pd.to_datetime(row['Date']).date()
                tx_merchant = str(row['Merchant'])
                tx_amount = float(round(row['Amount'], 2))
                tx_txn_id = str(row.get('TransactionId', '') or '')

                key = (tx_date, tx_merchant, tx_amount, tx_txn_id)
                if key in existing:
                    continue

                to_create.append(Transaction(
                    date=tx_date,
                    merchant=tx_merchant,
                    amount=Decimal(str(tx_amount)),
                    category=str(row['Category']),
                    is_anomaly=bool(row['is_anomaly']),
                    transaction_id=tx_txn_id,
                ))
                existing.add(key)

            if to_create:
                Transaction.objects.bulk_create(to_create, ignore_conflicts=True)

            return Response({
                "status": "success",
                "message": f"Processed successfully. Added {len(to_create)} new transactions."
            })

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


class DashboardApiView(APIView):
    def get(self, request):
        try:
            qs = Transaction.objects.all()

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

            # Category totals before category filter
            categories = {
                item['category']: float(round(item['total'], 2))
                for item in qs.values('category').annotate(total=Sum('amount'))
                if item['category']
            }

            selected_category = request.GET.get('category', 'all')
            if selected_category != 'all':
                qs = qs.filter(category__iexact=selected_category)

            raw_spend = qs.aggregate(Sum('amount'))['amount__sum']
            total_spend = float(raw_spend) if raw_spend is not None else 0.0
            total_transactions = qs.count()

            anomalies = [
                {
                    "Merchant": item['merchant'],
                    "Date": str(item['date']),
                    "Amount": float(item['amount']),
                }
                for item in qs.filter(is_anomaly=True).values('merchant', 'date', 'amount')
            ]

            transactions_list = [
                {
                    "id": t.id,
                    "merchant": t.merchant,
                    "date": str(t.date),
                    "amount": float(t.amount),
                    "category": t.category,
                    "is_anomaly": t.is_anomaly,
                }
                for t in qs.order_by('-date')
            ]

            # ---- Forecast: LR with day-of-week dummies ----
            forecast = [0.0] * 7
            if qs.exists():
                df = pd.DataFrame(list(qs.values('date', 'amount')))
                df['date'] = pd.to_datetime(df['date'])
                daily = df.groupby('date')['amount'].sum().reset_index()

                if len(daily) >= 2:
                    daily['day_num'] = (daily['date'] - daily['date'].min()).dt.days
                    daily['dow'] = daily['date'].dt.dayofweek

                    dow_dummies = pd.get_dummies(daily['dow'], prefix='dow', drop_first=True)
                    X = pd.concat([daily[['day_num']], dow_dummies], axis=1)
                    y = daily['amount']

                    model = LinearRegression().fit(X, y)

                    last_date = daily['date'].max()
                    last_day_num = int(daily['day_num'].max())
                    future = []
                    for i in range(1, 8):
                        fd = last_date + timedelta(days=i)
                        row = {'day_num': last_day_num + i}
                        for col in dow_dummies.columns:
                            row[col] = 1 if col == f'dow_{fd.dayofweek}' else 0
                        future.append(row)
                    future_df = pd.DataFrame(future).reindex(columns=X.columns, fill_value=0)
                    forecast = [
                        float(round(max(0.0, v), 2))
                        for v in model.predict(future_df)
                    ]

            # ---- Recommendations with structured `category` field ----
            recommendations = []
            if categories:
                sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
                top_cat_name, top_cat_val = sorted_cats[0]
                recommendations.append({
                    "id": 1,
                    "action": "optimize",
                    "category": top_cat_name,
                    "title": f"Optimize {top_cat_name} Spend",
                    "description": (
                        f"Cap reduces {top_cat_name} by ~15% "
                        f"(₹{round(top_cat_val * 0.15, 2)}/mo potential savings)."
                    ),
                })
                if len(sorted_cats) > 1:
                    sec_cat_name, sec_cat_val = sorted_cats[1]
                    recommendations.append({
                        "id": 2,
                        "action": "cap",
                        "category": sec_cat_name,
                        "title": f"Cap {sec_cat_name} Budget",
                        "description": (
                            f"Setting a cap on {sec_cat_name} "
                            f"saves ~₹{round(sec_cat_val * 0.10, 2)}/mo."
                        ),
                    })
                else:
                    recommendations.append({
                        "id": 2,
                        "action": "cap",
                        "category": None,
                        "title": "Establish Monthly Savings Cap",
                        "description": "Limiting discretionary weekend purchases keeps targets on track.",
                    })
            else:
                recommendations = [{
                    "id": 1,
                    "action": "upload",
                    "category": None,
                    "title": "Upload Statement",
                    "description": "Upload a UPI CSV to generate custom AI budget advice.",
                }]

            recommended_savings = float(round(
                sum(a['Amount'] for a in anomalies) + (total_spend * 0.10), 2
            ))

            current_target_month = latest_date.strftime('%Y-%m')
            active_budgets = {
                b.category: float(b.monthly_cap)
                for b in CategoryBudget.objects.filter(target_month=current_target_month)
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
                "active_budgets": active_budgets,
                "target_month": current_target_month,
            })

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


class OptimizeBudgetApiView(APIView):
    """
    Real Linear Programming budget optimization via scipy.optimize.linprog.
    Target month is always derived from the DB — never trusted from frontend.
    """
    def post(self, request):
        try:
            selected_categories = request.data.get('categories', [])
            if not selected_categories:
                return Response(
                    {"status": "error", "message": "No categories provided."},
                    status=400,
                )

            qs = Transaction.objects.all()
            if not qs.exists():
                return Response(
                    {"status": "error", "message": "No transactions to optimize."},
                    status=400,
                )

            latest_date = Transaction.objects.latest('date').date
            target_month = latest_date.strftime('%Y-%m')

            # Only last 30 days → true monthly baseline
            qs = qs.filter(date__gte=latest_date - timedelta(days=30))

            # Single aggregation, no N+1
            totals = {
                row['category'].strip().title(): float(row['total'])
                for row in qs.values('category').annotate(total=Sum('amount'))
                if row['category']
            }

            # Restrict to what the user actually selected
            selected_norm = {
                str(c).strip().title(): totals.get(str(c).strip().title(), 0.0)
                for c in selected_categories if c
            }

            if not selected_norm or all(v == 0 for v in selected_norm.values()):
                return Response(
                    {
                        "status": "error",
                        "message": "Selected categories have no spend in the last 30 days.",
                    },
                    status=400,
                )

            # === Real LP solver ===
            optimized_caps = optimize_budget_caps(selected_norm)

            total_saved = sum(
                selected_norm[cat] - optimized_caps.get(cat, selected_norm[cat])
                for cat in selected_norm
            )

            # Persist. unique_together guarantees one row per (category, month).
            for cat, cap in optimized_caps.items():
                CategoryBudget.objects.update_or_create(
                    category=cat,
                    target_month=target_month,
                    defaults={'monthly_cap': Decimal(str(cap))},
                )

            return Response({
                "status": "success",
                "message": "Linear Programming constraints solved and saved for the target month.",
                "target_month": target_month,
                "optimized_caps": optimized_caps,
                "historical_spend": selected_norm,
                "total_optimized_savings": round(total_saved, 2),
            })

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)