from django.db import models

# Create your models here.
from django.db import models
from agents.models import VoiceAgent


class KnowledgeFile(models.Model):
    agent = models.ForeignKey(
        VoiceAgent,
        on_delete=models.CASCADE,
        related_name="knowledge_files"
    )
    file = models.FileField(upload_to="knowledge_files/")
    extracted_text = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.agent.name} - {self.file.name}"
    


class KnowledgeChunk(models.Model):
    knowledge_file = models.ForeignKey(
        KnowledgeFile,
        on_delete=models.CASCADE,
        related_name="chunks"
    )
    content = models.TextField()
    embedding = models.BinaryField(null=True, blank=True)

    def __str__(self):
        return f"Chunk {self.id}"