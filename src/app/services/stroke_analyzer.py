"""
ML-based stroke analyzer service
Handles preprocessing, model inference, and prediction
"""
import logging
import time
from typing import Optional, Tuple, List
import numpy as np
from PIL import Image, ImageDraw
import io
import base64

logger = logging.getLogger(__name__)

# Mock Hangul character labels (in production, load from model)
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
    Service for analyzing hand-drawn Hangul strokes using ML model
    """
    
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.inference_times = []
    
    def load_model(self, model_path: Optional[str] = None):
        """
        Load ML model (TensorFlow Lite or ONNX)
        
        Args:
            model_path: Path to model file. If None, uses mock model.
        """
        try:
            # TODO: Load actual TensorFlow Lite or ONNX model
            # For now, use mock model
            if model_path:
                logger.info(f"Loading model from {model_path}")
                # self.model = load_tflite_model(model_path)
                # or
                # self.model = load_onnx_model(model_path)
                pass
            
            self.model_loaded = True
            logger.info("Model loaded successfully (mock mode)")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            self.model_loaded = False
            logger.info("Using mock model for inference")
    
    def preprocess_points(
        self,
        points: List[List[float]],
        image_size: Tuple[int, int] = (28, 28)
    ) -> np.ndarray:
        """
        Preprocess stroke points into normalized image
        
        Args:
            points: List of [x, y] coordinates
            image_size: Target image size (width, height)
            
        Returns:
            Normalized grayscale image as numpy array
        """
        if not points or len(points) < 2:
            return np.zeros(image_size, dtype=np.float32)
        
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
        img = Image.new('L', image_size, 0)  # Black background
        draw = ImageDraw.Draw(img)
        
        # Scale to image size
        scaled_points = [
            (
                int(p[0] * image_size[0]),
                int(p[1] * image_size[1])
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
        
        # Reshape for model input (28, 28, 1) or (1, 28, 28, 1)
        return img_array.reshape(*image_size, 1)
    
    def preprocess_image_base64(self, image_base64: str) -> np.ndarray:
        """
        Preprocess base64 encoded image
        
        Args:
            image_base64: Base64 encoded image string
            
        Returns:
            Preprocessed image array
        """
        try:
            # Decode base64
            image_data = base64.b64decode(image_base64)
            img = Image.open(io.BytesIO(image_data))
            
            # Convert to grayscale
            if img.mode != 'L':
                img = img.convert('L')
            
            # Resize to 28x28
            img = img.resize((28, 28), Image.Resampling.LANCZOS)
            
            # Convert to numpy array and normalize
            img_array = np.array(img, dtype=np.float32) / 255.0
            
            # Reshape for model input
            return img_array.reshape(28, 28, 1)
        except Exception as e:
            logger.error(f"Error preprocessing base64 image: {e}")
            return np.zeros((28, 28, 1), dtype=np.float32)
    
    def predict(self, input_data: np.ndarray) -> Tuple[str, float]:
        """
        Run model inference
        
        Args:
            input_data: Preprocessed image array
            
        Returns:
            Tuple of (predicted_char, confidence)
        """
        start_time = time.time()
        
        try:
            if self.model_loaded and self.model is not None:
                # Run actual model inference
                # predictions = self.model.predict(input_data)
                # predicted_idx = np.argmax(predictions)
                # confidence = float(predictions[0][predicted_idx])
                # predicted_char = HANGUL_CHARS[predicted_idx]
                pass
            else:
                # Mock prediction for development
                predicted_char, confidence = self._mock_predict(input_data)
            
            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)
            logger.info(f"Inference time: {inference_time:.3f}s")
            
            return predicted_char, confidence
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return "?", 0.0
    
    def _mock_predict(self, input_data: np.ndarray) -> Tuple[str, float]:
        """
        Mock prediction for development/testing
        Uses simple heuristics to return a prediction
        """
        # Simple heuristic: based on stroke density
        stroke_density = np.sum(input_data > 0.5) / input_data.size
        
        # Map density to character (mock logic)
        if stroke_density < 0.1:
            return "?", 0.3
        elif stroke_density < 0.2:
            # Simple characters
            return "ㅏ", 0.75
        elif stroke_density < 0.3:
            return "가", 0.82
        else:
            # Complex characters
            return "나", 0.78
    
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


# Global instance
_stroke_analyzer: Optional[StrokeAnalyzer] = None


def get_stroke_analyzer() -> StrokeAnalyzer:
    """Get or create global stroke analyzer instance"""
    global _stroke_analyzer
    if _stroke_analyzer is None:
        _stroke_analyzer = StrokeAnalyzer()
    return _stroke_analyzer

