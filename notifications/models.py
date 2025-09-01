from django.db import models
from users.models import User


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 알림 받을 회원
    content = models.TextField()  # 알림 내용
    target_link = models.URLField()  # 연결 URL (http:// or https:// 필수)
    is_read = models.BooleanField(default=False)  # 읽음 여부
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification to {self.user.id}: {self.content[:20]}"
