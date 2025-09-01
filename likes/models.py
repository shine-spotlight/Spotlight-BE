from django.db import models
from django.core.exceptions import ValidationError
from users.models import User
from artists.models import Artist
from spaces.models import Space


class Like(models.Model):
    # 좋아요를 누른 사람
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # 대상 구분 (Artist ↔ Space)
    ROLE_CHOICES = [
        ('artist', 'Artist'),
        ('space', 'Space'),
    ]
    target_type = models.CharField(max_length=20, choices=ROLE_CHOICES)

    # 대상 이름 (Artist.name or Space.place_name)
    # ✅ 마이그레이션 오류 방지를 위해 null/blank 허용
    target_name = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # 동일 유저가 동일 대상에게 중복 좋아요 불가
        unique_together = ('user', 'target_type', 'target_name')

    def clean(self):
        """
        Validation:
        1. role에 따른 대상만 허용
        2. 존재하지 않는 대상 좋아요 불가
        """
        if self.target_type == "artist":
            if not Artist.objects.filter(name=self.target_name).exists():
                raise ValidationError("해당 아티스트가 존재하지 않습니다.")
        elif self.target_type == "space":
            if not Space.objects.filter(place_name=self.target_name).exists():
                raise ValidationError("해당 공간이 존재하지 않습니다.")
        else:
            raise ValidationError("잘못된 target_type 입니다.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.id} likes {self.target_type}: {self.target_name}"
