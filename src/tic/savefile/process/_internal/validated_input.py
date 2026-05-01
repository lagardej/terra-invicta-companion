"""Shared helpers for validated savefile input extraction."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError
from returns.result import Failure, Result, Success

from tic.savefile.process._internal.validation_failure import ValidationFailure


def validate_input[ModelT: BaseModel](
    model_type: type[ModelT],
    data: dict,
) -> Result[ModelT, ValidationFailure]:
    """Validate raw input into a typed Pydantic model as a Result."""
    try:
        return Success(model_type.model_validate(data, by_alias=True))
    except ValidationError as exc:
        return Failure(ValidationFailure(reason=str(exc)))
