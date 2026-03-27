import json

from app.tasks import run_judge


def test_judge_parses_valid_json(monkeypatch):
    def mock_call_llm(messages, model, temperature):
        return json.dumps({"score_a": 7, "score_b": 9, "reasoning": "B is better"})

    monkeypatch.setattr("app.tasks.call_llm", mock_call_llm)

    result = run_judge("system", "user input", "original", "replayed")
    assert result["original_score"] in (7, 9)
    assert result["replayed_score"] in (7, 9)
    assert "reasoning" in result


def test_judge_handles_malformed_json(monkeypatch):
    def mock_call_llm(messages, model, temperature):
        return "This is not JSON at all"

    monkeypatch.setattr("app.tasks.call_llm", mock_call_llm)

    result = run_judge("system", "user input", "original", "replayed")
    assert result["original_score"] == 0
    assert result["replayed_score"] == 0
    assert "invalid response" in result["reasoning"].lower()


def test_judge_handles_partial_json(monkeypatch):
    def mock_call_llm(messages, model, temperature):
        return json.dumps({"score_a": 5})  # missing score_b

    monkeypatch.setattr("app.tasks.call_llm", mock_call_llm)

    result = run_judge("system", "user input", "original", "replayed")
    assert result["original_score"] == 0
    assert result["replayed_score"] == 0


def test_judge_strips_markdown_code_fences(monkeypatch):
    def mock_call_llm(messages, model, temperature):
        return '```json\n{"score_a": 4, "score_b": 9, "reasoning": "B is much better"}\n```'

    monkeypatch.setattr("app.tasks.call_llm", mock_call_llm)

    result = run_judge("system", "user input", "original", "replayed")
    assert result["original_score"] in (4, 9)
    assert result["replayed_score"] in (4, 9)
    assert "better" in result["reasoning"]
