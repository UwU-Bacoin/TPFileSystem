from __future__ import annotations
import builtins


def _skip(*_):
    pass


class FakeOpen:
    _open = builtins.open
    _lines = []
    _line_count = 0
    _content = None

    write = _skip
    close = _skip
    __exit__ = _skip

    def __iter__(self):
        return iter(self._lines)

    def __call__(self, *_) -> FakeOpen:
        return self

    __enter__ = __call__

    @classmethod
    def get_file_line(cls, lineno):
        if lineno > cls._line_count:
            return "\n"

        return cls._lines[lineno - 1]

    @classmethod
    def set_size(cls, size):
        print('set size to', cls._line_count)
        cls._lines = ['\n'] * size
        cls._line_count = size
        cls._content = None

    @classmethod
    def write_block_to_disk(cls, blockn, content):
        cls._lines[blockn - 1] = str(content or '\n')
        cls._content = None

    @classmethod
    def read(cls):
        if cls._content is not None:
            return cls._content

        cls._content = ''.join(cls._lines)
        return cls._content


fo = FakeOpen()


def hook_disk(disk):

    def init(func):

        def wrapped(disk_name, disk_size, cache_size):
            fo.set_size(disk_size)

            return func(disk_name, disk_size, cache_size)

        return wrapped

    disk.init = init(disk.init)
    disk.fs.fs.get_file_line = fo.get_file_line
    disk.fs.fs.write_block_to_disk = fo.write_block_to_disk
    builtins.open = fo


def nuke_blockcache_system(disk):
    _blocks = {}
    _next_block = 0

    def write_block(_, blockn, content):
        nonlocal _next_block

        if _next_block < blockn:
            _next_block = blockn

        print("Write block", blockn)
        _blocks[blockn] = content

    def read_block(self, blockn):
        print("Read block", blockn)
        blk = _blocks.get(blockn)
        if blk is not None:
            return blk

        blk = self.read_block_from_disk(blockn)
        self.write(blockn, blk)
        return blk

    def find_free_block(_):
        return _next_block + 1

    disk.fs.fs.read_block = read_block
    disk.fs.fs.write_block = write_block
    disk.fs.fs.get_cache_for = read_block
    disk.fs.fs.find_free_block = find_free_block


def override_copy(disk):

    class FakeCopy:

        @staticmethod
        def deepcopy(n):
            return n

    disk.fs.copy = FakeCopy
