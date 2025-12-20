import cv2
import os
import numpy as np
from typing import Generator, Tuple, Optional

class FrameExtractor:
    def __init__(self, sample_rate: int = 1):
        """
        Args:
            sample_rate (int): Capture one frame every 'sample_rate' seconds.
                               Defaults to 1 (one frame per second).
        """
        self.sample_rate = sample_rate

    def extract_frames(self, video_path: str) -> Generator[Tuple[float, np.ndarray], None, None]:
        """
        Yields frames from the video file at the specified sample rate.
        
        Args:
            video_path (str): Path to the input video file.
            
        Yields:
            Tuple[float, np.ndarray]: (timestamp_in_seconds, frame_image_array)
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Calculate frame interval (how many frames to skip to match sample_rate)
        # e.g., if FPS is 30 and sample_rate is 1s, we read every 30th frame.
        frame_interval = int(fps * self.sample_rate)
        if frame_interval == 0:
            frame_interval = 1 # Safety check for very low fps or high sample rates

        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                
                if not ret:
                    break

                # Only process frames at the specific interval
                if frame_count % frame_interval == 0:
                    # Calculate current timestamp in seconds
                    timestamp = frame_count / fps
                    yield timestamp, frame

                frame_count += 1
                
        finally:
            cap.release()

    def extract_to_dir(self, video_path: str, output_dir: str) -> int:
        """
        Helper method to save extracted frames to a directory (useful for debugging).
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        count = 0
        for timestamp, frame in self.extract_frames(video_path):
            filename = os.path.join(output_dir, f"frame_{timestamp:.2f}.jpg")
            cv2.imwrite(filename, frame)
            count += 1
            
        return count