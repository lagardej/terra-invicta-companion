"""Application container — framework-level base."""

from abc import ABC, abstractmethod

from lagom import ExplicitContainer


class Settings(ABC):
    """Base class for application settings."""

    @classmethod
    @abstractmethod
    def load(cls) -> Settings:
        """Load settings from the environment."""
        ...


class Application[S: Settings]:
    """Wired application — wraps the lagom container and exposes typed helpers.

    Immutable after construction.
    """

    __slots__ = ("_container", "settings")

    def __init__(self, container: ExplicitContainer, settings: S) -> None:
        """Initialize the application."""
        object.__setattr__(self, "_container", container)
        object.__setattr__(self, "settings", settings)

    def __setattr__(self, name: str, value: object) -> None:
        """Prevent mutation after construction."""
        raise AttributeError("Application is immutable")

    def __delattr__(self, name: str) -> None:
        """Prevent deletion after construction."""
        raise AttributeError("Application is immutable")

    def resolve[T](self, type_: type[T]) -> T:
        """Resolve a type from the container."""
        return self._container[type_]  # type: ignore[return-value]
