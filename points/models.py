from django.db import models
from users.models import User

class PointTransaction(models.Model):
    TRANSACTION_CHOICES = [
        ('charge', '충전'),
        ('deduct', '차감'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_CHOICES)
    amount = models.PositiveIntegerField()  # 변동 포인트
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.user.role != "artist":
            raise ValueError("포인트는 아티스트 계정만 사용할 수 있습니다.")
        if self.amount <= 0:
            raise ValueError("포인트 금액은 양수여야 합니다.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.kakao_id} - {self.transaction_type} {self.amount}P"

    @property
    def balance(self):
        charges = PointTransaction.objects.filter(
            user=self.user, transaction_type="charge"
        ).aggregate(models.Sum("amount"))["amount__sum"] or 0
        deducts = PointTransaction.objects.filter(
            user=self.user, transaction_type="deduct"
        ).aggregate(models.Sum("amount"))["amount__sum"] or 0
        return charges - deducts
