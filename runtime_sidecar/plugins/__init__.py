"""
Plugin package for hook event handlers.

Each module in this package declares a `HANDLED_EVENTS` iterable listing the
event names it is interested in.  The dispatcher will call its
`handle_event(context: dict)` when one of those events occurs.  A plugin may
return any JSON-serialisable object to pass back to the caller; ignored
plugins simply return None.
"""