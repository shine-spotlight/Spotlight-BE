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
        # ✅ 아티스트와 공간 둘 다 선택 불가
        if self.artist and self.space:
            raise ValidationError("아티스트와 공간을 동시에 좋아요할 수 없습니다.")

        # ✅ 둘 다 비어있으면 안 됨
        if not self.artist and not self.space:
            raise ValidationError("아티스트 또는 공간 중 하나는 선택해야 합니다.")

        # ✅ 본인 아티스트 → 자기 자신 찜 금지
        if self.artist and self.artist.user == self.user:
            raise ValidationError("아티스트는 자기 자신을 찜할 수 없습니다.")

        # ✅ 본인 공간 → 자기 공간 찜 금지
        if self.space and self.space.user == self.user:
            raise ValidationError("공간 보유자는 자기 공간을 찜할 수 없습니다.")


    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        target = self.artist.name if self.artist else self.space.place_name
        return f"{self.user.id} likes {target}"
