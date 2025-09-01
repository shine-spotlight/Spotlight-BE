from django.db import models
from django.core.exceptions import ValidationError
from users.models import User
from artists.models import Artist
from spaces.models import Space


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 좋아요 누른 회원
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, null=True, blank=True)
    space = models.ForeignKey(Space, on_delete=models.CASCADE, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "artist"], name="unique_user_artist_like"),
            models.UniqueConstraint(fields=["user", "space"], name="unique_user_space_like"),
        ]

    def clean(self):
        # artist와 space 둘 다 선택 불가
        if self.artist and self.space:
            raise ValidationError("아티스트와 공간을 동시에 좋아요할 수 없습니다.")
        # 둘 다 비어있으면 안 됨
        if not self.artist and not self.space:
            raise ValidationError("아티스트 또는 공간 중 하나는 선택해야 합니다.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        target = self.artist.name if self.artist else self.space.place_name
        return f"{self.user.id} likes {target}"
