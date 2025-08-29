from rest_framework.viewsets import ModelViewSet
from .models import Posting
from .serializers import PostingSerializer

class PostingViewSet(ModelViewSet):
    queryset = Posting.objects.all()
    serializer_class = PostingSerializer
