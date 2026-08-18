import json

import pytest

from app.ai.json_extraction import extract_json_payload


@pytest.mark.unit
def test_extracts_json_from_a_markdown_code_fence():
    content = """Here you go:
```json
{"flashcards": [{"term": "a", "definition": "b"}]}
```
Hope that helps."""

    assert extract_json_payload(content) == {
        "flashcards": [{"term": "a", "definition": "b"}]
    }


@pytest.mark.unit
def test_extracts_json_from_a_bare_fence_without_language_tag():
    content = "```\n[1, 2, 3]\n```"

    assert extract_json_payload(content) == [1, 2, 3]


@pytest.mark.unit
def test_extracts_a_json_array_surrounded_by_stray_text():
    content = 'Sure, here are the questions:\n[{"content": "q1"}]\nLet me know if you need more.'

    assert extract_json_payload(content) == [{"content": "q1"}]


@pytest.mark.unit
def test_extracts_a_json_object_surrounded_by_stray_text():
    content = 'Answer: {"content": "brief text"} -- generated from the document.'

    assert extract_json_payload(content) == {"content": "brief text"}


@pytest.mark.unit
def test_parses_already_clean_json_unchanged():
    content = json.dumps({"questions": []})

    assert extract_json_payload(content) == {"questions": []}


@pytest.mark.unit
def test_raises_json_decode_error_for_unrecoverable_text():
    with pytest.raises(json.JSONDecodeError):
        extract_json_payload("this is not JSON at all")
