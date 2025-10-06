from django.db import models
from core.models import Video

class Transcript(models.Model):
    """
    A container for all the transcript lines for a single video.
    """
    video = models.OneToOneField(Video, on_delete=models.CASCADE, related_name='transcript')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transcript for {self.video.title}"

class TranscriptLine(models.Model):
    """
    Represents a single line in a transcript with start and end times.
    """
    transcript = models.ForeignKey(Transcript, on_delete=models.CASCADE, related_name='lines')
    start_time = models.FloatField()
    end_time = models.FloatField(null=True, blank=True) # End time is optional
    text = models.TextField()

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.start_time}s: {self.text}"