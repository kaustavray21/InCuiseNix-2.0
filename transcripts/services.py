import os
import re
import csv
import whisper
from django.conf import settings
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

def sanitize_filename(title):
    # This is now only used for creating directory names from course titles
    sanitized = re.sub(r'[\\/*?:"<>|]', "", title)
    return sanitized

def save_transcript_to_csv(transcript, video):
    """Saves the transcript to a CSV file named after the video's video_id."""
    if not transcript:
        return

    sanitized_course_title = sanitize_filename(video.course.title)
    transcript_dir = os.path.join(settings.MEDIA_ROOT, 'transcripts', sanitized_course_title)
    os.makedirs(transcript_dir, exist_ok=True)
    
    # Use video_id for the filename
    file_path = os.path.join(transcript_dir, f"{video.video_id}.csv")

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['start', 'text'])
        for item in transcript:
            writer.writerow([item['start'], item['text']])

def get_transcript(video):
    """Fetches transcript from YouTube API or generates it using Whisper."""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video.video_id)
        return [{'start': item['start'], 'text': item['text']} for item in transcript_list]
    except Exception as e:
        print(f"Could not fetch transcript from YouTube API: {e}. Trying Whisper.")
        video_path = download_video(video)
        if video_path:
            transcript = transcribe_with_whisper(video_path)
            return transcript
        return None

def download_video(video):
    """Downloads a video, naming the file after the video_id."""
    sanitized_course_title = sanitize_filename(video.course.title)
    download_dir = os.path.join(settings.MEDIA_ROOT, 'downloads', sanitized_course_title)
    os.makedirs(download_dir, exist_ok=True)
    
    # Use video_id for the filename
    output_template = os.path.join(download_dir, f'{video.video_id}.%(ext)s')

    # Check for existing video files named with the video_id
    for ext in ['mp4', 'mkv', 'webm', 'mov', 'avi']:
        expected_video_path = os.path.join(download_dir, f'{video.video_id}.{ext}')
        if os.path.exists(expected_video_path):
            print(f"Video for '{video.title}' already exists. Using existing file.")
            return expected_video_path

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_template,
        'merge_output_format': 'mp4',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video.video_url, download=True)
            final_filepath = ydl.prepare_filename(info)
            if os.path.exists(final_filepath):
                return final_filepath
            else:
                 merged_filepath = os.path.splitext(final_filepath)[0] + "." + ydl.get_info().get('ext')
                 if os.path.exists(merged_filepath):
                     return merged_filepath
                 else:
                     print(f"Error: Could not find the downloaded video file for '{video.title}'.")
                     return None
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

def transcribe_with_whisper(video_path):
    try:
        model = whisper.load_model("base")
        result = model.transcribe(video_path)
        
        transcript_data = []
        for segment in result['segments']:
            transcript_data.append({
                'start': segment['start'],
                'text': segment['text']
            })
        return transcript_data
    except Exception as e:
        print(f"Error during transcription with Whisper: {e}")
        return None

def get_transcript_from_file(video):
    """Loads a transcript from a CSV file named after the video's video_id."""
    try:
        sanitized_course_title = sanitize_filename(video.course.title)
        
        # Look for a CSV file named with the video_id
        file_path = os.path.join(
            settings.MEDIA_ROOT, 
            'transcripts', 
            sanitized_course_title, 
            f"{video.video_id}.csv"
        )

        if not os.path.exists(file_path):
            return None

        transcript_data = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # Skip header
            for row in reader:
                transcript_data.append({
                    'start': float(row[0]),
                    'text': row[1]
                })
        return transcript_data
        
    except Exception as e:
        print(f"Error loading transcript file for '{video.title}': {e}")
        return None