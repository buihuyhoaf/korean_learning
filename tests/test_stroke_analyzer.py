import numpy as np
import pytest

from src.app.services.stroke_analyzer import StrokeAnalyzer


@pytest.fixture()
def analyzer() -> StrokeAnalyzer:
    instance = StrokeAnalyzer()
    instance.model_loaded = True
    instance._use_mock = False
    instance.interpreter = object()  # sentinel to avoid lazy loading
    return instance


def test_predict_and_describe_matches_vowel(analyzer: StrokeAnalyzer):
    analyzer.predict = lambda data: (
        "가",
        0.92,
        [{"char": "가", "confidence": 0.92, "index": 0}],
    )
    input_data = np.zeros((28, 28, 1), dtype=np.float32)

    result = analyzer.predict_and_describe(input_data, "ㅏ")

    assert result["predicted_char"] == "가"
    assert result["predicted_jungseong"] == "ㅏ"
    assert result["matches_target"] is True
    assert result["target_category"] == "jungseong"
    assert result["top_predictions"]


def test_predict_and_describe_mismatch_choseong(analyzer: StrokeAnalyzer):
    analyzer.predict = lambda data: (
        "나",
        0.5,
        [{"char": "나", "confidence": 0.5, "index": 0}],
    )
    input_data = np.zeros((28, 28, 1), dtype=np.float32)

    result = analyzer.predict_and_describe(input_data, "ㄱ")

    assert result["matches_target"] is False
    assert "Target was" in result["message"]


def test_analyze_stroke_no_input_returns_error(analyzer: StrokeAnalyzer):
    result = analyzer.analyze_stroke(points=None, image_base64=None, target_char=None)
    assert result["message"] == "No input data provided"
    assert result["predicted_char"] == "?"
    assert result["matches_target"] is False
