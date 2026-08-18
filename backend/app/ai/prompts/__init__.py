"""Versioned prompt templates (AI-001).

Each module exposes a stable `PROMPT_ID`, an integer `PROMPT_VERSION`, and a
`render(...)` function. Wording is unchanged from the inline f-strings that
used to live in `ai_studio_service.py`/`material_service.py` -- this package
only extracts and versions them, it does not edit prompt content.
"""
