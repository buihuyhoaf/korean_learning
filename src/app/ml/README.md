# ML Module - Hangul Character Recognition

## Overview

This module implements Machine Learning-based recognition for Hangul characters drawn by users.

## Architecture

### Components

1. **model_loader.py**: Loads and caches TensorFlow CNN model
   - Supports model caching for performance
   - Falls back to mock model if real model not found (for development)

2. **preprocessor.py**: Converts stroke data to 28x28 grayscale images
   - Normalizes stroke coordinates
   - Rasterizes strokes to image format
   - Handles batch processing

3. **API Router** (`api/v1/predict.py`): FastAPI endpoint for predictions
   - Endpoint: `POST /api/v1/predict/stroke`
   - Accepts stroke data in JSON format
   - Returns predicted character and confidence score

## Usage

### Backend API

```python
POST /api/v1/predict/stroke
Content-Type: application/json

{
  "strokes": [
    {
      "stroke_id": 1,
      "points": [
        {"x": 100.0, "y": 100.0},
        {"x": 150.0, "y": 150.0}
      ],
      "timestamp": 1234567890
    }
  ]
}
```

Response:
```json
{
  "predicted_char": "가",
  "confidence": 0.93,
  "top_k": [
    {"char": "가", "confidence": 0.93},
    {"char": "나", "confidence": 0.05}
  ]
}
```

### Model Setup

1. Place trained model in `models/hangul_cnn_model/` directory
2. Model should be saved in TensorFlow SavedModel format
3. If model not found, system uses mock model (random predictions)

### Training Model (Future)

TODO: Add instructions for training CNN model on Hangul character dataset

## Testing

Run unit tests:
```bash
pytest tests/test_ml/
```

## Extension Points

- **Room Persistence**: Store failed predictions for retraining
- **ML Kit Integration**: Replace TensorFlow with on-device ML Kit
- **Stroke Correction**: Add feedback loop for stroke improvement

