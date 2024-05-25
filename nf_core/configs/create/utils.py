from logging import LogRecord
from typing import Optional

from pydantic import BaseModel
from rich.logging import RichHandler
from textual._context import active_app
from textual.message import Message
from textual.widget import Widget
from textual.widgets import RichLog

## Logging (TODO: move to common place and share with pipelines logging?)

class LoggingConsole(RichLog):
    file = False
    console: Widget

    def print(self, content):
        self.write(content)

class CustomLogHandler(RichHandler):
    """A Logging handler which extends RichHandler to write to a Widget and handle a Textual App."""

    def emit(self, record: LogRecord) -> None:
        """Invoked by logging."""
        try:
            _app = active_app.get()
        except LookupError:
            pass
        else:
            super().emit(record)

class ShowLogs(Message):
    """Custom message to show the logging messages."""

    pass

## Config model template

class CreateConfig(BaseModel):
    """Pydantic model for the nf-core create config."""

    config_type: Optional[str] = None
