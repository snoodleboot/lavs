import contextlib


class Connection:

    @contextlib.contextmanager
    @property
    def connection(self):
        raise NotImplementedError
