from rest_framework import serializers
from .models import KnowledgeFile


class KnowledgeUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeFile
        fields = ["file"]