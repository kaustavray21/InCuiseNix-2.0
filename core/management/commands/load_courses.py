
import json
from django.core.management.base import BaseCommand
from django.db import connection
from core.models import Course, Video

class Command(BaseCommand):
    help = 'Loads courses and videos from a JSON file into the database.'

    def handle(self, *args, **options):
        self.stdout.write('Clearing all existing course-related data...')
        Video.objects.all().delete()
        Course.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Successfully cleared old data.'))

        self.stdout.write('Resetting database auto-increment counters...')
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE core_course AUTO_INCREMENT = 1;")
            cursor.execute("ALTER TABLE core_video AUTO_INCREMENT = 1;")
        self.stdout.write(self.style.SUCCESS('Successfully reset counters.'))

        try:
            with open('courses.json', 'r') as f:
                courses_data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('courses.json not found in the root directory.'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR('Error decoding courses.json. Please check its format.'))
            return

        for course_data in courses_data:
            # Use 'title' to find the course, as it's unique
            course, created = Course.objects.update_or_create(
                title=course_data['title'],
                defaults={
                    'description': course_data.get('description', ''),
                    'image_url': course_data.get('image_url', '')
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created course: "{course.title}"'))
            else:
                self.stdout.write(self.style.WARNING(f'Updated course: "{course.title}"'))

            for video_data in course_data.get('videos', []):
                # Use 'youtube_id' to find the video, as it's unique
                video, v_created = Video.objects.update_or_create(
                    youtube_id=video_data['video_id'],
                    defaults={
                        'course': course,
                        'title': video_data.get('title', 'Untitled Video'),
                        'video_url': f"https://www.youtube.com/watch?v={video_data['video_id']}"
                    }
                )
                if v_created:
                    self.stdout.write(f'  - Added video: "{video.title}"')

        self.stdout.write(self.style.SUCCESS('Finished loading all courses and videos.'))