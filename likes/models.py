from django.db import models
from users.models import User
from artists.models import Artist
from spaces.models import Space


class Like(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="likes"
    )
    artist = models.ForeignKey(
        Artist,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="liked_by"
    )
    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="liked_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "artist"], name="unique_user_artist_like"),
            models.UniqueConstraint(fields=["user", "space"], name="unique_user_space_like"),
        ]

    def __str__(self):
        if self.artist:
            return f"{self.user} likes Artist {self.artist}"
        if self.space:
            return f"{self.user} likes Space {self.space}"
        return f"{self.user} likes ?"
