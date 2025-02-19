import contextlib


class Connection:
    """Abstraction for a data system connection."""

    @contextlib.contextmanager
    @property
    def connection(self):
        """Contextable property for retrieving a live data system connection."""
        raise NotImplementedError
