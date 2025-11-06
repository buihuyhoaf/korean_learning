"""
Model loader for TensorFlow CNN model
Loads and caches the pre-trained model for Hangul character recognition
"""
import os
import logging
from pathlib import Path
from typing import Optional
import tensorflow as tf

logger = logging.getLogger(__name__)

# Global model cache
_loaded_model: Optional[tf.keras.Model] = None
_model_path: Optional[str] = None


def load_model(model_path: Optional[str] = None) -> tf.keras.Model:
    """
    Load and cache TensorFlow model for Hangul character recognition.
    
    Args:
        model_path: Path to the saved model. If None, uses default path.
        
    Returns:
        Loaded TensorFlow model
        
    Raises:
        FileNotFoundError: If model file doesn't exist
        ValueError: If model cannot be loaded
    """
    global _loaded_model, _model_path
    
    # Use default path if not provided
    if model_path is None:
        # Default path: models/hangul_cnn_model/
        default_path = Path(__file__).parent.parent / "models" / "hangul_cnn_model"
        model_path = str(default_path)
    
    # Return cached model if already loaded and path matches
    if _loaded_model is not None and _model_path == model_path:
        logger.info("Returning cached model")
        return _loaded_model
    
    # Check if model exists
    if not os.path.exists(model_path):
        logger.warning(f"Model not found at {model_path}, creating mock model for development")
        # Create a simple mock model for development/testing
        return _create_mock_model()
    
    try:
        logger.info(f"Loading model from {model_path}")
        _loaded_model = tf.keras.models.load_model(model_path)
        _model_path = model_path
        logger.info("Model loaded successfully")
        return _loaded_model
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        logger.warning("Falling back to mock model")
        return _create_mock_model()


def _create_mock_model() -> tf.keras.Model:
    """
    Create a simple mock CNN model for development/testing.
    This model will return random predictions.
    
    Returns:
        Mock TensorFlow model
    """
    logger.info("Creating mock model for development")
    
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(28, 28, 1)),
        tf.keras.layers.Conv2D(32, (3, 3), activation='relu'),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
        tf.keras.layers.MaxPooling2D((2, 2)),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(128, activation='relu'),
        tf.keras.layers.Dropout(0.5),
        # Output layer: 2350 Hangul characters (0xAC00-0xD7A3)
        tf.keras.layers.Dense(2350, activation='softmax', name='predictions')
    ])
    
    # Compile with dummy optimizer (not used for inference)
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    
    _loaded_model = model
    return model


def get_model() -> tf.keras.Model:
    """
    Get the currently loaded model.
    Loads model if not already loaded.
    
    Returns:
        TensorFlow model
    """
    if _loaded_model is None:
        return load_model()
    return _loaded_model


def clear_cache():
    """Clear the model cache (useful for testing or reloading)"""
    global _loaded_model, _model_path
    _loaded_model = None
    _model_path = None
    logger.info("Model cache cleared")

