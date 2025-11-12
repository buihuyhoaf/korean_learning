"""
Pydantic schemas for stroke analysis API
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class StrokeInput(BaseModel):
    """Input schema for stroke analysis"""
    points: Optional[List[List[float]]] = Field(
        None,
        description="List of stroke points as [[x1, y1], [x2, y2], ...]"
    )
    image_base64: Optional[str] = Field(
        None,
        description="Base64 encoded image of the drawn character"
    )
    target_char: Optional[str] = Field(
        None,
        description="Target Hangul character (for comparison, optional)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "points": [[100.0, 100.0], [150.0, 150.0], [200.0, 100.0]],
                "target_char": "가"
            }
        }


class StrokeTopPrediction(BaseModel):
    index: int = Field(ge=0, description="Index of the label in the model output")
    char: str = Field(description="Predicted Hangul syllable")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0.0-1.0)")


class StrokeResult(BaseModel):
    """Output schema for stroke analysis"""

    predicted_char: str = Field(description="Predicted Hangul syllable")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0) of the top prediction"
    )
    message: str = Field(description="Human-readable message about the prediction")
    top_predictions: List[StrokeTopPrediction] = Field(
        default_factory=list,
        description="Top-k predictions from the model"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "predicted_char": "헹",
                "confidence": 0.12,
                "message": "Predicted syllable 헹. Hãy tô nét rõ hơn để tăng độ tin cậy.",
                "top_predictions": [
                    {"index": 1234, "char": "헹", "confidence": 0.12},
                    {"index": 432, "char": "행", "confidence": 0.08}
                ]
            }
        }


class StrokeResponse(BaseModel):
    result: StrokeResult
    inference_time_ms: float

