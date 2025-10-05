from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from core.models import Video
from .services import get_transcript, save_transcript_to_csv

def download_transcript_view(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    transcript = get_transcript(video.video_url)

    if transcript:
        file_path = save_transcript_to_csv(transcript, video.video_id)
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=f"{video.video_id}_transcript.csv")
    
    return HttpResponse(
        "A transcript could not be found for this video.", 
        status=404 # Not Found status
    )