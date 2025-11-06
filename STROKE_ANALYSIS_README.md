# Phase 3 - ML-Based Stroke Recognition

## Overview

This implementation provides ML-based stroke recognition for Hangul characters. Users can draw characters on the Android app, and the FastAPI backend analyzes the strokes using ML models to predict the character and provide confidence scores.

## Architecture

### Backend (FastAPI)

**Clean Architecture Structure:**
```
src/app/
├── schemas/
│   └── stroke_schema.py          # Pydantic models for API
├── services/
│   └── stroke_analyzer.py        # ML inference service
├── api/
│   └── routes/
│       └── stroke_api.py         # API endpoint
└── core/
    └── setup.py                  # Model loading on startup
```

**Key Components:**
- **StrokeAnalyzer**: Handles preprocessing, model inference, and prediction
- **Preprocessing**: Converts stroke points or base64 images to 28x28 grayscale images
- **Model Loading**: Loads TensorFlow Lite or ONNX model on app startup
- **Mock Mode**: Falls back to mock predictions if model not available

### Frontend (Android/Kotlin)

**Clean Architecture:**
```
app/src/main/java/com/seoulhankuko/app/
├── domain/
│   └── usecase/
│       └── AnalyzeStrokeUseCase.kt    # Domain use case
├── data/
│   ├── api/
│   │   ├── model/
│   │   │   └── StrokeAnalysisModels.kt
│   │   └── service/
│   │       └── ApiService.kt
│   └── repository/
│       └── StrokeAnalysisRepository.kt
└── ui/
    └── screen/
        └── canvas/
            ├── HangulCanvasViewModel.kt
            └── HangulCanvasScreen.kt
```

## API Endpoint

### POST `/api/stroke/analyze`

**Request:**
```json
{
  "points": [[100.0, 100.0], [150.0, 150.0], [200.0, 100.0]],
  "image_base64": null,
  "target_char": "가"
}
```

**Response:**
```json
{
  "predicted_char": "가",
  "confidence": 0.92,
  "message": "Perfect match! Excellent drawing."
}
```

## Usage

### Backend

1. **Start FastAPI server:**
   ```bash
   uvicorn src.app.main:app --reload
   ```

2. **Model Loading:**
   - Model is loaded automatically on startup
   - If model file not found, uses mock mode
   - Set `MODEL_PATH` environment variable to specify model location

3. **Test endpoint:**
   ```bash
   curl -X POST http://localhost:8000/api/stroke/analyze \
     -H "Content-Type: application/json" \
     -d '{
       "points": [[100.0, 100.0], [150.0, 150.0], [200.0, 100.0]],
       "target_char": "가"
     }'
   ```

### Frontend

1. **Open Hangul Canvas Screen:**
   - Navigate to character selection
   - Select a character (e.g., "가")
   - Draw the character on canvas

2. **Analyze Stroke:**
   - Click "Kiểm tra" (Check) button
   - App sends stroke data to backend
   - Displays prediction result with confidence

3. **View Results:**
   - Predicted character
   - Confidence score (0-100%)
   - Success message based on confidence and target match

## Model Requirements

- **Format**: TensorFlow Lite or ONNX
- **Size**: ≤10MB (for Render free tier)
- **Input**: 28x28 grayscale image
- **Output**: Character prediction with confidence

## Configuration

### Environment Variables

```bash
# Optional: Model file path
MODEL_PATH=/path/to/model.tflite
```

### Render Deployment

1. **Dependencies**: Already included in `pyproject.toml`
2. **Model**: Place model file in project root or configure path
3. **Memory**: Free tier has 512MB RAM - keep model ≤10MB

## Testing

### Local Test Data

```python
# Example test request
test_points = [
    [100.0, 100.0],
    [150.0, 150.0],
    [200.0, 100.0],
    [250.0, 150.0]
]

# Expected: Character prediction with confidence > 0.5
```

## Future Enhancements

- [ ] Train actual CNN model on Hangul dataset
- [ ] Add model caching for better performance
- [ ] Support image_base64 input
- [ ] Add batch prediction endpoint
- [ ] Store failed predictions for retraining
- [ ] Add stroke correction feedback

## Troubleshooting

**Model not loading:**
- Check model file path
- Verify model format (TensorFlow Lite or ONNX)
- Check logs for errors

**Low confidence predictions:**
- Ensure strokes are drawn clearly
- Check preprocessing normalization
- Verify model is trained properly

**API errors:**
- Check FastAPI logs
- Verify endpoint URL is correct
- Ensure request format matches schema

