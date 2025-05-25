from rich.console import Console
from rich.live import Live
from rich.text import Text

console = Console()
_logger = None


def rich_log(message: Text):
    global _logger
    if _logger is None:
        _logger = Live(console=console, refresh_per_second=4)
        _logger.start()
    _logger.update(message)


def rich_log_done():
    """Stop the current Live context and print the last message to scroll it up."""
    global _logger
    if _logger is not None:
        _logger.stop()
        _logger = None


def progress(entry: str, status: str):
    return Text.from_markup(f"[blue]{entry}[/blue] - [green]{status}[/green]")
