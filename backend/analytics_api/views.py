import traceback
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from django.db.models import Sum
from django.utils.dateparse import parse_date
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .ml_engine import SmartExpenseEngine
from .optimizer import optimize_budget_caps
from .data_mining import run_kmeans_pca, run_apriori
from .models import Transaction, CategoryBudget, MerchantCategory

class UploadApiView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided."}, status=400)

        try:
            df = SmartExpenseEngine.process_upi_csv(file)

            existing = set(
                (d, str(m), float(round(a, 2)), str(tid or ""))
                for d, m, a, tid in Transaction.objects.filter(user=request.user).values_list(
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
                    user=request.user,
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
            qs = Transaction.objects.filter(user=request.user)
            time_range = request.GET.get('range', 'all')
            start_date_param = request.GET.get('start_date')
            end_date_param = request.GET.get('end_date')

            if qs.exists():
                latest_date = qs.latest('date').date
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

            # ---- Forecast (Smooth Trend + Weekday Blend) ----
            forecast = [0.0] * 7
            forecast_dates = []
            if qs.exists():
                df = pd.DataFrame(list(qs.values('date', 'amount')))
                df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0).astype(float)
                df['date'] = pd.to_datetime(df['date'])
                daily = df.groupby('date')['amount'].sum().reset_index()
                n_days = len(daily)

                if n_days < 14:
                    # Not enough data, just use recent average
                    avg = float(daily['amount'].tail(7).mean()) if n_days > 0 else 0.0
                    forecast = [round(avg, 2)] * 7
                    last_date = daily['date'].max() if n_days > 0 else datetime.now()
                    forecast_dates = [
                        (last_date + timedelta(days=i)).strftime('%a, %b %d')
                        for i in range(1, 8)
                    ]
                else:
                    full_range = pd.date_range(daily['date'].min(), daily['date'].max(), freq='D')
                    daily = daily.set_index('date').reindex(full_range, fill_value=0.0).reset_index()
                    daily.columns = ['date', 'amount']
                    daily['amount'] = daily['amount'].astype(float)
                    daily['dow'] = daily['date'].dt.dayofweek

                    # 1. Use recent 7-day moving average to smooth spikes
                    recent_7d_avg = float(daily['amount'].tail(7).mean())
                    
                    # 2. Get weekday medians from last 28 days
                    recent = daily.tail(28)
                    dow_baseline = recent.groupby('dow')['amount'].median().to_dict()

                    last_date = daily['date'].max()
                    forecast = []
                    forecast_dates = []
                    
                    for i in range(1, 8):
                        fd = last_date + timedelta(days=i)
                        weekday_val = dow_baseline.get(fd.dayofweek, recent_7d_avg)
                        
                        # 3. Blend heavily towards recent average (70% avg, 30% weekday) 
                        # This prevents random massive spikes
                        predicted = (0.7 * recent_7d_avg) + (0.3 * weekday_val)
                        
                        forecast.append(float(round(max(0.0, predicted), 2)))
                        forecast_dates.append(fd.strftime('%a, %b %d'))

            # ---- Recommendations ----
            recommendations = []
            if categories:
                sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
                top_cat_name, top_cat_val = sorted_cats[0]
                recommendations.append({
                    "id": 1, "action": "optimize", "category": top_cat_name,
                    "title": f"Optimize {top_cat_name} Spend",
                    "description": f"Cap reduces {top_cat_name} by ~15% (₹{round(top_cat_val * 0.15, 2)}/mo potential savings).",
                })
                if len(sorted_cats) > 1:
                    sec_cat_name, sec_cat_val = sorted_cats[1]
                    recommendations.append({
                        "id": 2, "action": "cap", "category": sec_cat_name,
                        "title": f"Cap {sec_cat_name} Budget",
                        "description": f"Setting a cap on {sec_cat_name} saves ~₹{round(sec_cat_val * 0.10, 2)}/mo.",
                    })
                else:
                    recommendations.append({
                        "id": 2, "action": "cap", "category": None,
                        "title": "Establish Monthly Savings Cap",
                        "description": "Limiting discretionary weekend purchases keeps targets on track.",
                    })
            else:
                recommendations = [{
                    "id": 1, "action": "upload", "category": None,
                    "title": "Upload Statement",
                    "description": "Upload a UPI CSV to generate custom AI budget advice.",
                }]

            recommended_savings = float(round(sum(a['Amount'] for a in anomalies) + (total_spend * 0.10), 2))
            current_target_month = latest_date.strftime('%Y-%m')
            
            active_budgets = {
                b.category: float(b.monthly_cap)
                for b in CategoryBudget.objects.filter(user=request.user, target_month=current_target_month)
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
                "forecast_dates": forecast_dates,
                "recommendations": recommendations,
                "active_budgets": active_budgets,
                "target_month": current_target_month,
            })

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


class OptimizeBudgetApiView(APIView):
    def post(self, request):
        try:
            selected_categories = request.data.get('categories', [])
            if not selected_categories:
                return Response({"status": "error", "message": "No categories provided."}, status=400)

            qs = Transaction.objects.filter(user=request.user)
            if not qs.exists():
                return Response({"status": "error", "message": "No transactions to optimize."}, status=400)

            latest_date = qs.latest('date').date
            target_month = latest_date.strftime('%Y-%m')
            qs = qs.filter(date__gte=latest_date - timedelta(days=30))

            totals = {
                row['category'].strip().title(): float(row['total'])
                for row in qs.values('category').annotate(total=Sum('amount'))
                if row['category']
            }

            selected_norm = {
                str(c).strip().title(): totals.get(str(c).strip().title(), 0.0)
                for c in selected_categories if c
            }

            if not selected_norm or all(v == 0 for v in selected_norm.values()):
                return Response({"status": "error", "message": "Selected categories have no spend in the last 30 days."}, status=400)

            optimized_caps = optimize_budget_caps(selected_norm)
            total_saved = sum(selected_norm[cat] - optimized_caps.get(cat, selected_norm[cat]) for cat in selected_norm)

            for cat, cap in optimized_caps.items():
                CategoryBudget.objects.update_or_create(
                    user=request.user,
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


class UpdateTransactionCategoryApiView(APIView):
    def post(self, request, tx_id=None):
        try:
            tx_id = tx_id or request.data.get('transaction_id')
            new_category = str(request.data.get('category', '')).strip().title()

            if not tx_id or not new_category:
                return Response({"status": "error", "message": "transaction_id and category required."}, status=400)

            try:
                tx = Transaction.objects.get(id=tx_id, user=request.user)
            except Transaction.DoesNotExist:
                return Response({"status": "error", "message": "Transaction not found."}, status=404)

            old_category = tx.category
            merchant = tx.merchant

            tx.category = new_category
            tx.save(update_fields=['category'])

            MerchantCategory.objects.update_or_create(
                merchant=merchant, defaults={'category': new_category, 'source': 'user'},
            )

            updated_count = Transaction.objects.filter(
                user=request.user, merchant=merchant
            ).exclude(id=tx_id).update(category=new_category)

            return Response({
                "status": "success",
                "message": f"Updated '{merchant}' to '{new_category}'. Also fixed {updated_count} other transactions.",
                "transaction_id": tx_id, "old_category": old_category,
                "new_category": new_category, "retroactive_updates": updated_count,
            })

        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


class BudgetHistoryApiView(APIView):
    def get(self, request):
        try:
            budgets = CategoryBudget.objects.filter(user=request.user).order_by('-target_month', 'category')
            history = []

            # SYSTEM DATE ki jagah, USER ke latest uploaded transaction ka month nikal rahe hain
            latest_tx = Transaction.objects.filter(user=request.user).order_by('-date').first()
            if latest_tx:
                current_active_month = latest_tx.date.strftime('%Y-%m')
            else:
                current_active_month = datetime.now().strftime('%Y-%m')

            for b in budgets:
                year, month = b.target_month.split('-')
                
                actual_spend = Transaction.objects.filter(
                    user=request.user,
                    category=b.category,
                    date__year=int(year),
                    date__month=int(month)
                ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

                cap = b.monthly_cap
                difference = cap - actual_spend
                
                # LOGIC CHANGE: 
                # Agar target_month user ke LATEST data wale month ke barabar hai, 
                # toh usko "In Progress" maano.
                if b.target_month >= current_active_month:
                    status = "in_progress"
                    message = "Currently tracking"
                else:
                    status = "success" if actual_spend <= cap else "failed"
                    message = "Stayed under budget" if status == "success" else "Overspent"

                history.append({
                    "id": b.id,
                    "month": b.target_month,
                    "category": b.category,
                    "cap": float(cap),
                    "actual_spend": float(actual_spend),
                    "difference": float(abs(difference)),
                    "status": status,
                    "message": message
                })

            return Response({"status": "success", "history": history})
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


class SpendingTrendApiView(APIView):
    def get(self, request):
        try:
            granularity = request.GET.get('granularity', 'month')
            qs = Transaction.objects.filter(user=request.user)

            if not qs.exists():
                return Response({"status": "success", "labels": [], "data": []})

            df = pd.DataFrame(list(qs.values('date', 'amount')))
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0).astype(float)
            df['date'] = pd.to_datetime(df['date'])

            if granularity == 'day':
                grouped = df.groupby(df['date'].dt.strftime('%Y-%m-%d'))['amount'].sum()
                labels = grouped.index.tolist()
                data = grouped.values.tolist()
            elif granularity == 'year':
                grouped = df.groupby(df['date'].dt.strftime('%Y'))['amount'].sum()
                labels = grouped.index.tolist()
                data = grouped.values.tolist()
            else:
                grouped = df.groupby(df['date'].dt.strftime('%b %Y'))['amount'].sum()
                sorted_dates = pd.to_datetime(grouped.index, format='%b %Y').argsort()
                labels = grouped.index[sorted_dates].tolist()
                data = grouped.values[sorted_dates].tolist()

            data = [round(float(v), 2) for v in data]

            return Response({"status": "success", "labels": labels, "data": data})
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


# ==========================================
# NEW: DATA MINING (K-MEANS, PCA, APRIORI)
# ==========================================
class DataMiningApiView(APIView):
    def get(self, request):
        try:
            qs = list(Transaction.objects.filter(user=request.user))
            
            scatter_data = run_kmeans_pca(qs)
            apriori_insights = run_apriori(qs)

            return Response({
                "status": "success", 
                "scatter_data": scatter_data,
                "apriori_insights": apriori_insights
            })
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)