from django.db import models
from users.models import User


class PointTransaction(models.Model):
    TYPE_CHARGE = "charge"
    TYPE_DEDUCT = "deduct"
    TYPES = (
        (TYPE_CHARGE, "충전"),
        (TYPE_DEDUCT, "차감"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="point_transactions")
    amount = models.IntegerField()  # 양수만 저장
    transaction_type = models.CharField(max_length=10, choices=TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.user}] {self.transaction_type} {self.amount} at {self.created_at}"

    class Meta:
        ordering = ["-created_at"]
