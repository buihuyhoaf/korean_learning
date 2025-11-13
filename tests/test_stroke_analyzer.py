import base64
import io

import numpy as np
import pytest
from PIL import Image

from src.app.services.stroke_analyzer import StrokeAnalyzer


@pytest.fixture()
def analyzer() -> StrokeAnalyzer:
    instance = StrokeAnalyzer()
    instance.model_loaded = True
    instance._use_mock = False
    instance.interpreter = object()  # sentinel to avoid lazy loading
    return instance


def test_predict_and_describe_returns_prediction(analyzer: StrokeAnalyzer):
    analyzer.predict = lambda data: (
        "가",
        0.92,
        [{"char": "가", "confidence": 0.92, "index": 0}],
    )
    input_data = np.zeros((28, 28, 1), dtype=np.float32)

    result = analyzer.predict_and_describe(input_data)

    assert result["predicted_char"] == "가"
    assert result["top_predictions"]


def test_predict_and_describe_low_confidence_message(analyzer: StrokeAnalyzer):
    analyzer.predict = lambda data: (
        "나",
        0.5,
        [{"char": "나", "confidence": 0.5, "index": 0}],
    )
    input_data = np.zeros((28, 28, 1), dtype=np.float32)

    result = analyzer.predict_and_describe(input_data)

    assert "Độ tin cậy" in result["message"] or "Dự đoán" in result["message"]


def test_analyze_stroke_no_input_returns_error(analyzer: StrokeAnalyzer):
    result = analyzer.analyze_stroke(points=None, image_base64=None, target_char=None)
    assert result["message"] == "No input data provided"
    assert result["predicted_char"] == "?"


def test_analyze_stroke_prefers_image_over_points(analyzer: StrokeAnalyzer):
    called = {"image": False}

    def fake_preprocess_image(data: str) -> np.ndarray:
        called["image"] = True
        return np.zeros((64, 64, 1), dtype=np.float32)

    analyzer.preprocess_image_base64 = fake_preprocess_image  # type: ignore[assignment]
    analyzer.predict_and_describe = lambda data: {
        "predicted_char": "가",
        "confidence": 0.9,
        "message": "",
        "top_predictions": [],
    }

    buffer = io.BytesIO()
    Image.new("L", (64, 64), color=0).save(buffer, format="PNG")
    image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    analyzer.analyze_stroke(
        points=[[0.0, 0.0], [10.0, 10.0]],
        image_base64=image_base64,
        target_char=None,
    )

    assert called["image"] is True
