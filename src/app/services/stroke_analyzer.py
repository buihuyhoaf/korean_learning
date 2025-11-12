"""
ML-based stroke analyzer service using TensorFlow Lite
Handles preprocessing, model inference, and prediction with minimal memory footprint
"""
import logging
import time
from typing import Optional, Tuple, List
from threading import Lock
import numpy as np  # type: ignore[import-not-found]
from PIL import Image, ImageDraw
import io
import base64

logger = logging.getLogger(__name__)

# Hangul character labels (should match model training)
HANGUL_CHARS = [
    "가", "나", "다", "라", "마", "바", "사", "아", "자", "차",
    "카", "타", "파", "하", "거", "너", "더", "러", "머", "버",
    "서", "어", "저", "처", "커", "터", "퍼", "허", "고", "노",
    "도", "로", "모", "보", "소", "오", "조", "초", "코", "토",
    "포", "호", "구", "누", "두", "루", "무", "부", "수", "우",
    "주", "추", "쿠", "투", "푸", "후", "그", "느", "드", "르",
    "므", "브", "스", "으", "즈", "츠", "크", "트", "프", "흐",
    "기", "니", "디", "리", "미", "비", "시", "이", "지", "치",
    "키", "티", "피", "히", "ㅏ", "ㅑ", "ㅓ", "ㅕ", "ㅗ", "ㅛ",
    "ㅜ", "ㅠ", "ㅡ", "ㅣ", "ㄱ", "ㄴ", "ㄷ", "ㄹ", "ㅁ", "ㅂ",
    "ㅅ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"
]


class StrokeAnalyzer:
    """
    Service for analyzing hand-drawn Hangul strokes using TensorFlow Lite model.
    Thread-safe lazy loading with mock fallback for development/testing.
    """
    
    def __init__(self):
        self.interpreter = None
        self.model_loaded = False
        self.inference_times = []
        self._use_mock = False
        self.image_size: Tuple[int, int] = (28, 28)  # (width, height)
        self.input_channels: int = 1
    
    def load_model(self, model_path: Optional[str] = None):
        """
        Load TensorFlow Lite model (lazy loading on first use).
        
        Args:
            model_path: Path to .tflite model file. If None, uses env var or default.
        """
        try:
            from ..ml.tflite_loader import get_tflite_model
            
            # Lazy load TFLite model (thread-safe)
            self.interpreter = get_tflite_model(allow_mock=True)
            
            if self.interpreter is None:
                self._use_mock = True
                self.model_loaded = False
                logger.warning("TFLite model not available, using mock mode")
            else:
                self._use_mock = False
                self.model_loaded = True
                logger.info("TFLite model loaded successfully")
                try:
                    input_details = self.interpreter.get_input_details()
                    if input_details:
                        shape = input_details[0].get("shape")
                        if shape is not None and len(shape) >= 3:
                            height = int(shape[1]) if int(shape[1]) > 0 else self.image_size[1]
                            width = int(shape[2]) if int(shape[2]) > 0 else self.image_size[0]
                            self.image_size = (width, height)
                        if shape is not None and len(shape) >= 4 and int(shape[3]) > 0:
                            self.input_channels = int(shape[3])
                    logger.info(
                        "Configured stroke analyzer input: %sx%s (channels=%s)",
                        self.image_size[0],
                        self.image_size[1],
                        self.input_channels,
                    )
                except Exception as shape_error:
                    logger.warning("Could not determine TFLite input shape: %s", shape_error)
                
        except Exception as e:
            logger.error(f"Failed to load TFLite model: {e}")
            self._use_mock = True
            self.model_loaded = False
            logger.warning("Using mock mode for inference")
    
    def preprocess_points(
        self,
        points: List[List[float]],
        image_size: Optional[Tuple[int, int]] = None,
    ) -> np.ndarray:
        """
        Preprocess stroke points into normalized image
        
        Args:
            points: List of [x, y] coordinates
            image_size: Target image size (width, height)
            
        Returns:
            Normalized grayscale image as numpy array (28, 28, 1)
        """
        size = image_size or self.image_size
        width, height = size

        if not points or len(points) < 2:
            return np.zeros((height, width, self.input_channels), dtype=np.float32)
        
        # Convert to numpy array
        points_array = np.array(points, dtype=np.float32)
        
        # Normalize coordinates to [0, 1]
        min_x, min_y = points_array.min(axis=0)
        max_x, max_y = points_array.max(axis=0)
        
        # Handle edge case where all points are the same
        if max_x == min_x:
            max_x = min_x + 1
        if max_y == min_y:
            max_y = min_y + 1
        
        # Normalize
        normalized_points = (points_array - np.array([min_x, min_y])) / np.array([
            max_x - min_x,
            max_y - min_y
        ])
        
        # Create image
        img = Image.new('L', size, 0)  # Black background
        draw = ImageDraw.Draw(img)
        
        # Scale to image size
        scaled_points = [
            (
                min(max(int(p[0] * width), 0), width - 1),
                min(max(int(p[1] * height), 0), height - 1),
            )
            for p in normalized_points
        ]
        
        # Draw lines between points
        for i in range(len(scaled_points) - 1):
            draw.line(
                [scaled_points[i], scaled_points[i + 1]],
                fill=255,  # White stroke
                width=2
            )
        
        # Convert to numpy array and normalize to [0, 1]
        img_array = np.array(img, dtype=np.float32) / 255.0
        
        if self.input_channels > 1:
            img_array = np.stack([img_array] * self.input_channels, axis=-1)
        else:
            img_array = img_array.reshape(height, width, 1)
        
        return img_array.astype(np.float32)
    
    def preprocess_image_base64(self, image_base64: str) -> np.ndarray:
        """
        Preprocess base64 encoded image
        
        Args:
            image_base64: Base64 encoded image string
            
        Returns:
            Preprocessed image array (28, 28, 1)
        """
        try:
            # Decode base64
            image_data = base64.b64decode(image_base64)
            img = Image.open(io.BytesIO(image_data))
            
            # Convert to grayscale
            if img.mode != 'L':
                img = img.convert('L')
            
            # Resize to expected input size
            img = img.resize(self.image_size, Image.Resampling.LANCZOS)
            
            # Convert to numpy array and normalize
            img_array = np.array(img, dtype=np.float32) / 255.0
            
            if self.input_channels > 1:
                if img_array.ndim == 2:
                    img_array = np.stack([img_array] * self.input_channels, axis=-1)
                elif img_array.shape[-1] != self.input_channels:
                    img_array = np.repeat(img_array[..., :1], self.input_channels, axis=-1)
            else:
                if img_array.ndim == 2:
                    img_array = img_array.reshape(self.image_size[1], self.image_size[0], 1)
                else:
                    img_array = img_array[..., :1]
            
            return img_array.astype(np.float32)
        except Exception as e:
            logger.error(f"Error preprocessing base64 image: {e}")
            height = self.image_size[1]
            width = self.image_size[0]
            return np.zeros((height, width, self.input_channels), dtype=np.float32)
    
    def predict(self, input_data: np.ndarray) -> Tuple[str, float]:
        """
        Run model inference using TFLite or mock mode
        
        Args:
            input_data: Preprocessed image array (28, 28, 1)
            
        Returns:
            Tuple of (predicted_char, confidence)
        """
        start_time = time.time()
        
        try:
            # Ensure model is loaded (lazy loading)
            if not self.model_loaded and self.interpreter is None:
                self.load_model()
            
            if self._use_mock or self.interpreter is None:
                # Mock prediction for development/testing (lightweight, <10MB)
                predicted_char, confidence = self._mock_predict(input_data)
            else:
                # Run actual TFLite inference
                from ..ml.tflite_loader import predict_tflite
                predicted_char, confidence = predict_tflite(self.interpreter, input_data)
            
            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)
            logger.info(f"Inference time: {inference_time:.3f}s")
            
            return predicted_char, confidence
            
        except Exception as e:
            logger.error(f"Prediction error: {e}", exc_info=True)
            # Fallback to mock on error
            return self._mock_predict(input_data)
    
    def _mock_predict(self, input_data: np.ndarray) -> Tuple[str, float]:
        """
        Mock prediction for development/testing.
        Lightweight implementation (<10MB memory) with stable predictions.
        
        Args:
            input_data: Preprocessed image array
            
        Returns:
            Tuple of (predicted_char, confidence)
        """
        # Simple heuristic: based on stroke density and pattern
        stroke_density = np.sum(input_data > 0.5) / input_data.size
        
        # Stable mock predictions based on density
        if stroke_density < 0.05:
            return "?", 0.3
        elif stroke_density < 0.15:
            # Simple characters (vowels)
            return "ㅏ", 0.75
        elif stroke_density < 0.25:
            # Basic syllables
            return "가", 0.82
        elif stroke_density < 0.35:
            # Medium complexity
            return "나", 0.78
        else:
            # Complex characters
            return "다", 0.80
    
    def analyze_stroke(
        self,
        points: Optional[List[List[float]]] = None,
        image_base64: Optional[str] = None,
        target_char: Optional[str] = None
    ) -> Tuple[str, float, str]:
        """
        Main analysis method
        
        Args:
            points: List of stroke points
            image_base64: Base64 encoded image
            target_char: Target character (optional, for comparison)
            
        Returns:
            Tuple of (predicted_char, confidence, message)
        """
        # Preprocess input
        if points:
            input_data = self.preprocess_points(points)
        elif image_base64:
            input_data = self.preprocess_image_base64(image_base64)
        else:
            return "?", 0.0, "No input data provided"
        
        # Run prediction
        predicted_char, confidence = self.predict(input_data)
        
        # Generate message
        message = self._generate_message(predicted_char, confidence, target_char)
        
        return predicted_char, confidence, message
    
    def _generate_message(
        self,
        predicted_char: str,
        confidence: float,
        target_char: Optional[str] = None
    ) -> str:
        """Generate human-readable message"""
        if target_char:
            if predicted_char == target_char:
                if confidence >= 0.9:
                    return "Perfect match! Excellent drawing."
                elif confidence >= 0.75:
                    return "Good match! Well done."
                else:
                    return "Correct character, but try to improve accuracy."
            else:
                return f"Predicted: {predicted_char}, but target was {target_char}. Try again!"
        else:
            if confidence >= 0.9:
                return "High confidence prediction."
            elif confidence >= 0.75:
                return "Good confidence prediction."
            elif confidence >= 0.5:
                return "Moderate confidence. Try drawing more clearly."
            else:
                return "Low confidence. Please draw more clearly."


# Global instance with thread-safe lazy loading
_stroke_analyzer: Optional[StrokeAnalyzer] = None
_analyzer_lock = Lock()


def get_stroke_analyzer() -> StrokeAnalyzer:
    """
    Get or create global stroke analyzer instance.
    Thread-safe singleton pattern.
    """
    global _stroke_analyzer
    
    if _stroke_analyzer is None:
        with _analyzer_lock:
            # Double-check after acquiring lock
            if _stroke_analyzer is None:
                _stroke_analyzer = StrokeAnalyzer()
                logger.debug("Created new StrokeAnalyzer instance")
    
    return _stroke_analyzer
