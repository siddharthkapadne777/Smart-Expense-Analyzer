from django.contrib import admin
from django.urls import path, include
from analytics_api.views import (
    UploadApiView, DashboardApiView, OptimizeBudgetApiView,
    UpdateTransactionCategoryApiView, BudgetHistoryApiView, 
    SpendingTrendApiView, DataMiningApiView # <-- Updated Import
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('api/auth/', include('djoser.urls')),
    path('api/auth/', include('djoser.urls.authtoken')),

    path('api/upload/', UploadApiView.as_view(), name='api-upload'),
    path('api/dashboard/', DashboardApiView.as_view(), name='api-dashboard'),
    path('api/optimize/', OptimizeBudgetApiView.as_view(), name='api-optimize'),
    path('api/transaction/<int:tx_id>/category/', UpdateTransactionCategoryApiView.as_view(), name='api-update-category'),
    path('api/budget-history/', BudgetHistoryApiView.as_view(), name='api-budget-history'),
    path('api/spending-trends/', SpendingTrendApiView.as_view(), name='api-spending-trends'),
    path('api/data-mining/', DataMiningApiView.as_view(), name='api-data-mining'), # <-- Updated Endpoint
]