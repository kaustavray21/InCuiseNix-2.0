import os
import re
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Video

def sanitize_filename(title):
    return re.sub(r'[\\/*?:"<>|]', "", title)

def get_youtube_id_from_url(url):
    if "embed/" in url:
        return url.split("embed/")[1].split("?")[0]
    return None

class Command(BaseCommand):
    help = 'Renames media and transcript files to use the YouTube video ID from the video_url.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting renaming process to use YouTube IDs...'))
        
        # Load the original video_ids from courses.json to find the old files
        with open('courses.json', 'r') as f:
            courses_data = json.load(f)

        video_id_map = {}
        for course_data in courses_data:
            for video_data in course_data['videos']:
                new_id = get_youtube_id_from_url(video_data['video_url'])
                if new_id:
                    video_id_map[video_data['video_id']] = new_id

        # Now find the video objects in the DB to get course info
        all_videos = Video.objects.select_related('course').all()
        renamed_files_count = 0

        for old_id, new_id in video_id_map.items():
            # Find the corresponding video object in the database
            video = all_videos.filter(video_id=new_id).first()
            if not video:
                continue

            self.stdout.write(f'Checking for video with old ID: "{old_id}" -> new ID: "{new_id}"')
            
            sanitized_course_title = sanitize_filename(video.course.title)

            # --- 1. Rename Transcript File ---
            transcript_dir = os.path.join(settings.MEDIA_ROOT, 'transcripts', sanitized_course_title)
            old_transcript_path = os.path.join(transcript_dir, f"{old_id}.csv")
            new_transcript_path = os.path.join(transcript_dir, f"{new_id}.csv")

            if os.path.exists(old_transcript_path):
                try:
                    os.rename(old_transcript_path, new_transcript_path)
                    self.stdout.write(self.style.SUCCESS(f'  - Renamed transcript to: {new_id}.csv'))
                    renamed_files_count += 1
                except OSError as e:
                    self.stdout.write(self.style.ERROR(f'  - Error renaming transcript: {e}'))
            
            # --- 2. Rename Video File ---
            download_dir = os.path.join(settings.MEDIA_ROOT, 'downloads', sanitized_course_title)
            
            for ext in ['mp4', 'mkv', 'webm', 'mov', 'avi']:
                old_video_path = os.path.join(download_dir, f"{old_id}.{ext}")
                if os.path.exists(old_video_path):
                    new_video_path = os.path.join(download_dir, f"{new_id}.{ext}")
                    try:
                        os.rename(old_video_path, new_video_path)
                        self.stdout.write(self.style.SUCCESS(f'  - Renamed video to: {new_id}.{ext}'))
                        renamed_files_count += 1
                    except OSError as e:
                        self.stdout.write(self.style.ERROR(f'  - Error renaming video: {e}'))
                    break

        self.stdout.write(self.style.SUCCESS(f'\nFinished. Successfully renamed {renamed_files_count} file(s).'))