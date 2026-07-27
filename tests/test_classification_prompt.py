from app.ai.classification import FEW_SHOT_EXAMPLES, SYSTEM_PROMPT


def test_system_prompt_includes_sarcasm_guidance():
    assert "sarcasm" in SYSTEM_PROMPT.lower()


def test_system_prompt_includes_mixed_sentiment_guidance():
    assert "mixed sentiment" in SYSTEM_PROMPT.lower()


def test_few_shot_examples_include_sarcasm_case():
    inputs = [example_input for example_input, _ in FEW_SHOT_EXAMPLES]
    assert any("wonderful" in text.lower() and "crash" in text.lower() for text in inputs)


def test_few_shot_examples_include_mixed_sentiment_case():
    inputs = [example_input for example_input, _ in FEW_SHOT_EXAMPLES]
    assert any("rocky start" in text.lower() for text in inputs)
