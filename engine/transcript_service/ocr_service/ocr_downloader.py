import os
import glob
import yt_dlp
import uuid
import logging
import time
import random
from django.conf import settings

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self):
        self.temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_videos')
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def _clean_url(self, url: str) -> str:
        """
        Forces all URLs to be standard 'watch' URLs.
        Avoids 'embed' or 'player' links which cause 403 Forbidden errors.
        """
        # --- VIMEO LOGIC ---
        # Convert 'player.vimeo.com/video/123' -> 'https://vimeo.com/123'
        if "player.vimeo.com/video/" in url:
            video_id = url.split('player.vimeo.com/video/')[-1].split('?')[0]
            return f"https://vimeo.com/{video_id}"
        
        # Ensure standard 'vimeo.com/123' (remove query params)
        if "vimeo.com/" in url and "player." not in url:
            return url.split('?')[0]

        # --- YOUTUBE LOGIC ---
        # Convert 'youtube.com/embed/123' -> 'https://www.youtube.com/watch?v=123'
        if "youtube.com/embed/" in url:
            video_id = url.split("youtube.com/embed/")[-1].split('?')[0]
            return f"https://www.youtube.com/watch?v={video_id}"
            
        # Convert 'youtu.be/123' -> 'https://www.youtube.com/watch?v=123'
        if "youtu.be/" in url:
             video_id = url.split("youtu.be/")[-1].split('?')[0]
             return f"https://www.youtube.com/watch?v={video_id}"

        # Standard YouTube links: just strip extra query params (keep 'v')
        if "youtube.com/watch" in url:
            if "&" in url:
                return url.split('&')[0] # Keep only the first param (v=ID)
            return url
            
        return url

    def download_video(self, url: str) -> str:
        # 1. Stagger downloads to prevent rate-limit blocks
        sleep_time = random.uniform(2, 5)
        logger.info(f"Downloader: Sleeping for {sleep_time:.2f}s...")
        time.sleep(sleep_time)

        cleaned_url = self._clean_url(url)
        unique_name = str(uuid.uuid4())
        # We use a UUID filename so we can find it regardless of the extension yt-dlp chooses
        # NOTE: The post-processor will force this to be .mp4
        output_template = os.path.join(self.temp_dir, f"{unique_name}.%(ext)s")

        # --- NEW LOGIC: Dynamic Referer & Transcoding ---
        vimeo_referer = os.getenv('VIMEO_REFERER', 'https://vimeo.com/')

        ydl_opts = {
            # OPTIMIZATION: Prioritize video-only streams (bestvideo). 
            # We allow AV1 here because we will transcode it below.
            'format': 'bestvideo[height<=720]/best[height<=720]/best',
            
            # --- TRANSCODING LOGIC ---
            # This fixes the "AV1 not supported" crash in OpenCV by converting everything to H.264
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'postprocessor_args': {
                # Force video codec to libx264 (Standard H.264)
                # -crf 23: Balance between quality and file size
                # -preset fast: Faster encoding
                'ffmpeg': ['-c:v', 'libx264', '-crf', '23', '-preset', 'fast']
            },
            # -------------------------

            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'noplaylist': True,
            'nocheckcertificate': True,
            'sleep_interval': 3,
            'max_sleep_interval': 10,
            'ignoreerrors': False, # Crash on error so we know if authentication fails
        }

        # --- Platform Headers & Auth ---
        if "vimeo" in cleaned_url:
            logger.info(f"Downloader: Using Referer: {vimeo_referer}")
            ydl_opts['http_headers'] = {
                'Referer': vimeo_referer,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
            vimeo_username = os.getenv('VIMEO_USERNAME')
            vimeo_password = os.getenv('VIMEO_PASSWORD')
            if vimeo_username and vimeo_password:
                ydl_opts['username'] = vimeo_username
                ydl_opts['password'] = vimeo_password

        elif "youtube" in cleaned_url:
            # YouTube works BEST when we DO NOT provide a custom User-Agent.
            pass

        try:
            logger.info(f"Downloader: Downloading {cleaned_url} (Transcoding to H.264)")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(cleaned_url, download=True)
                
                # --- ROBUST FILE FINDER ---
                # Search for any file starting with the UUID. 
                # Note: It will almost certainly be .mp4 now due to conversion.
                search_pattern = os.path.join(self.temp_dir, f"{unique_name}.*")
                found_files = glob.glob(search_pattern)

                if found_files:
                    # Return the largest file (ignores small temp parts or thumbnails)
                    actual_file = max(found_files, key=os.path.getsize)
                    
                    # --- FIX: File Size Validation ---
                    if os.path.getsize(actual_file) == 0:
                        logger.error(f"Downloader: Downloaded file is empty (0 bytes): {actual_file}")
                        self.cleanup(actual_file)
                        return None
                    
                    logger.info(f"Downloader: Found valid file at {actual_file}")
                    return os.path.abspath(actual_file)
                else:
                    logger.error(f"Downloader: Download finished but no file found for ID {unique_name}")
                    return None

        except Exception as e:
            logger.error(f"Downloader: Failed to download {cleaned_url}. Error: {str(e)}")
            return None

    def cleanup(self, file_path: str):
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Downloader: Deleted temporary file {file_path}")
            except Exception as e:
                logger.warning(f"Downloader: Failed to delete {file_path}: {e}")