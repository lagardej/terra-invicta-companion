"""Tests for Message, DomainEvent, and IntegrationEvent base types."""

from __future__ import annotations

import pytest

from tic.shared.events.base import DomainEvent, IntegrationEvent, Message


class TestMessage:
    """Message is the common base — defines the type() contract."""

    @pytest.mark.unit
    def test_domain_event_is_message(self) -> None:
        assert issubclass(DomainEvent, Message)

    @pytest.mark.unit
    def test_integration_event_is_message(self) -> None:
        assert issubclass(IntegrationEvent, Message)


class TestDomainEvent:
    """DomainEvent subclasses declare their own type string."""

    @pytest.mark.unit
    def test_type_returns_declared_string(self) -> None:
        class SomethingHappened(DomainEvent):
            @classmethod
            def type(cls) -> str:
                return "something.happened"

        assert SomethingHappened.type() == "something.happened"

    @pytest.mark.unit
    def test_type_accessible_on_instance(self) -> None:
        class SomethingHappened(DomainEvent):
            @classmethod
            def type(cls) -> str:
                return "something.happened"

        assert SomethingHappened().type() == "something.happened"


class TestIntegrationEvent:
    """IntegrationEvent subclasses declare their own type string."""

    @pytest.mark.unit
    def test_type_returns_declared_string(self) -> None:
        class SomethingCrossed(IntegrationEvent):
            @classmethod
            def type(cls) -> str:
                return "something.crossed"

        assert SomethingCrossed.type() == "something.crossed"
