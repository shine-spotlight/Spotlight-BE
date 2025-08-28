from django.db import models

class User(models.Model):
    ROLE_CHOICES = (
        ('artist', 'Artist'),
        ('space', 'Space'),
    )
    kakao_id = models.CharField(max_length=255, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role} - {self.kakao_id}"
