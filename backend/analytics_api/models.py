from django.db import models


class Transaction(models.Model):
    date = models.DateField()
    merchant = models.CharField(max_length=255, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=100, db_index=True)
    is_anomaly = models.BooleanField(default=False)

    # Bank reference / UTR number when available. If present, used as the
    # primary deduplication key. If blank, we fall back to the composite
    # (date, merchant, amount) tuple — but that's lossy for same-day repeats.
    transaction_id = models.CharField(
        max_length=64, blank=True, default="", db_index=True
    )

    class Meta:
        # Removing unique_together on (date, merchant, amount) — it silently
        # drops legitimate same-day repeats (e.g., two ₹10 teas).
        # We rely on transaction_id where available, and on the parser's
        # in-memory dedup set otherwise.
        indexes = [
            models.Index(fields=['date', 'category']),
            models.Index(fields=['merchant']),
        ]

    def __str__(self):
        return f"{self.date} - {self.merchant} - ₹{self.amount}"


class CategoryBudget(models.Model):
    category = models.CharField(max_length=100)
    monthly_cap = models.DecimalField(max_digits=10, decimal_places=2)
    # Format: YYYY-MM. Blank default prevents stale months from silently matching.
    target_month = models.CharField(max_length=7, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # One budget row per (category, month). Prevents duplicate rows.
        unique_together = ('category', 'target_month')

    def __str__(self):
        return f"{self.category}: ₹{self.monthly_cap} ({self.target_month})"


class MerchantCategory(models.Model):
    """
    Persistent cache for AI-categorized merchants. Replaces the class-level
    dict that leaked memory and couldn't be shared across processes.
    """
    merchant = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=100)
    source = models.CharField(
        max_length=16,
        choices=[('rule', 'Rule'), ('ai', 'AI'), ('user', 'User')],
        default='ai',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['merchant'])]

    def __str__(self):
        return f"{self.merchant} → {self.category} ({self.source})"