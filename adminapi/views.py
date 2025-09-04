from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from artists.models import Artist
from artists.serializers import ArtistSerializer
from spaces.models import Space
from spaces.serializers import SpaceSerializer
from postings.models import Posting
from postings.serializers import PostingSerializer
from points.models import PointTransaction
from points.serializers import PointTransactionSerializer
from notifications.models import Notification
from notifications.serializers import NotificationSerializer

class AdminViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["get"], url_path="artists")
    def artists(self, request):
        return Response(ArtistSerializer(Artist.objects.all(), many=True).data)

    @action(detail=True, methods=["patch"], url_path="artists")
    def update_artist(self, request, pk=None):
        artist = Artist.objects.get(pk=pk)
        serializer = ArtistSerializer(artist, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="spaces")
    def spaces(self, request):
        return Response(SpaceSerializer(Space.objects.all(), many=True).data)

    @action(detail=True, methods=["patch"], url_path="spaces")
    def update_space(self, request, pk=None):
        space = Space.objects.get(pk=pk)
        serializer = SpaceSerializer(space, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["delete"], url_path="postings")
    def delete_posting(self, request, pk=None):
        Posting.objects.get(pk=pk).delete()
        return Response({"status": "deleted"}, status=204)

    @action(detail=False, methods=["get"], url_path="points/history")
    def points_history(self, request):
        return Response(PointTransactionSerializer(PointTransaction.objects.all(), many=True).data)

    @action(detail=False, methods=["get"], url_path="points/balance")
    def points_balance(self, request):
        balances = {}
        for tx in PointTransaction.objects.all():
            balances[tx.user.id] = tx.balance
        return Response(balances)

    @action(detail=False, methods=["post"], url_path="notifications")
    def send_notification(self, request):
        serializer = NotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)
