from collections.abc import Awaitable, Callable

Handler = Callable[[dict[str, object]], Awaitable[None]]


class HandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, event_type: str, handler: Handler) -> None:
        self._handlers[event_type] = handler

    def get(self, event_type: str) -> Handler | None:
        return self._handlers.get(event_type)
