from django.db import models

class Transaction(models.Model):
    date = models.DateField()
    merchant = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=100)
    is_anomaly = models.BooleanField(default=False)

    class Meta:
        # Prevents identical transactions from being duplicated
        unique_together = ('date', 'merchant', 'amount')

    def __str__(self):
        return f"{self.date} - {self.merchant} - ₹{self.amount}"


class CategoryBudget(models.Model):
    category = models.CharField(max_length=100)
    monthly_cap = models.DecimalField(max_digits=10, decimal_places=2)
    target_month = models.CharField(max_length=7, default="2026-09") # Format: YYYY-MM
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category}: ₹{self.monthly_cap} ({self.target_month})"