import os
import yt_dlp
import uuid
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self):
        self.temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_videos')
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)

    def _clean_url(self, url: str) -> str:
        if "player.vimeo.com/video/" in url:
            return url.split('?')[0]
        
        if "vimeo.com/" in url and "player." not in url:
            video_id = url.split('/')[-1].split('?')[0]
            return f"https://player.vimeo.com/video/{video_id}"

        if "youtube.com/embed/" in url:
            url = url.replace("youtube.com/embed/", "youtube.com/watch?v=").split('?')[0]
            
        return url

    def download_video(self, url: str) -> str:
        cleaned_url = self._clean_url(url)
        unique_name = str(uuid.uuid4())
        output_template = os.path.join(self.temp_dir, f"{unique_name}.%(ext)s")

        ydl_opts = {
            'format': 'best[height<=720]/best',
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Referer': 'https://vimeo.com/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            },
            'nocheckcertificate': True,
        }

        try:
            logger.info(f"Downloader: Attempting to download {cleaned_url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(cleaned_url, download=True)
                filename = ydl.prepare_filename(info)
                
                if os.path.exists(filename):
                    return os.path.abspath(filename)
                else:
                    logger.error(f"Downloader: yt-dlp finished but file not found at {filename}")
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