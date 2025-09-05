from django.db import models
from django.core.exceptions import ValidationError
from artists.models import Artist
from spaces.models import Space


class Suggestion(models.Model):
    # 제안 주체: 아티스트 → 공간 / 공간 → 아티스트
    SENDER_TYPE_CHOICES = [
        ("artist", "Artist → Space"),
        ("space", "Space → Artist"),
    ]

    sender_type = models.CharField(max_length=10, choices=SENDER_TYPE_CHOICES)

    # FK
    artist_id = models.ForeignKey(Artist, on_delete=models.CASCADE)
    space_id = models.ForeignKey(Space, on_delete=models.CASCADE)

    # 제안 메시지
    message = models.TextField()

    # 상태값
    is_accepted = models.BooleanField(default=False)          # 제안 수락 여부
    is_free_allowed = models.BooleanField(default=False)      # 아티스트 전용
    is_performed_confirmed = models.BooleanField(default=False)  # 공간 전용

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Suggestion from {self.sender_type} ({self.artist_id} ↔ {self.space_id})"

    # ✅ 무결성 검증
    def clean(self):
        if self.sender_type == "artist" and self.is_performed_confirmed:
            raise ValidationError("아티스트 제안에는 'is_performed_confirmed'를 사용할 수 없습니다.")
        if self.sender_type == "space" and self.is_free_allowed:
            raise ValidationError("공간 제안에는 'is_free_allowed'를 사용할 수 없습니다.")

    # ✅ 저장 전에 항상 clean() 실행
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
