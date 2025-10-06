# transcripts/models.py

from django.db import models
from core.models import Video

class Transcript(models.Model):
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name='transcript')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transcript for {self.video.title}"