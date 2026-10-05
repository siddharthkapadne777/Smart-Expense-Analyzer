from django.urls import path
from analytics_api.views import UploadApiView, DashboardApiView, OptimizeBudgetApiView

urlpatterns = [
    path('api/upload/', UploadApiView.as_view(), name='api-upload'),
    path('api/dashboard/', DashboardApiView.as_view(), name='api-dashboard'),
    path('api/optimize/', OptimizeBudgetApiView.as_view(), name='api-optimize'), # <--- Add this line
]