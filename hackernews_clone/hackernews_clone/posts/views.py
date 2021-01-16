from datetime import datetime, timezone
from requests.exceptions import ConnectionError

from django_celery_beat.models import PeriodicTask
from django.db import transaction
from django.core.cache import cache
from rest_framework import filters, generics, serializers, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from hackernews_clone.posts.models import Post
from hackernews_clone.posts.tasks import scrap_from_web, fetch_from_api


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = '__all__'


class PostList(generics.ListAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['@subject']

    def get(self, request, *args, **kwargs):
        if cache.get('running'):
            return Response(
                {
                    'message': 'Update with Hackernews In Progress',
                },
                status=status.HTTP_409_CONFLICT
            )
        else:
            return self.list(request, *args, **kwargs)


@api_view(['GET'])
def get_scrapper_info(request):
    context = {
        'running': cache.get('running'),
        'last_start_time': cache.get('scrapper_last_start_time'),
        'last_finish_time': cache.get('scrapper_last_finish_time'),
    }
    return Response(context)


@api_view(['POST'])
def update_using_scrapper(request):
    if not cache.get('running'):
        try:
            with transaction.atomic():
                periodic_task = PeriodicTask.objects.select_for_update().get(
                    name='Scrap Posts')
                periodic_task.last_run_at = datetime.now(tz=timezone.utc)
                periodic_task.save()
            scrap_from_web()
        except ConnectionError:
            return Response(
                {
                    'message': 'Hackernews Connection Problem',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    else:
        return Response(
            {
                'message': 'Update with Hackernews Already In Progress',
            },
            status=status.HTTP_409_CONFLICT
        )

    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
def get_fetch_api_info(request):
    context = {
        'running': cache.get('running'),
        'last_start_time': cache.get('fetch_api_last_start_time'),
        'last_finish_time': cache.get('fetch_api_last_finish_time'),
    }
    return Response(context)


@api_view(['POST'])
def update_using_api(request):
    if not cache.get('running'):
        try:
            with transaction.atomic():
                periodic_task = PeriodicTask.objects.select_for_update().get(
                    name='Fetch Posts From Api')
                periodic_task.last_run_at = datetime.now(tz=timezone.utc)
                periodic_task.save()
            fetch_from_api()
        except ConnectionError:
            return Response(
                {
                    'message': 'Hackernews API Connection Problem',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
    else:
        return Response(
            {
                'message': 'Update with Hackernews Already In Progress',
            },
            status=status.HTTP_409_CONFLICT
        )

    return Response(status=status.HTTP_200_OK)
