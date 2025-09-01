from django.db import models
from users.models import User

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    target_type = models.CharField(
        max_length=20,
        choices=[('artist', 'Artist'), ('space', 'Space')]
    )
    target_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'target_type', 'target_id')  # 중복 방지

    def __str__(self):
        return f"{self.user} likes {self.target_type}:{self.target_id}"
