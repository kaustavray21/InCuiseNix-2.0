import time
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.contrib.auth.models import User
from core.models import Video
from django_q.tasks import async_task

class Command(BaseCommand):
    help = 'Queues FAISS note index generation tasks for all users/videos with notes.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Scanning for videos with notes...'))
        start_time = time.time()
        
        # 1. Find videos that actually have notes
        videos_with_notes = Video.objects.annotate(
            note_count=Count('note')
        ).filter(note_count__gt=0)
        
        if not videos_with_notes.exists():
            self.stdout.write(self.style.WARNING('No videos with notes found. Nothing to queue.'))
            return

        self.stdout.write(f'Found {videos_with_notes.count()} videos containing notes.')
        
        queued_count = 0
        skipped_count = 0

        # 2. Iterate through videos and find relevant users
        for video in videos_with_notes:
            platform_id = video.youtube_id or video.vimeo_id
            
            if not platform_id:
                self.stderr.write(self.style.ERROR(f'Skipping Video {video.id}: Missing Platform ID (YouTube/Vimeo)'))
                skipped_count += 1
                continue

            # Find all users who have written notes on this specific video
            # distinct() ensures we only queue one task per user per video
            users_with_notes = User.objects.filter(note__video=video).distinct()

            for user in users_with_notes:
                # Queue the task using the wrapper defined in engine/tasks.py
                async_task(
                    'engine.tasks.task_update_note_index', 
                    user_id=user.id, 
                    video_id=platform_id
                )
                queued_count += 1
                
            self.stdout.write(f'  - Video "{video.title}": Queued updates for {users_with_notes.count()} user(s).')

        end_time = time.time()
        total_time = end_time - start_time
        
        self.stdout.write(self.style.SUCCESS('=' * 30))
        self.stdout.write(self.style.SUCCESS('Batch Queue Complete!'))
        self.stdout.write(f'Total Tasks Queued: {queued_count}')
        self.stdout.write(f'Skipped Videos: {skipped_count}')
        self.stdout.write(f'Time taken: {total_time:.2f} seconds')