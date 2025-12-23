from django.core.management.base import BaseCommand
from django_q.models import Task, OrmQ, Schedule
from core.models import Video

class Command(BaseCommand):
    help = 'Clears all Django Q data and resets stuck videos to pending.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting System Cleanup..."))

        # 1. Clear Pending Tasks (The "Stacked Up" Queue)
        pending_count = OrmQ.objects.count()
        if pending_count > 0:
            OrmQ.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'  [✓] Deleted {pending_count} pending tasks from queue.'))
        else:
            self.stdout.write('  [-] No pending tasks found.')

        # 2. Clear History (Failed & Successful Logs)
        history_count = Task.objects.count()
        if history_count > 0:
            Task.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'  [✓] Deleted {history_count} entries from task history.'))
        else:
            self.stdout.write('  [-] No task history found.')

        # 3. Reset "Stuck" Videos (The most important part!)
        # If a task was deleted while running, the video still thinks it is "processing".
        self.stdout.write(self.style.WARNING("  Scanning for stuck videos..."))
        
        stuck_videos = Video.objects.filter(ocr_transcript_status='processing')
        count = stuck_videos.count()
        if count > 0:
            stuck_videos.update(ocr_transcript_status='pending')
            self.stdout.write(self.style.SUCCESS(f'  [✓] Reset {count} videos from "processing" -> "pending".'))
        else:
            self.stdout.write('  [-] No stuck videos found.')

        self.stdout.write(self.style.SUCCESS('\nSystem Ready. You can now run "python manage.py run_ocr" again.'))