from app.ai.prompts import question_generation_v1


def test_fill_in_blank_prompt_uses_the_canonical_placeholder_contract():
    prompt = question_generation_v1.render(
        context_text="Verified source material",
        count=1,
        question_types="FILL_IN_BLANK",
        difficulty="EASY",
    )

    assert question_generation_v1.PROMPT_VERSION == 3
    assert "[BLANK]" in prompt
    assert "không dùng dấu gạch dưới thay thế" in prompt
