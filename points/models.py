from django.db import models
from users.models import User

class Point(models.Model):
    # 어떤 사용자(아티스트)가 사용하는지
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # 현재 잔액
    balance = models.IntegerField(default=0)

    # 거래 타입: 충전(charge) or 차감(deduct)
    TRANSACTION_TYPES = [
        ('charge', '충전'),
        ('deduct', '차감'),
    ]
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)

    # 거래 금액 (변동된 포인트)
    amount = models.IntegerField()

    # 생성일시
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.user.id}] {self.transaction_type} {self.amount}p"
