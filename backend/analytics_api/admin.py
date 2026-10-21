from django.contrib import admin
from .models import Transaction, CategoryBudget, MerchantCategory

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'merchant', 'amount', 'category', 'is_anomaly')
    list_filter = ('category', 'is_anomaly', 'date')
    search_fields = ('merchant', 'category')

@admin.register(CategoryBudget)
class CategoryBudgetAdmin(admin.ModelAdmin):
    # This lets you see the Month, Category, and Cap at a glance
    list_display = ('target_month', 'category', 'monthly_cap', 'created_at')
    list_filter = ('target_month', 'category')
    search_fields = ('category',)

@admin.register(MerchantCategory)
class MerchantCategoryAdmin(admin.ModelAdmin):
    list_display = ('merchant', 'category', 'source')
    list_filter = ('source', 'category')
    search_fields = ('merchant',)