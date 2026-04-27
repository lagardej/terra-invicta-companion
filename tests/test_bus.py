"""Tests for the async message bus."""

import pytest

from tic.bus import Bus


class TestBus:
    """Async message bus behaviour."""

    @pytest.mark.unit
    async def test_subscribed_handler_is_called(self) -> None:
        bus = Bus()
        received: list[object] = []

        async def handler(payload: object) -> None:
            received.append(payload)

        bus.subscribe("save.detected", handler)
        await bus.publish("save.detected", "payload_a")

        assert received == ["payload_a"]

    @pytest.mark.unit
    async def test_multiple_handlers_all_called(self) -> None:
        bus = Bus()
        received: list[object] = []

        async def handler_a(payload: object) -> None:
            received.append(("a", payload))

        async def handler_b(payload: object) -> None:
            received.append(("b", payload))

        bus.subscribe("save.detected", handler_a)
        bus.subscribe("save.detected", handler_b)
        await bus.publish("save.detected", "x")

        assert ("a", "x") in received
        assert ("b", "x") in received

    @pytest.mark.unit
    async def test_unrelated_event_not_dispatched(self) -> None:
        bus = Bus()
        received: list[object] = []

        async def handler(payload: object) -> None: ...

        bus.subscribe("save.detected", handler)
        await bus.publish("import.succeeded", "y")

        assert received == []

    @pytest.mark.unit
    async def test_no_subscribers_publish_is_silent(self) -> None:
        bus = Bus()
        await bus.publish("save.detected", "z")
