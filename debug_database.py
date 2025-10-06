import os
import django

# Set up the Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incuisenix.settings')
django.setup()

# Import your models AFTER setting up Django
from core.models import Video
from transcripts.models import Transcript

def check_database_integrity():
    """
    This script checks if every video in the database has a corresponding transcript.
    """
    print("--- Starting Database Integrity Check ---")
    
    all_videos = Video.objects.all()
    
    if not all_videos.exists():
        print("No videos found in the database. Please run 'python manage.py load_courses' first.")
        return

    print(f"Found {all_videos.count()} videos. Checking for linked transcripts...\n")
    
    found_issues = False
    
    for video in all_videos:
        try:
            # The exact same query your application uses
            Transcript.objects.get(video=video)
            print(f"✅ SUCCESS: Transcript found for Video ID: {video.id} ('{video.title}')")
        except Transcript.DoesNotExist:
            print(f"❌ FAILED: No transcript is linked to Video ID: {video.id} ('{video.title}')")
            found_issues = True
            
    print("\n--- Check Complete ---")
    if found_issues:
        print("\n🔴 Found one or more issues. This confirms the database relationship is broken.")
        print("   The recommended solution is to reset your database and reload your data.")
    else:
        print("\n🟢 No issues found. All videos have a correctly linked transcript.")

if __name__ == "__main__":
    check_database_integrity()