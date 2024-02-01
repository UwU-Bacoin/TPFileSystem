from __future__ import annotations
import builtins

DEFAULT_SIZE = 64

def _skip(*_):
    pass


class FakeOpen:
    _open = builtins.open
    _lines = []
    _line_count = 0

    write = _skip
    close = _skip
    __exit__ = _skip

    def __iter__(self):
        return iter(self._lines)

    def __enter__(self):
        return self

    def __call__(self, *_) -> FakeOpen:
        return self

    @classmethod
    def get_file_line(cls, lineno):
        if lineno > cls._line_count:
            return "\n"

        return cls._lines[lineno - 1]

    @classmethod
    def set_size(cls, size):
        print('set size to', cls._line_count)
        cls._lines = ['\n'] * size
        cls._line_count = len(cls._lines)

    @classmethod
    def write_block_to_disk(cls, blockn, content):
        cls._lines[blockn - 1] = str(content or '\n')

    @classmethod
    def read(cls):
        return ''.join(cls._lines)


fake_open = FakeOpen()


def hook_disk(disk):

    def init(func):

        def wrapped(disk_name, disk_size, cache_size):
            fake_open.set_size(disk_size)

            return func(disk_name, disk_size, cache_size)

        return wrapped

    disk.init = init(disk.init)
    disk.fs.fs.get_file_line = fake_open.get_file_line
    disk.fs.fs.write_block_to_disk = fake_open.write_block_to_disk
