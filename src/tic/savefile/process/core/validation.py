"""Validation error returned by scoped savefile processors."""

from dataclasses import dataclass

from pydantic import BaseModel, ValidationError
from returns.result import Failure, Result, Success


@dataclass(frozen=True)
class ValidationFailure:
    """Validation error returned by scoped savefile processors."""

    violations: tuple[str, ...]


def validate_input[ModelT: BaseModel](
    model_type: type[ModelT],
    data: dict,
) -> Result[ModelT, ValidationFailure]:
    """Validate raw input into a typed Pydantic model as a Result."""
    try:
        return Success(model_type.model_validate(data, by_alias=True))
    except ValidationError as exc:
        violations = tuple(error["msg"] for error in exc.errors())
        return Failure(ValidationFailure(violations=violations))
