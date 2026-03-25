"""Qt signal bus for real-time (WebSocket) messages.

We keep this in `common/` so both client entrypoint and shared UI modules can use it
without importing each other.
"""

from PyQt5.QtCore import QObject, pyqtSignal


class RealtimeBus(QObject):
    """Thread-safe Qt signal bus for real-time messages."""

    message = pyqtSignal(dict)


