"""
Model loader for TensorFlow CNN model
Loads and caches the pre-trained model for Hangul character recognition
"""
import os
import logging
from pathlib import Path
from typing import Optional
from threading import Lock
import tensorflow as tf

logger = logging.getLogger(__name__)

# Global model cache
_loaded_model: Optional[tf.keras.Model] = None
_model_path: Optional[str] = None
_loading = False
_load_lock = Lock()  # Thread-safe lock for model loading


def load_model(model_path: Optional[str] = None, allow_mock: bool = True) -> tf.keras.Model:
    """
    Load and cache TensorFlow model for Hangul character recognition.
    Thread-safe implementation with lock to prevent race conditions.
    
    Args:
        model_path: Path to the saved model. If None, uses default path.
        allow_mock: If True, create mock model when real model fails. Default: True (safe fallback).
        
    Returns:
        Loaded TensorFlow model
        
    Raises:
        FileNotFoundError: If model file doesn't exist and allow_mock=False
        ValueError: If model cannot be loaded and allow_mock=False
    """
    global _loaded_model, _model_path, _loading
    
    # Use default path if not provided
    if model_path is None:
        # Default path: models/hangul_cnn_model/
        default_path = Path(__file__).parent.parent / "models" / "hangul_cnn_model"
        model_path = str(default_path)
    
    # Fast path: return cached model if already loaded (no lock needed for read)
    if _loaded_model is not None and _model_path == model_path:
        logger.debug("Returning cached model")
        return _loaded_model
    
    # Thread-safe loading with lock
    with _load_lock:
        # Double-check after acquiring lock (another thread might have loaded it)
        if _loaded_model is not None and _model_path == model_path:
            logger.debug("Model loaded by another thread, returning cached")
            return _loaded_model
        
        # Check if another thread is currently loading
        if _loading:
            logger.warning("Another thread is loading model, waiting...")
            # Wait a bit and check again
            import time
            for _ in range(50):  # Wait up to 5 seconds
                time.sleep(0.1)
                if _loaded_model is not None:
                    logger.info("Model loaded by another thread after waiting")
                    return _loaded_model
            logger.warning("Timeout waiting for model load, proceeding with fallback")
        
        # Mark as loading
        _loading = True
        
        try:
            # Check if model exists
            if not os.path.exists(model_path):
                logger.warning(f"Model not found at {model_path}")
                if allow_mock:
                    logger.info("Creating mock model as fallback")
                    _loaded_model = _create_mock_model()
                    _model_path = model_path
                    return _loaded_model
                else:
                    raise FileNotFoundError(
                        f"Model not found at {model_path}. "
                        f"Set allow_mock=True to use mock model for development."
                    )
            
            # Load real model
            try:
                logger.info(f"Loading model from {model_path}")
                _loaded_model = tf.keras.models.load_model(model_path)
                _model_path = model_path
                logger.info("Model loaded successfully")
                return _loaded_model
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                if allow_mock:
                    logger.warning("Falling back to mock model")
                    _loaded_model = _create_mock_model()
                    _model_path = model_path
                    return _loaded_model
                else:
                    raise ValueError(f"Failed to load model: {e}") from e
        finally:
            _loading = False


def _create_mock_model() -> tf.keras.Model:
    """
    Create a minimal mock CNN model for development/testing.
    This model uses minimal memory and returns random predictions.
    
    Returns:
        Mock TensorFlow model
    """
    logger.info("Creating minimal mock model for development (memory-efficient)")
    
    # Use minimal model to save memory on free tier
    # Only create what's needed for inference
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(28, 28, 1)),
        tf.keras.layers.Flatten(),
        # Minimal output layer - just enough for basic prediction
        tf.keras.layers.Dense(10, activation='softmax', name='predictions')
    ])
    
    # Compile with dummy optimizer (not used for inference)
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    
    _loaded_model = model
    return model


def get_model(allow_mock: bool = True) -> tf.keras.Model:
    """
    Get the currently loaded model.
    Thread-safe lazy loading with lock if model not yet loaded.
    
    Args:
        allow_mock: If True, create mock model when real model fails. Default: True.
    
    Returns:
        TensorFlow model
    """
    if _loaded_model is None:
        return load_model(allow_mock=allow_mock)
    return _loaded_model


async def load_model_async(model_path: Optional[str] = None, allow_mock: bool = True) -> tf.keras.Model:
    """
    Async version of load_model for background loading.
    Uses asyncio.to_thread to run blocking TensorFlow load in thread pool.
    
    Args:
        model_path: Path to the saved model. If None, uses default path.
        allow_mock: If True, create mock model when real model fails. Default: True.
        
    Returns:
        Loaded TensorFlow model
    """
    import asyncio
    return await asyncio.to_thread(load_model, model_path, allow_mock)


def clear_cache():
    """Clear the model cache (useful for testing or reloading). Thread-safe."""
    global _loaded_model, _model_path, _loading
    with _load_lock:
        _loaded_model = None
        _model_path = None
        _loading = False
    logger.info("Model cache cleared")

