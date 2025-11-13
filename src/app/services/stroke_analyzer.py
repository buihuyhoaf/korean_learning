"""
ML-based stroke analyzer service using TensorFlow or TensorFlow Lite
Handles preprocessing, model inference, and prediction with minimal memory footprint
"""
import base64
import io
import logging
import os
import time
from pathlib import Path
from threading import Lock
from typing import List, Optional, Tuple

import numpy as np  # type: ignore[import-not-found]
from PIL import Image, ImageDraw

from ..ml.tflite_loader import predict_top_k
from ..utils.hangul import split_hangul

logger = logging.getLogger(__name__)


class StrokeAnalyzer:
    """Service for analyzing hand-drawn Hangul strokes using TensorFlow or TensorFlow Lite."""
    
    def __init__(self) -> None:
        self.interpreter = None  # For TFLite
        self.model = None  # For TensorFlow Keras/SavedModel
        self.model_loaded = False
        self.model_type: Optional[str] = None  # 'tf_keras' or 'tflite'
        self.inference_times: list[float] = []
        self._use_mock = False
        self.image_size: Tuple[int, int] = (28, 28)  # Default, will be auto-detected
        self.input_channels: int = 1
        self.top_k: int = 5
    
    def load_model(self, model_path: Optional[str] = None) -> None:
        """Lazy-load the model - TensorFlow Keras/SavedModel first if available, then TFLite fallback."""
        
        from ..core.config import settings
        
        # Get model path from config or use default
        if model_path is None:
            model_path = settings.STROKE_MODEL_PATH
            if model_path is None:
                # Try TensorFlow SavedModel/Keras first, then TFLite
                default_tf = Path(__file__).parent.parent.parent / "models" / "hangul_cnn_model"
                default_tflite = Path(__file__).parent.parent.parent / "models" / "hangul_stroke_model.tflite"
                
                if default_tf.exists() and default_tf.is_dir():
                    model_path = str(default_tf)
                elif default_tflite.exists():
                    model_path = str(default_tflite)
                else:
                    model_path = str(default_tf)  # Default to TensorFlow SavedModel path
        
        # Try TensorFlow Keras/SavedModel first (if it's a directory or .h5 file)
        is_tf_model = (
            (os.path.isdir(model_path) and not model_path.endswith('.tflite')) or
            model_path.endswith('.h5') or
            model_path.endswith('.keras')
        )
        
        if is_tf_model:
            try:
                from ..ml.model_loader import load_model
                
                if os.path.exists(model_path):
                    self.model = load_model(model_path=model_path, allow_mock=True)
                    
                    if self.model is not None and not hasattr(self.model, '_is_mock'):
                        self.model_type = 'tf_keras'
                        self._use_mock = False
                        self.model_loaded = True
                        # TensorFlow model typically uses 64x64 for IBM model
                        self.image_size = (64, 64)
                        
                        logger.info("TensorFlow Keras/SavedModel loaded successfully")
                        logger.info(f"Model path: {model_path}")
                        return
            except Exception as exc:
                logger.warning(f"Failed to load TensorFlow model: {exc}")
                logger.debug("Falling back to TFLite...")
        
        # Fallback to TFLite
        try:
            from ..ml.tflite_loader import get_tflite_model
            
            self.interpreter = get_tflite_model(allow_mock=True)
            
            if self.interpreter is not None:
                self.model_type = 'tflite'
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
                        "Configured stroke analyzer input: %sx%s (channels=%s) - TFLite",
                        self.image_size[0],
                        self.image_size[1],
                        self.input_channels,
                    )
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.warning("Could not determine TFLite input shape: %s", exc)
                return
        except Exception as exc:
            logger.debug(f"TFLite model not available: {exc}")
        
        # No model available
        self._use_mock = True
        self.model_loaded = False
        self.model_type = None
        logger.warning("No model available, using mock mode")
    
    def preprocess_points(
        self,
        points: List[List[float]],
        image_size: Optional[Tuple[int, int]] = None,
    ) -> np.ndarray:
        """Rasterise stroke points into a grayscale image."""

        size = image_size or self.image_size
        width, height = size

        if not points or len(points) < 2:
            return np.zeros((height, width, self.input_channels), dtype=np.float32)
        
        points_array = np.array(points, dtype=np.float32)
        min_x, min_y = points_array.min(axis=0)
        max_x, max_y = points_array.max(axis=0)
        
        if max_x == min_x:
            max_x = min_x + 1
        if max_y == min_y:
            max_y = min_y + 1
        
        normalized_points = (points_array - np.array([min_x, min_y])) / np.array(
            [max_x - min_x, max_y - min_y]
        )
        
        img = Image.new("L", size, 0)
        draw = ImageDraw.Draw(img)
        
        scaled_points = [
            (
                min(max(int(p[0] * width), 0), width - 1),
                min(max(int(p[1] * height), 0), height - 1),
            )
            for p in normalized_points
        ]
        
        for index in range(len(scaled_points) - 1):
            draw.line(
                [scaled_points[index], scaled_points[index + 1]],
                fill=255,
                width=2,
            )
        
        img_array = np.array(img, dtype=np.float32) / 255.0
        
        if self.input_channels > 1:
            img_array = np.stack([img_array] * self.input_channels, axis=-1)
        else:
            img_array = img_array.reshape(height, width, 1)
        
        return img_array.astype(np.float32)
    
    def preprocess_image_base64(self, image_base64: str) -> np.ndarray:
        """Decode a base64 image and resize it for inference."""

        try:
            image_data = base64.b64decode(image_base64)
            img = Image.open(io.BytesIO(image_data))
            
            if img.mode != "L":
                img = img.convert("L")
            
            img = img.resize(self.image_size, Image.Resampling.LANCZOS)
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
        except Exception as exc:
            logger.error("Error preprocessing base64 image: %s", exc)
            return np.zeros(
                (self.image_size[1], self.image_size[0], self.input_channels),
                dtype=np.float32,
            )
    
    def predict(
        self,
        input_data: np.ndarray,
    ) -> Tuple[str, float, list[dict[str, object]]]:
        """Run inference and return the best prediction together with top-k."""

        start_time = time.time()
        
        try:
            if not self.model_loaded:
                self.load_model()

            if self._use_mock or not self.model_loaded:
                predicted_char, confidence, top_predictions = self._mock_predict(input_data)
            elif self.model_type == 'tf_keras':
                # Use TensorFlow Keras/SavedModel
                from ..ml.preprocessor import unicode_to_char
                
                batched_input = (
                    input_data
                    if input_data.ndim == 4
                    else np.expand_dims(input_data, axis=0)
                )
                
                # Log input info for debugging
                logger.info(f"Model type: {self.model_type}")
                logger.info(f"Image size: {self.image_size}")
                logger.info(f"Input shape: {batched_input.shape}")
                
                predictions = self.model.predict(batched_input, verbose=0)
                
                # Log predictions info for debugging
                logits = predictions[0]
                logger.info(f"Predictions shape: {predictions.shape}")
                logger.info(f"Predictions min/max/sum: {logits.min():.4f} / {logits.max():.4f} / {np.sum(logits):.4f}")
                
                # Apply softmax if output is logits (not probabilities)
                # Check if values are outside [0, 1] range or sum is not close to 1.0
                if logits.min() < 0 or logits.max() > 1.0 or abs(np.sum(logits) - 1.0) > 0.1:
                    # Likely logits, apply softmax
                    exp_logits = np.exp(logits - np.max(logits))  # Numerical stability
                    probabilities = exp_logits / np.sum(exp_logits)
                    logger.info("Applied softmax to convert logits to probabilities")
                else:
                    # Already probabilities
                    probabilities = logits
                    logger.info("Using predictions as probabilities (no softmax needed)")
                
                # Get top prediction
                predicted_idx = int(np.argmax(probabilities))
                confidence = float(probabilities[predicted_idx])
                predicted_char = unicode_to_char(predicted_idx)
                
                # Get top-k predictions
                top_k_indices = np.argsort(probabilities)[-self.top_k:][::-1]
                top_predictions = [
                    {
                        "index": int(idx),
                        "char": unicode_to_char(int(idx)),
                        "confidence": float(probabilities[idx])
                    }
                    for idx in top_k_indices
                ]
                
                # Log top predictions for debugging
                logger.info(f"Top {self.top_k} indices: {top_k_indices}")
                logger.info(f"Top {self.top_k} confidences: {[probabilities[idx] for idx in top_k_indices]}")
                logger.info(f"Predicted char: {predicted_char} (confidence: {confidence:.4f})")
            elif self.model_type == 'tflite':
                # Use TFLite
                batched_input = (
                    input_data
                    if input_data.ndim == 4
                    else np.expand_dims(input_data, axis=0)
                )
                top_predictions = predict_top_k(self.interpreter, batched_input, self.top_k)
                if top_predictions:
                    best = top_predictions[0]
                    predicted_char = str(best.get("char", "?"))
                    confidence = float(best.get("confidence", 0.0))
                else:
                    predicted_char, confidence = "?", 0.0
            else:
                predicted_char, confidence, top_predictions = self._mock_predict(input_data)
            
            inference_time = time.time() - start_time
            self.inference_times.append(inference_time)
            logger.info("Inference time: %.3fs", inference_time)
            
            return predicted_char, confidence, top_predictions
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Prediction error: %s", exc, exc_info=True)
            return self._mock_predict(input_data)
    
    def _mock_predict(
        self,
        input_data: np.ndarray,
    ) -> Tuple[str, float, list[dict[str, object]]]:
        """Fallback mock prediction based on stroke density."""

        stroke_density = np.sum(input_data > 0.5) / input_data.size
        if stroke_density < 0.05:
            char, confidence = "?", 0.3
        elif stroke_density < 0.15:
            char, confidence = "ㅏ", 0.75
        elif stroke_density < 0.25:
            char, confidence = "가", 0.82
        elif stroke_density < 0.35:
            char, confidence = "나", 0.78
        else:
            char, confidence = "다", 0.80

        return char, confidence, [{"index": 0, "char": char, "confidence": confidence}]
    
    def analyze_stroke(
        self,
        points: Optional[List[List[float]]] = None,
        image_base64: Optional[str] = None,
        target_char: Optional[str] = None,
    ) -> dict[str, object]:
        """Analyze provided stroke input and return a structured breakdown."""

        if not self.model_loaded:
            self.load_model()

        if image_base64:
            input_data = self.preprocess_image_base64(image_base64)
        elif points:
            input_data = self.preprocess_points(points)
        else:
            return {
                "predicted_char": "?",
                "confidence": 0.0,
                "message": "No input data provided",
                "top_predictions": [],
            }

        return self.predict_and_describe(input_data)

    def predict_and_describe(
        self,
        input_data: np.ndarray,
    ) -> dict[str, object]:
        predicted_char, confidence, top_predictions = self.predict(input_data)
        split = split_hangul(predicted_char)
        message = self._generate_message(
            predicted_char=predicted_char,
            confidence=confidence,
            choseong=split.choseong,
            jungseong=split.jungseong,
            jongseong=split.jongseong,
        )
        
        return {
            "predicted_char": predicted_char,
            "confidence": confidence,
            "message": message,
            "top_predictions": top_predictions,
        }
    
    def _generate_message(
        self,
        predicted_char: str,
        confidence: float,
        choseong: str,
        jungseong: str,
        jongseong: str,
    ) -> str:
        syllable_breakdown = f"{choseong}{jungseong}{jongseong}".strip()
        if confidence >= 0.9:
            return f"Mô hình rất tự tin đây là {predicted_char} ({syllable_breakdown})."
        if confidence >= 0.75:
            return f"Khá chắc chắn: {predicted_char}."
        if confidence >= 0.5:
            return f"Dự đoán {predicted_char}. Hãy tô nét rõ hơn để tăng độ tin cậy."
        return "Độ tin cậy thấp, hãy thử lại với nét to và đều hơn."


_stroke_analyzer: Optional[StrokeAnalyzer] = None
_analyzer_lock = Lock()


def get_stroke_analyzer() -> StrokeAnalyzer:
    """Get a global stroke analyzer instance (thread-safe singleton)."""

    global _stroke_analyzer
    
    if _stroke_analyzer is None:
        with _analyzer_lock:
            if _stroke_analyzer is None:
                _stroke_analyzer = StrokeAnalyzer()
                logger.debug("Created new StrokeAnalyzer instance")
    
    return _stroke_analyzer
