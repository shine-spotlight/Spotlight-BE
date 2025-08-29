from django.db import models
from spaces.models import Space

class SpaceAvailableDate(models.Model):
    # 어떤 공간에 해당하는지
    space = models.ForeignKey(Space, on_delete=models.CASCADE)

    # 가능한 날짜
    date = models.DateField()

    # 기획공연 여부
    is_planned_event = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.space.place_name} - {self.date} ({'기획공연' if self.is_planned_event else '일반'})"
