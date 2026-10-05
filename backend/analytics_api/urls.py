from django.urls import path
from .views import DashboardApiView, UploadApiView

urlpatterns = [
    path('dashboard/', DashboardApiView.as_view(), name='dashboard'),
    path('upload/', UploadApiView.as_view(), name='upload'),
]