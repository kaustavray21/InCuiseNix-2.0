import os
import csv
import re # Make sure re is imported
from urllib.parse import urlparse, parse_qs
from django.conf import settings
import whisper
from yt_dlp import YoutubeDL

def sanitize_filename(title):
    """Removes illegal characters from a string to make it a valid filename."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", title)
    sanitized = sanitized.replace(":", " -")
    return sanitized

def get_video_id(url):
    """Extracts video ID from various YouTube URL formats."""
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

def download_video(video_id, video_title, output_dir):
    """Downloads a video from YouTube using its title as the filename."""
    sanitized_title = sanitize_filename(video_title)
    video_path = os.path.join(output_dir, f"{sanitized_title}.mp4")

    if os.path.exists(video_path):
        print(f"Video already exists: {video_path}")
        return video_path

    # Use the sanitized title as the output filename template
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': video_path, # Directly use the path we constructed
        'quiet': False,
    }
    
    with YoutubeDL(ydl_opts) as ydl:
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"Downloading '{video_title}'...")
            ydl.download([url])
            return video_path
        except Exception as e:
            print(f"Failed to download video '{video_title}': {e}")
            return None

def transcribe_local_video(video_path):
    """Transcribes a local video file using Whisper."""
    print(f"Transcribing local video: {video_path}")
    try:
        model = whisper.load_model("tiny") # Using the faster 'tiny' model
        result = model.transcribe(video_path)
        transcript_data = []
        for segment in result['segments']:
            transcript_data.append({
                'start': segment['start'],
                'duration': segment['end'] - segment['start'],
                'text': segment['text']
            })
        return transcript_data
    except Exception as e:
        print(f"Error during local transcription: {e}")
        return None

def get_transcript(video_url, video_title):
    """Main function to download and transcribe a video, using its title."""
    video_id = get_video_id(video_url)
    if not video_id:
        raise ValueError("Invalid YouTube video URL")

    video_download_dir = os.path.join(settings.MEDIA_ROOT, 'videos')
    os.makedirs(video_download_dir, exist_ok=True)
    
    # Pass the title to the download function
    video_path = download_video(video_id, video_title, video_download_dir)
    
    if video_path:
        return transcribe_local_video(video_path)
    else:
        print(f"Could not generate transcript for '{video_title}' because download failed.")
        return None

def save_transcript_to_csv(transcript, video_title):
    """Saves the transcript data to a CSV file named after the video title."""
    sanitized_title = sanitize_filename(video_title)
    output_dir = os.path.join(settings.MEDIA_ROOT, 'transcripts')
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, f"{sanitized_title}.csv")
    
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['start', 'duration', 'text'])
        for entry in transcript:
            writer.writerow([entry['start'], entry['duration'], entry['text']])
    print(f"Transcript saved to {file_path}")
    return file_path