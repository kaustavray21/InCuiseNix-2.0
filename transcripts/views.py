from django.shortcuts import render

from django.http import JsonResponse, FileResponse
from django.shortcuts import get_object_or_404
from core.models import Video
from .services import get_transcript, save_transcript_to_csv

def download_transcript_view(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    transcript = get_transcript(video.video_url)

    if transcript:
        # Save the transcript to a CSV file
        file_path = save_transcript_to_csv(transcript, video.video_id)
        
        # Return the file as a response
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=f"{video.video_id}_transcript.csv")
    
    return JsonResponse({'status': 'error', 'message': 'Could not retrieve transcript.'}, status=404)