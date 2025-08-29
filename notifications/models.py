from django.db import models
from users.models import User

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 알림 대상
    content = models.TextField()  # 알림 내용
    target_link = models.CharField(max_length=255, blank=True)  # 제안/공고 등 링크
    is_read = models.BooleanField(default=False)  # 읽음 여부
    created_at = models.DateTimeField(auto_now_add=True)  # 생성 일시

    def __str__(self):
        return f"Notification to {self.user.id} - {self.content[:20]}"
