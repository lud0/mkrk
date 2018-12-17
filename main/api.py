from django.http import Http404
from rest_framework import authentication, permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Article, UserTarget
from main.serializers import ArticleSerializer, UserTargetSerializer


class APIUserTarget(APIView):

    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        serializer = UserTargetSerializer(request.user.my_targets.all(), many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = UserTargetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, format=None):
        try:
            user_target = UserTarget.objects.get(pk=request.data['id'])
        except UserTarget.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if request.user != user_target.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        user_target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class APIArticle(APIView):

    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, format=None):
        user_keywords = list(request.user.my_targets.all().values_list('target_keyword__keyword', flat=True))
        user_articles = Article.objects.filter(sentiment_data__reports__0__target_keyword__in=user_keywords)
        serializer = ArticleSerializer(user_articles, many=True)
        return Response(serializer.data)
