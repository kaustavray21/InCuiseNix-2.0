import os
import csv
from urllib.parse import urlparse, parse_qs
from django.conf import settings
# Import the library in a way that avoids the Windows bug
from youtube_transcript_api._api import YouTubeTranscriptApi
from youtube_transcript_api import NoTranscriptFound

def get_video_id(url):
    """Extract video ID from YouTube URLs."""
    try:
        if 'embed/' in url:
            return url.split('embed/')[1].split('?')[0]
        parsed_url = urlparse(url)
        if parsed_url.netloc == 'youtu.be':
            return parsed_url.path[1:]
        elif 'youtube.com' in parsed_url.netloc and parsed_url.path == '/watch':
            return parse_qs(parsed_url.query)['v'][0]
        return None
    except Exception:
        return None

def get_transcript(video_url):
    """Retrieve transcript using the local youtube-transcript-api library."""
    video_id = get_video_id(video_url)
    if not video_id:
        return None
    
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en'])
        return transcript.fetch()
    except NoTranscriptFound:
        print(f"No English transcript found for {video_id}. Trying first available.")
        try:
            transcript = transcript_list[0]
            return transcript.fetch()
        except Exception as e:
            print(f"Could not retrieve any transcript for {video_id}: {e}")
            return None
    except Exception as e:
        print(f"An unexpected error occurred while fetching transcript for {video_id}: {e}")
        return None

def save_transcript_to_csv(transcript, video_id):
    """Save transcript to a CSV file."""
    output_dir = os.path.join(settings.MEDIA_ROOT, 'transcripts')
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, f"{video_id}_transcript.csv")
    
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['start', 'duration', 'text'])
        for entry in transcript:
            writer.writerow([entry.get('start', ''), entry.get('duration', ''), entry.get('text', '')])
    return file_path