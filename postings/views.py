from rest_framework import viewsets
from .models import Posting
from .serializers import PostingSerializer


class PostingViewSet(viewsets.ModelViewSet):
    queryset = Posting.objects.all().order_by("-created_at")
    serializer_class = PostingSerializer
