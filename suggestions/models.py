from django.db import models
from users.models import User

class Suggestion(models.Model):
    # 발신자/수신자
    sender = models.ForeignKey(
    User,
    on_delete=models.CASCADE,
    related_name="sent_suggestions",
    null=True,
    blank=True
)

    receiver = models.ForeignKey(
    User, 
    on_delete=models.CASCADE, 
    related_name="received_suggestions",
    null=True, blank=True   # ✅ 추가
)

    # 메시지
    message = models.TextField()

    # 무료 공연 여부
    is_free_allowed_suggestion = models.BooleanField(default=False)
    is_performed_confirmed = models.BooleanField(
    default=False,
    help_text="공간 보유자만 공연 완료 여부를 체크할 수 있습니다."
)


    # 상태 (수신자 기준)
    status = models.CharField(
        max_length=10,
        choices=[
            ("pending", "미확인"),
            ("accepted", "수락"),
            ("rejected", "거절"),
        ],
        default="pending",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # 유효성 체크: 같은 유형끼리는 제안 불가
    def save(self, *args, **kwargs):
        if self.sender.role == self.receiver.role:
            raise ValueError("아티스트는 공간 보유자에게, 공간 보유자는 아티스트에게만 제안할 수 있습니다.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sender} → {self.receiver} ({self.status})"
