from django.db import models
from users.models import User
from artists.models import Artist
from spaces.models import Space

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 좋아요 누른 사람
    target_type = models.CharField(
        max_length=20,
        choices=[('artist', 'Artist'), ('space', 'Space')]
    )
    target_id = models.IntegerField()  # artist.id or space.id
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.id} likes {self.target_type}:{self.target_id}"
