"""
API routes for stroke analysis
"""
import logging
from fastapi import APIRouter, HTTPException, status
from ...schemas.stroke_schema import StrokeInput, StrokeResult
from ...services.stroke_analyzer import get_stroke_analyzer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stroke", tags=["stroke"])


@router.post("/analyze", response_model=StrokeResult)
async def analyze_stroke(stroke_input: StrokeInput) -> StrokeResult:
    """
    Analyze hand-drawn Hangul stroke and return prediction
    
    Args:
        stroke_input: Input containing points or image_base64
        
    Returns:
        StrokeResult with predicted character and confidence
    """
    try:
        # Validate input
        if not stroke_input.points and not stroke_input.image_base64:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'points' or 'image_base64' must be provided"
            )
        
        # Get analyzer instance
        analyzer = get_stroke_analyzer()
        
        # Run analysis
        predicted_char, confidence, message = analyzer.analyze_stroke(
            points=stroke_input.points,
            image_base64=stroke_input.image_base64,
            target_char=stroke_input.target_char
        )
        
        logger.info(
            f"Prediction: {predicted_char} (confidence: {confidence:.2f})"
        )
        
        return StrokeResult(
            predicted_char=predicted_char,
            confidence=confidence,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing stroke: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

