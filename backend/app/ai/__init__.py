"""Provider-neutral AI generation boundary (AI-001).

`default_provider` is the process-wide `AIProvider` singleton used by
`ai_studio_service.py` and `material_service.py`, mirroring
`app.core.file_storage.material_file_storage`: production call sites use
the default, tests inject a fake implementing `app.ai.provider.AIProvider`.
"""
from app.ai.openrouter_adapter import OpenRouterAdapter

default_provider = OpenRouterAdapter()
default_embedding_provider = default_provider

__all__ = ["default_embedding_provider", "default_provider", "OpenRouterAdapter"]
