"""Typed domain errors exposed through application results, never raw infrastructure errors."""

from __future__ import annotations

from dataclasses import dataclass


# Not frozen/slotted: raised exceptions must accept __traceback__ assignment.
@dataclass(eq=False)
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


class ModelOutputError(DomainError):
    def __init__(self, message: str = "El modelo devolvió una estructura no verificable.") -> None:
        super().__init__("model_output_invalid", message, retryable=False)


class OcrUnavailableError(DomainError):
    def __init__(self, message: str = "El motor OCR local no está disponible.") -> None:
        super().__init__("ocr_unavailable", message, retryable=True)


class OcrTimeoutError(DomainError):
    def __init__(self, message: str = "El OCR excedió el tiempo límite.") -> None:
        super().__init__("ocr_timeout", message, retryable=True)


class OcrExecutionError(DomainError):
    def __init__(self, message: str = "El OCR no pudo procesar la página.") -> None:
        super().__init__("ocr_failed", message, retryable=False)
