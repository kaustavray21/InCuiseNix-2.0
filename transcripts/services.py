import os
import csv
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
from django.conf import settings

def get_video_id(url):
    """Extract video ID from YouTube URLs."""
    try:
        # The video URLs in your courses.json are in 'embed' format
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
    """Retrieve transcript using youtube_transcript_api."""
    video_id = get_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube video URL")
    
    try:
        # This is a more robust way to find and fetch the transcript
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript(['en'])
        return transcript.fetch()
    except NoTranscriptFound:
        print(f"No English transcript found for {video_id}. Trying first available.")
        try:
            # If English isn't found, try getting the first transcript in the list
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
            writer.writerow([entry['start'], entry['duration'], entry['text']])
    return file_path