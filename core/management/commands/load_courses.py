import json
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import Course, Video

class Command(BaseCommand):
    help = 'Loads courses and videos from a JSON file into the database'

    def handle(self, *args, **kwargs):
        json_file_path = settings.BASE_DIR / 'courses.json'
        
        with open(json_file_path, 'r') as f:
            courses_data = json.load(f)

        for course_data in courses_data:
            course, created = Course.objects.update_or_create(
                course_id=course_data['course_id'],
                defaults={
                    'title': course_data['title'],
                    'description': course_data['description'],
                    'image_url': course_data['image_url'],
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created course "{course.title}"'))
            else:
                self.stdout.write(self.style.WARNING(f'Updated existing course "{course.title}"'))

            for video_data in course_data['videos']:
                Video.objects.update_or_create(
                    video_id=video_data['video_id'],
                    defaults={
                        'title': video_data['title'],
                        'video_url': video_data['video_url'],
                        'course': course,
                    }
                )
        self.stdout.write(self.style.SUCCESS('Finished loading all courses and videos.'))