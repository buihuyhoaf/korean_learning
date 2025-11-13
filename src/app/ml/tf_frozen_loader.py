"""
TensorFlow frozen graph loader for Hangul character recognition
Simple implementation to load and use .pb model files
"""
import os
import logging
from pathlib import Path
from typing import Optional, Tuple, List
from threading import Lock
import numpy as np

logger = logging.getLogger(__name__)

# Lazy import TensorFlow
try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    tf = None

# Global cache
_session = None
_graph = None
_input_tensor = None
_output_tensor = None
_model_path = None
_labels: List[str] = []
_labels_path = None
_lock = Lock()


def load_labels(label_file: str) -> List[str]:
    """Load labels from file (one label per line)"""
    global _labels, _labels_path
    
    if _labels and _labels_path == label_file:
        return _labels
    
    with _lock:
        if _labels and _labels_path == label_file:
            return _labels
        
        try:
            with open(label_file, 'r', encoding='utf-8') as f:
                _labels = [line.strip() for line in f if line.strip()]
            _labels_path = label_file
            logger.info(f"Loaded {len(_labels)} labels from {label_file}")
            return _labels
        except Exception as e:
            logger.error(f"Failed to load labels: {e}")
            return []


def load_graph(model_file: str) -> Tuple[object, object, object, object]:
    """
    Load TensorFlow frozen graph (.pb file)
    Returns: (session, graph, input_tensor, output_tensor)
    """
    global _session, _graph, _input_tensor, _output_tensor, _model_path
    
    if _session is not None and _model_path == model_file:
        return _session, _graph, _input_tensor, _output_tensor
    
    with _lock:
        if _session is not None and _model_path == model_file:
            return _session, _graph, _input_tensor, _output_tensor
        
        if not TF_AVAILABLE:
            raise ImportError("TensorFlow is required. Install with: pip install tensorflow")
        
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"Model file not found: {model_file}")
        
        logger.info(f"Loading TensorFlow frozen graph from {model_file}")
        
        # Load frozen graph
        graph = tf.Graph()
        with graph.as_default():
            # Read frozen graph
            with tf.io.gfile.GFile(model_file, 'rb') as f:
                graph_def = tf.compat.v1.GraphDef()
                graph_def.ParseFromString(f.read())
            
            # Import graph
            tf.compat.v1.import_graph_def(graph_def, name='')
            
            # Create session
            session = tf.compat.v1.Session(graph=graph)
            
            # Get input and output tensors
            # Try common tensor names
            try:
                input_tensor = graph.get_tensor_by_name('input:0')
                output_tensor = graph.get_tensor_by_name('output:0')
            except KeyError:
                # Try alternative names
                try:
                    input_tensor = graph.get_tensor_by_name('Placeholder:0')
                    output_tensor = graph.get_tensor_by_name('predictions:0')
                except KeyError:
                    # List available tensors for debugging
                    all_ops = [op.name for op in graph.get_operations()]
                    logger.error(f"Could not find input/output tensors. Available operations: {all_ops[:10]}...")
                    raise ValueError("Could not find input/output tensors in model. Expected 'input:0' and 'output:0'")
            
            logger.info("TensorFlow frozen graph loaded successfully")
            logger.info(f"Input tensor: {input_tensor.name}, shape: {input_tensor.shape}")
            logger.info(f"Output tensor: {output_tensor.name}, shape: {output_tensor.shape}")
        
        _session = session
        _graph = graph
        _input_tensor = input_tensor
        _output_tensor = output_tensor
        _model_path = model_file
        
        return session, graph, input_tensor, output_tensor


def predict_top_k(
    session, 
    input_tensor, 
    output_tensor, 
    image: np.ndarray, 
    labels: List[str],
    k: int = 5
) -> List[dict]:
    """
    Get top-k predictions using TensorFlow frozen graph
    """
    # Ensure image has correct shape [1, height, width, 1]
    if image.ndim == 2:
        image = np.expand_dims(image, axis=0)  # Add batch dim
        image = np.expand_dims(image, axis=-1)  # Add channel dim
    elif image.ndim == 3:
        image = np.expand_dims(image, axis=0)  # Add batch dim
    
    # Run inference
    predictions = session.run(output_tensor, feed_dict={input_tensor: image})
    
    # Get top-k
    if predictions.ndim == 2 and predictions.shape[0] > 0:
        top_k_indices = np.argsort(predictions[0])[::-1][:k]
        
        results = []
        for idx in top_k_indices:
            char = labels[idx] if idx < len(labels) else "?"
            results.append({
                "index": int(idx),
                "char": char,
                "confidence": float(predictions[0][idx])
            })
        return results
    else:
        return []

