import os
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.conf import settings
from core.models import Video
from .services import sanitize_filename # Import the new helper function

def download_transcript_view(request, video_id):
    video = get_object_or_404(Video, id=video_id)
    
    # Sanitize the title to find the correct file
    sanitized_title = sanitize_filename(video.title)
    
    file_path = os.path.join(settings.MEDIA_ROOT, 'transcripts', f"{sanitized_title}.csv")

    if os.path.exists(file_path):
        # Serve the file with a clean filename for the user
        response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=f"{sanitized_title}.csv")
        return response
    else:
        raise Http404("Transcript file not found. It may not have been generated yet.")