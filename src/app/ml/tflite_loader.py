"""
TensorFlow Lite model loader for Hangul character recognition.
Thread-safe lazy loading with minimal memory footprint (<100MB).
"""
import os
import logging
from pathlib import Path
from typing import Optional, TYPE_CHECKING
from threading import Lock
import numpy as np  # type: ignore[import-not-found]

# Lazy import TFLite runtime to save memory on startup
if TYPE_CHECKING:
    import tflite_runtime.interpreter as tflite  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)

# Global model cache
_loaded_interpreter: Optional[object] = None  # Type: tflite.Interpreter (lazy import)
_model_path: Optional[str] = None
_loading = False
_load_lock = Lock()  # Thread-safe lock for model loading
_input_details = None
_output_details = None
_labels_path: Optional[str] = None
_labels_loaded = False
_labels_lock = Lock()

# Hangul character labels (default fallback, should match model training)
_DEFAULT_HANGUL_CHARS = [
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
HANGUL_CHARS = _DEFAULT_HANGUL_CHARS.copy()


def load_tflite_model(model_path: Optional[str] = None, allow_mock: bool = True):
    """
    Load and cache TensorFlow Lite model for Hangul character recognition.
    Thread-safe implementation with lock to prevent race conditions.
    
    Args:
        model_path: Path to the .tflite model file. If None, uses default path or env var.
        allow_mock: If True, use mock mode when model fails. Default: True (safe fallback).
        
    Returns:
        TFLite Interpreter instance
        
    Raises:
        FileNotFoundError: If model file doesn't exist and allow_mock=False
        ValueError: If model cannot be loaded and allow_mock=False
    """
    # Lazy import TFLite runtime to save memory (only import when actually needed)
    try:
        import tflite_runtime.interpreter as tflite  # type: ignore[import-not-found]
    except ImportError:
        logger.error("tflite-runtime not installed. Install with: pip install tflite-runtime")
        if allow_mock:
            logger.warning("Falling back to mock mode")
            return None
        raise ImportError("tflite-runtime is required. Install with: pip install tflite-runtime")
    
    global _loaded_interpreter, _model_path, _loading, _input_details, _output_details
    
    # Get model path from env var or use default
    if model_path is None:
        from ..core.config import settings
        model_path = settings.STROKE_MODEL_PATH
        
        if model_path is None:
            # Default path: models/hangul_stroke_model.tflite
            default_path = Path(__file__).parent.parent / "models" / "hangul_stroke_model.tflite"
            model_path = str(default_path)
    
    # Fast path: return cached interpreter if already loaded (no lock needed for read)
    if _loaded_interpreter is not None and _model_path == model_path:
        logger.debug("Returning cached TFLite model")
        return _loaded_interpreter
    
    # Thread-safe loading with lock
    with _load_lock:
        # Double-check after acquiring lock (another thread might have loaded it)
        if _loaded_interpreter is not None and _model_path == model_path:
            logger.debug("TFLite model loaded by another thread, returning cached")
            return _loaded_interpreter
        
        # Check if another thread is currently loading
        if _loading:
            logger.warning("Another thread is loading TFLite model, waiting...")
            import time
            for _ in range(50):  # Wait up to 5 seconds
                time.sleep(0.1)
                if _loaded_interpreter is not None:
                    logger.info("TFLite model loaded by another thread after waiting")
                    return _loaded_interpreter
            logger.warning("Timeout waiting for TFLite model load, proceeding with fallback")
        
        # Mark as loading
        _loading = True
        
        try:
            # Check if model exists
            if not os.path.exists(model_path):
                logger.warning(f"TFLite model not found at {model_path}")
                if allow_mock:
                    logger.info("Using mock mode as fallback")
                    _loaded_interpreter = None
                    _model_path = model_path
                    return None
                else:
                    raise FileNotFoundError(
                        f"TFLite model not found at {model_path}. "
                        f"Set STROKE_MODEL_PATH environment variable or set allow_mock=True."
                    )
            
            # Load real TFLite model
            try:
                logger.info(f"Loading TFLite model from {model_path}")
                interpreter = tflite.Interpreter(model_path=model_path)
                interpreter.allocate_tensors()
                
                # Get input and output details
                _input_details = interpreter.get_input_details()
                _output_details = interpreter.get_output_details()
                
                logger.info(f"TFLite model loaded successfully")
                logger.info(f"Input shape: {_input_details[0]['shape']}")
                logger.info(f"Output shape: {_output_details[0]['shape']}")

                _ensure_labels_loaded()
                
                _loaded_interpreter = interpreter
                _model_path = model_path
                return interpreter
            except Exception as e:
                logger.error(f"Error loading TFLite model: {e}")
                if allow_mock:
                    logger.warning("Falling back to mock mode")
                    _loaded_interpreter = None
                    _model_path = model_path
                    return None
                else:
                    raise ValueError(f"Failed to load TFLite model: {e}") from e
        finally:
            _loading = False


def get_tflite_model(allow_mock: bool = True):
    """
    Get the currently loaded TFLite model.
    Thread-safe lazy loading with lock if model not yet loaded.
    
    Args:
        allow_mock: If True, return None (mock mode) when real model fails. Default: True.
    
    Returns:
        TFLite Interpreter instance or None (for mock mode)
    """
    if _loaded_interpreter is None:
        return load_tflite_model(allow_mock=allow_mock)
    return _loaded_interpreter


def predict_tflite(interpreter, input_data: np.ndarray) -> tuple[str, float]:
    """
    Run inference using TFLite interpreter.
    
    Args:
        interpreter: TFLite Interpreter instance
        input_data: Preprocessed image array (28, 28, 1) or (1, 28, 28, 1)
        
    Returns:
        Tuple of (predicted_char, confidence)
    """
    global _input_details, _output_details
    
    # Ensure input is in correct shape
    if len(input_data.shape) == 3:
        input_data = np.expand_dims(input_data, axis=0)  # Add batch dimension
    
    # Get input/output details if not cached
    if _input_details is None:
        _input_details = interpreter.get_input_details()
        _output_details = interpreter.get_output_details()
    
    # Get input tensor index and set input
    input_index = _input_details[0]['index']
    interpreter.set_tensor(input_index, input_data.astype(np.float32))
    
    # Run inference
    interpreter.invoke()
    
    # Get output
    output_index = _output_details[0]['index']
    predictions = interpreter.get_tensor(output_index)
    predictions = np.asarray(predictions)
    if predictions.ndim == 0:
        predictions = predictions.reshape(1)
    if predictions.ndim == 1:
        predictions = np.expand_dims(predictions, axis=0)
    
    # Get top prediction
    logits = predictions[0].astype(np.float32)
    predicted_idx = int(np.argmax(logits))

    # Convert logits to probabilities with stable softmax
    logits_stable = logits - np.max(logits)
    exp_logits = np.exp(logits_stable)
    sum_exp = np.sum(exp_logits)
    if sum_exp <= 0 or np.isnan(sum_exp) or np.isinf(sum_exp):
        probabilities = np.full_like(exp_logits, 1.0 / exp_logits.size)
    else:
        probabilities = exp_logits / sum_exp

    confidence = float(probabilities[predicted_idx])
    if np.isnan(confidence) or np.isinf(confidence):
        confidence = 0.0
    confidence = float(max(0.0, min(1.0, confidence)))
    
    # Map to Hangul character
    if predicted_idx < len(HANGUL_CHARS):
        predicted_char = HANGUL_CHARS[predicted_idx]
    else:
        predicted_char = "?"
        logger.warning(f"Predicted index {predicted_idx} out of range for HANGUL_CHARS")
    
    return predicted_char, confidence


def clear_cache():
    """Clear the TFLite model cache (useful for testing or reloading). Thread-safe."""
    global _loaded_interpreter, _model_path, _loading, _input_details, _output_details, _labels_loaded, _labels_path
    with _load_lock:
        _loaded_interpreter = None
        _model_path = None
        _loading = False
        _input_details = None
        _output_details = None
    with _labels_lock:
        _labels_loaded = False
        _labels_path = None
        HANGUL_CHARS[:] = _DEFAULT_HANGUL_CHARS
    logger.info("TFLite model cache cleared")


def _ensure_labels_loaded(label_path: Optional[str] = None):
    """
    Ensure stroke labels are loaded from file if provided; fall back to defaults.
    Thread-safe with its own lock.
    """
    global HANGUL_CHARS, _labels_loaded, _labels_path

    if _labels_loaded and (label_path is None or _labels_path == label_path):
        return

    with _labels_lock:
        if _labels_loaded and (label_path is None or _labels_path == label_path):
            return

        from ..core.config import settings

        resolved_path: Optional[str] = label_path or settings.STROKE_LABEL_PATH
        if resolved_path is None:
            default_path = Path(__file__).parent.parent / "models" / "hangul_labels.txt"
            resolved_path = str(default_path)

        if not resolved_path:
            logger.debug("No stroke label path configured; using default labels.")
            HANGUL_CHARS[:] = _DEFAULT_HANGUL_CHARS
            _labels_path = None
            _labels_loaded = True
            return

        try:
            label_file = Path(resolved_path)
            if not label_file.exists():
                logger.warning(
                    "Stroke label file not found at %s. Using default labels.", resolved_path
                )
                HANGUL_CHARS[:] = _DEFAULT_HANGUL_CHARS
                _labels_path = None
                _labels_loaded = True
                return

            content = label_file.read_text(encoding="utf-8")
            if not content.strip():
                raise ValueError("Label file is empty")

            lines = [line.strip() for line in content.replace("\r", "").splitlines() if line.strip()]
            if len(lines) == 1 and "," in lines[0]:
                labels = [item.strip() for item in lines[0].split(",") if item.strip()]
            else:
                labels = lines

            if not labels:
                raise ValueError("No labels parsed from file")

            HANGUL_CHARS[:] = labels
            _labels_path = resolved_path
            _labels_loaded = True
            logger.info(
                "Loaded %d stroke labels from %s.", len(labels), resolved_path
            )
        except Exception as exc:
            logger.error(
                "Failed to load stroke labels from %s: %s. Using default labels.",
                resolved_path,
                exc,
            )
            HANGUL_CHARS[:] = _DEFAULT_HANGUL_CHARS
            _labels_path = None
            _labels_loaded = True


def load_labels(label_path: Optional[str] = None) -> list[str]:
    """
    Public helper to ensure stroke labels are loaded from disk.
    Returns the current label list.
    """
    _ensure_labels_loaded(label_path)
    return HANGUL_CHARS

