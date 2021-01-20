from rest_framework import filters, status
from rest_framework.generics import ListAPIView
from rest_framework.decorators import api_view
from rest_framework.response import Response

from hackernews_clone.posts.models import Post, ScrapperTracker, APIFetcherTracker
from hackernews_clone.posts.serializers import PostSerializer
from hackernews_clone.posts.tasks import scrap_from_web, fetch_from_api


class PostList(ListAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["@subject"]

    def get(self, request, *args, **kwargs):
        if ScrapperTracker.objects.get(pk=1).status == ScrapperTracker.ACTIVE:
            return Response(status=status.HTTP_409_CONFLICT)
        else:
            return self.list(request, *args, **kwargs)


@api_view(["GET"])
def get_scrapper_info(request):
    st = ScrapperTracker.objects.get(pk=1)
    context = {
        "status": st.get_status_display(),
        "last_run_at": st.last_run_at,
        "last_run_finish_at": st.last_run_finish_at,
    }
    return Response(context)


@api_view(["POST"])
def update_using_scrapper(request):
    if ScrapperTracker.objects.get(pk=1).status == ScrapperTracker.ACTIVE:
        return Response(status=status.HTTP_409_CONFLICT)

    scrap_from_web.delay()
    return Response(status=status.HTTP_200_OK)


@api_view(["GET"])
def get_fetch_api_info(request):
    at = APIFetcherTracker.objects.get(pk=1)
    context = {
        "status": at.get_status_display(),
        "last_run_at": at.last_run_at,
        "last_run_finish_at": at.last_run_finish_at,
    }
    return Response(context)


@api_view(["POST"])
def update_using_api(request):
    if APIFetcherTracker.objects.get(pk=1).status == APIFetcherTracker.ACTIVE:
        return Response(status=status.HTTP_409_CONFLICT)

    fetch_from_api.delay()
    return Response(status=status.HTTP_200_OK)
