from django.db import models
from django.db.models import Q
from artists.models import Artist
from spaces.models import Space
from postings.models import Posting


class Suggestion(models.Model):
    SENDER_ARTIST = "artist"
    SENDER_SPACE = "space"
    SENDER_TYPES = (
        (SENDER_ARTIST, "artist"),
        (SENDER_SPACE, "space"),
    )

    sender_type = models.CharField(max_length=10, choices=SENDER_TYPES)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="suggestions_as_artist")
    space = models.ForeignKey(Space, on_delete=models.CASCADE, related_name="suggestions_as_space")
    posting = models.ForeignKey(Posting, on_delete=models.SET_NULL, blank=True, null=True, related_name="suggestions")

    message = models.TextField()

    # 조건부 필드 — 아티스트 전용 / 공간 전용
    is_free_allowed = models.BooleanField(blank=True, null=True)          # artist sender 전용
    is_performed_confirmed = models.BooleanField(blank=True, null=True)   # space sender 전용

    # 상태: None(대기) / True(수락) / False(거절)
    is_accepted = models.BooleanField(blank=True, null=True)
    is_read = models.BooleanField(default=False)  # 읽음 여부 (기본 False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        #constraints = [
            # 진행중(대기) 상태 중복 방지: 같은 artist-space 조합의 pending은 1건만
            #models.UniqueConstraint(
            #    fields=["artist", "space"],
            #    condition=Q(is_accepted__isnull=True),
            #    name="uniq_pending_suggestion_artist_space",
            #),
        #]
        pass
    

    def __str__(self):
        return f"[{self.id}] {self.sender_type} -> A{self.artist_id}/S{self.space_id}"
