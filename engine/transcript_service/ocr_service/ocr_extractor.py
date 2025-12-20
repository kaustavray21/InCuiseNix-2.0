import cv2
import numpy as np
import os
from PIL import Image
from typing import Union, List, Dict, Any, Optional
from paddleocr import PaddleOCR

class OCRExtractor:
    def __init__(self, lang: str = 'en', use_gpu: bool = False):
        """
        Initializes the PaddleOCR engine.
        
        Args:
            lang (str): Language code (e.g., 'en', 'ch').
            use_gpu (bool): Whether to use GPU for inference.
        """
        # Initialize PaddleOCR with angle classification
        # We suppress the debug logs to keep the console clean
        self.ocr_engine = PaddleOCR(
            use_angle_cls=True, 
            lang=lang, 
            use_gpu=use_gpu, 
            show_log=False
        )

    def _load_image(self, source: Union[str, np.ndarray, Image.Image]) -> np.ndarray:
        if isinstance(source, str):
            if not os.path.exists(source):
                raise FileNotFoundError(f"Image not found at path: {source}")
            return cv2.imread(source)
        elif isinstance(source, Image.Image):
            return cv2.cvtColor(np.array(source), cv2.COLOR_RGB2BGR)
        elif isinstance(source, np.ndarray):
            return source
        else:
            raise ValueError("Unsupported image source type")

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Basic preprocessing. Note: PaddleOCR is quite robust to raw images, 
        so aggressive thresholding (like in Tesseract) might actually hurt performance.
        We keep this simple or optional.
        """
        # Convert to grayscale might help, but Paddle handles color well.
        # We'll stick to returning the image as-is or doing minimal contrast adjustment if needed.
        # For now, we return the original image to let Paddle's internal net handle it.
        return image

    def extract_text(self, 
                     source: Union[str, np.ndarray, Image.Image], 
                     preprocess: bool = False) -> str:
        """
        Returns all detected text joined by newlines.
        """
        try:
            image = self._load_image(source)
            
            if preprocess:
                image = self._preprocess(image)
            
            # PaddleOCR.ocr expects a numpy array or file path
            # cls=True enables angle classification
            result = self.ocr_engine.ocr(image, cls=True)
            
            # PaddleOCR returns a list of results (one per image). 
            # Since we process one image, we take result[0].
            if not result or result[0] is None:
                return ""

            # result structure: [[[box], [text, confidence]], ...]
            extracted_lines = [line[1][0] for line in result[0]]
            
            return "\n".join(extracted_lines)
        
        except Exception as e:
            print(f"Error during OCR extraction: {str(e)}")
            return ""

    def extract_data(self, 
                     source: Union[str, np.ndarray, Image.Image], 
                     preprocess: bool = False) -> List[Dict[str, Any]]:
        """
        Returns detailed data including bounding boxes and confidence scores.
        Structure: [{'text': str, 'confidence': float, 'box': list}, ...]
        """
        try:
            image = self._load_image(source)
            
            if preprocess:
                image = self._preprocess(image)
                
            result = self.ocr_engine.ocr(image, cls=True)
            
            if not result or result[0] is None:
                return []

            structured_data = []
            for line in result[0]:
                box = line[0]
                text = line[1][0]
                confidence = line[1][1]
                
                structured_data.append({
                    'text': text,
                    'confidence': confidence,
                    'box': box
                })
                
            return structured_data
            
        except Exception as e:
            print(f"Error during OCR data extraction: {str(e)}")
            return []