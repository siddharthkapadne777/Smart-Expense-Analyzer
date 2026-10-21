from django.db import models
from django.contrib.auth.models import User


class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    date = models.DateField()
    merchant = models.CharField(max_length=255, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=100, db_index=True)
    is_anomaly = models.BooleanField(default=False)
    transaction_id = models.CharField(
        max_length=64, blank=True, default="", db_index=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['date', 'category']),
            models.Index(fields=['merchant']),
        ]

    def __str__(self):
        return f"{self.date} - {self.merchant} - ₹{self.amount}"


class CategoryBudget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True) # <-- YEH ADD KIYA HAI
    category = models.CharField(max_length=100)
    monthly_cap = models.DecimalField(max_digits=10, decimal_places=2)
    target_month = models.CharField(max_length=7, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Humne yahan se unique_together hata diya hai kyunki ab har user ka apna budget hoga
        pass

    def __str__(self):
        return f"{self.category}: ₹{self.monthly_cap} ({self.target_month})"


class MerchantCategory(models.Model):
    """
    Persistent categorization memory. Precedence:
      user  >  ai  >  rule
    Once a merchant is categorized (by any source), future uploads reuse it
    without re-invoking the LLM.
    """
    SOURCE_CHOICES = [
        ('rule', 'Rule Engine'),
        ('ai', 'AI'),
        ('user', 'User Override'),
    ]

    merchant = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=100)
    source = models.CharField(max_length=8, choices=SOURCE_CHOICES, default='ai')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['merchant'])]

    def __str__(self):
        return f"{self.merchant} → {self.category} ({self.source})"