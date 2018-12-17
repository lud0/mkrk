from rest_framework import serializers

from main.models import Article, Target, UserTarget


class ArticleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Article
        fields = ('url', 'title', 'snippet', 'source', 'published_at', 'sentiment_data')
        # read_only_fields = ('id', )


class UserTargetSerializer(serializers.ModelSerializer):
    keyword = serializers.CharField(source='target_keyword.keyword')

    class Meta:
        model = UserTarget
        fields = ('id', 'keyword')
        read_only_fields = ('id', )

    def create(self, validated_data):
        target, created = Target.objects.get_or_create(keyword=validated_data['target_keyword']['keyword'])
        validated_data['target_keyword'] = target
        usertarget, created = UserTarget.objects.get_or_create(**validated_data)

        return usertarget
