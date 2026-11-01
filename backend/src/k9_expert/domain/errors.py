"""Typed domain errors exposed through application results, never raw infrastructure errors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DomainError(Exception):
    code: str
    message: str
    retryable: bool = False


class ValidationError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__("validation_error", message)


class ModelUnavailableError(DomainError):
    def __init__(self, message: str = "El modelo local no está disponible.") -> None:
        super().__init__("model_unavailable", message, retryable=True)

