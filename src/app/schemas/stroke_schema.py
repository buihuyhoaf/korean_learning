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


class StrokeResult(BaseModel):
    """Output schema for stroke analysis"""
    predicted_char: str = Field(
        description="Predicted Hangul character"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0)"
    )
    message: str = Field(
        description="Human-readable message about the prediction"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "predicted_char": "가",
                "confidence": 0.92,
                "message": "Good match! High confidence prediction."
            }
        }

