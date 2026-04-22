"""
Simple event bus for dispatching hook events to plugin handlers.

The bus loads plugins from the `runtime_sidecar.plugins` package and
invokes their `handle_event` functions based on the event type.  Each
plugin can opt into handling certain events by listing them in a
`HANDLED_EVENTS` iterable.

If a plugin raises an exception, the bus catches it and logs a warning
rather than propagating the error.  This ensures that one failing
component does not cause the entire hook chain to fail.
"""

from importlib import import_module
from typing import Any, Dict, List, Callable

from .hook_events import HookEvent, HookEventType
from .logging.logger import get_logger

logger = get_logger(__name__)


class EventBus:
    """A simple event bus that maps events to plugin handlers."""

    def __init__(self) -> None:
        # Discover plugin modules under runtime_sidecar.plugins
        self.plugins = self._discover_plugins()

    def _discover_plugins(self) -> List[Any]:
        """Import all modules in the plugins package and return them."""
        plugins: List[Any] = []
        # List of plugin module names to import.  Explicitly list the expected
        # modules to avoid dynamic filesystem scanning, which can be fragile.
        plugin_names = [
            "session_start",
            "post_compact",
            "post_tool_use",
            "file_changed",
            "pre_tool_use",
            "user_prompt_submit",
        ]
        for name in plugin_names:
            try:
                module = import_module(f"runtime_sidecar.plugins.{name}")
                plugins.append(module)
            except Exception as exc:
                logger.warning("Failed to import plugin %s: %s", name, exc)
        return plugins

    def dispatch(self, event: HookEvent) -> List[Any]:
        """Dispatch a hook event to all interested plugins.

        Returns a list of plugin results.  Individual plugin failures are
        logged and skipped.
        """
        results: List[Any] = []
        for plugin in self.plugins:
            handled_events = getattr(plugin, "HANDLED_EVENTS", [])
            if event.event_type.value not in handled_events:
                continue
            handle_fn: Callable[[Dict[str, Any]], Any] = getattr(
                plugin, "handle_event", None
            )
            if not callable(handle_fn):
                logger.warning(
                    "Plugin %s does not define a callable handle_event", plugin.__name__
                )
                continue
            try:
                result = handle_fn(event.context)
                results.append(result)
            except Exception as exc:
                logger.warning(
                    "Plugin %s raised exception while handling %s: %s",
                    plugin.__name__,
                    event.event_type.value,
                    exc,
                )
        return results