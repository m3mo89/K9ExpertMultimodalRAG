"""Telemetry privacy policy shared by trace producers, sinks and exports."""

from __future__ import annotations

from collections.abc import Mapping

# Attributes that may carry user questions, document text, files, secrets or raw feedback.
PROTECTED_KEYS = frozenset(
    {
        "question",
        "answer",
        "text",
        "content",
        "comment",
        "excerpt",
        "file_path",
        "secret",
        "admin_secret",
        "prompt",
        "error_message",
    }
)


def redact(attributes: Mapping[str, object], include_protected: bool = False) -> dict[str, object]:
    """Drop protected attributes recursively unless a privileged export asks for them."""
    if include_protected:
        return dict(attributes)
    result: dict[str, object] = {}
    for key, value in attributes.items():
        if key in PROTECTED_KEYS:
            continue
        if isinstance(value, Mapping):
            result[key] = redact(value)
        elif isinstance(value, list):
            result[key] = [redact(item) if isinstance(item, Mapping) else item for item in value]
        else:
            result[key] = value
    return result
