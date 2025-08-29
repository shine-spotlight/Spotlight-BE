from django.db import models
from artists.models import Artist
from spaces.models import Space

class Suggestion(models.Model):
    # 제안 주체: 아티스트 → 공간 / 공간 → 아티스트
    SENDER_TYPE_CHOICES = [
        ("artist", "Artist → Space"),
        ("space", "Space → Artist"),
    ]

    sender_type = models.CharField(max_length=10, choices=SENDER_TYPE_CHOICES)

    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="sent_suggestions")
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name="received_suggestions")

    message = models.TextField()  # 제안서 내용
    performance_date = models.DateField()  # 희망 공연 날짜

    

    # 상태
    is_accepted = models.BooleanField(default=False)  # 수락 여부
    is_performed_confirmed = models.BooleanField(default=False)  # 공연 완료 여부(공간측만)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender_type} suggestion: {self.artist.name} ↔ {self.space.place_name}"
