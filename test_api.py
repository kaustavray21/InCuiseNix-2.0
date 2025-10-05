try:
    from youtube_transcript_api import YouTubeTranscriptApi
    
    # Check for the function that is causing the error
    api = YouTubeTranscriptApi()
    print("✅ SUCCESS: The youtube_transcript_api library is installed and can be imported correctly.")

except ImportError:
    print("❌ ERROR: The library could not be imported. It might not be installed correctly.")
except AttributeError as e:
    print(f"❌ ATTRIBUTE ERROR: The library was imported, but it is the wrong one. Error: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")