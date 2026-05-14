from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import KnowledgeFile,KnowledgeChunk

admin.site.register(KnowledgeFile)
admin.site.register(KnowledgeChunk)