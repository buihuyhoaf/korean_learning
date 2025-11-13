"""
FastAPI router for ML-based stroke prediction
"""
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, validator

# Lazy imports to avoid loading TensorFlow on startup (saves memory)
import numpy as np

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["ML Prediction"])


class StrokePoint(BaseModel):
    """Single point in a stroke"""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")
    
    class Config:
        json_schema_extra = {
            "example": {"x": 100.5, "y": 200.3}
        }


class StrokeRequest(BaseModel):
    """Request model for stroke data"""
    stroke_id: int = Field(..., description="Stroke identifier")
    points: List[StrokePoint] = Field(..., description="List of points in the stroke")
    timestamp: Optional[int] = Field(None, description="Timestamp (optional)")
    
    @validator("points")
    def validate_points(cls, v):
        if not v:
            raise ValueError("Points list cannot be empty")
        if len(v) < 2:
            raise ValueError("Stroke must have at least 2 points")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "stroke_id": 1,
                "points": [
                    {"x": 100.0, "y": 100.0},
                    {"x": 150.0, "y": 150.0},
                    {"x": 200.0, "y": 100.0}
                ],
                "timestamp": 1234567890
            }
        }


class PredictStrokeRequest(BaseModel):
    """Request body for stroke prediction"""
    strokes: List[StrokeRequest] = Field(..., description="List of strokes")
    
    @validator("strokes")
    def validate_strokes(cls, v):
        if not v:
            raise ValueError("Strokes list cannot be empty")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "strokes": [
                    {
                        "stroke_id": 1,
                        "points": [
                            {"x": 100.0, "y": 100.0},
                            {"x": 150.0, "y": 150.0}
                        ]
                    },
                    {
                        "stroke_id": 2,
                        "points": [
                            {"x": 150.0, "y": 150.0},
                            {"x": 200.0, "y": 100.0}
                        ]
                    }
                ]
            }
        }


class PredictStrokeResponse(BaseModel):
    """Response model for stroke prediction"""
    predicted_char: str = Field(..., description="Predicted Hangul character")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    top_k: Optional[List[Dict[str, Any]]] = Field(None, description="Top K predictions (optional)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "predicted_char": "가",
                "confidence": 0.93,
                "top_k": [
                    {"char": "가", "confidence": 0.93},
                    {"char": "나", "confidence": 0.05},
                    {"char": "다", "confidence": 0.02}
                ]
            }
        }


# DISABLED: Stroke prediction endpoint - inference now runs locally on Android device
# This reduces backend load and improves response time
# @router.post("/stroke", response_model=PredictStrokeResponse)
async def predict_stroke_disabled(request: PredictStrokeRequest) -> PredictStrokeResponse:
    """
    Predict Hangul character from stroke data.
    
    This endpoint:
    1. Preprocesses stroke data into 28x28 grayscale image
    2. Runs inference using CNN model
    3. Returns predicted character and confidence score
    
    Args:
        request: Stroke data request
        
    Returns:
        Prediction result with character and confidence
        
    Raises:
        HTTPException: If prediction fails or data is invalid
    """
    # Lazy imports to save memory on startup
    try:
        from ...ml.model_loader import get_model
        from ...ml.preprocessor import StrokePreprocessor, unicode_to_char
        import tensorflow as tf
    except ImportError as e:
        logger.error(f"Failed to import ML modules: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML service temporarily unavailable"
        )
    
    try:
        # Convert request to format expected by preprocessor
        strokes_data = []
        for stroke_req in request.strokes:
            strokes_data.append({
                "stroke_id": stroke_req.stroke_id,
                "points": [[p.x, p.y] for p in stroke_req.points],
                "timestamp": stroke_req.timestamp
            })
        
        # Preprocess strokes
        preprocessor = StrokePreprocessor()
        try:
            image = preprocessor.preprocess(strokes_data)
        except ValueError as e:
            logger.error(f"Preprocessing error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stroke data: {str(e)}"
            )
        
        # Prepare model input: add batch and channel dimensions
        model_input = np.expand_dims(image, axis=0)  # (1, 28, 28)
        model_input = np.expand_dims(model_input, axis=-1)  # (1, 28, 28, 1)
        
        # Get model and predict (thread-safe with lock, mock fallback enabled)
        model = get_model(allow_mock=True)  # Safe fallback if real model unavailable
        try:
            predictions = model.predict(model_input, verbose=0)
        except Exception as e:
            logger.error(f"Model prediction error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Model prediction failed"
            )
        
        # Apply softmax if output is logits (not probabilities)
        logits = predictions[0]
        logger.debug(f"Predictions min/max/sum: {logits.min():.4f} / {logits.max():.4f} / {np.sum(logits):.4f}")
        
        if logits.min() < 0 or logits.max() > 1.0 or abs(np.sum(logits) - 1.0) > 0.1:
            # Likely logits, apply softmax
            exp_logits = np.exp(logits - np.max(logits))  # Numerical stability
            probabilities = exp_logits / np.sum(exp_logits)
            logger.debug("Applied softmax to convert logits to probabilities")
        else:
            # Already probabilities
            probabilities = logits
            logger.debug("Using predictions as probabilities (no softmax needed)")
        
        # Get top prediction
        predicted_idx = int(np.argmax(probabilities))
        confidence = float(probabilities[predicted_idx])
        
        # Convert index to Hangul character
        predicted_char = unicode_to_char(predicted_idx)
        
        # Get top 5 predictions for debugging/feedback
        top_k_indices = np.argsort(probabilities)[-5:][::-1]
        top_k = [
            {
                "char": unicode_to_char(int(idx)),
                "confidence": float(probabilities[idx])
            }
            for idx in top_k_indices
        ]
        
        logger.info(
            f"Prediction: {predicted_char} (confidence: {confidence:.3f}, "
            f"top_k: {[t['char'] for t in top_k[:3]]})"
        )
        
        return PredictStrokeResponse(
            predicted_char=predicted_char,
            confidence=confidence,
            top_k=top_k
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in predict_stroke: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )

