import builtins
import random
from enum import IntEnum, auto
from functools import wraps
from string import ascii_letters
from typing import Callable, TypeVar, List, Tuple

from vendor import fs
import tp_sgf_new as disk

disk.fs_log_on()


class Dir:
    __next_dir = None

    def __init__(self, parent):
        self.__parent = parent
        self.dirs = {}
        self.files = set()

    @property
    def parent(self):
        if self.__parent is not None:
            return self.__parent
        return self

    @property
    def actions(self):
        _ac = [create_file, create_dir, go_up]

        if self.dirs:
            _ac.append(move_to_folder)
        if self.files:
            _ac.extend((read_file, write_file))
        if len(_ac) > 3:
            _ac.append(remove)

        return _ac

    @property
    def next_dir(self):
        if self.__next_dir is None:
            return self

        d = self.__next_dir
        self.__next_dir = None
        return d

    @classmethod
    def set_next_dir(cls, new_dir):
        cls.__next_dir = new_dir


class FakeOpen:
    content = ''

    _computed_lines = None
    _line_count = 0

    def __init__(self, filename, mode):
        self.filename = filename
        self.mode = mode

    @classmethod
    def __compute_lines(cls):
        cls._computed_lines = cls.content.splitlines()
        cls._line_count = len(cls._computed_lines)
        print("=>", cls._line_count)

    @classmethod
    def write(cls, content):
        cls.content = content
        cls.__compute_lines()

    @classmethod
    def get_file_line(cls, lineno):
        if lineno >= cls._line_count:
            return "\n"
        return cls._computed_lines[lineno - 1]

    @classmethod
    def set_size(cls, size):
        cls._computed_lines = [''] * size
        cls.content = '\n'.join(cls._computed_lines)
        cls._line_count = len(cls._computed_lines)
        print('line count', cls._line_count)

    @classmethod
    def write_block_to_disk(cls, blockn, content):
        cls._computed_lines[blockn - 1] = str(content or '\n')
        cls.content = '\n'.join(cls._computed_lines)

    @classmethod
    def read(cls):
        return cls.content

    def __iter__(self):
        if not self._computed_lines:
            self.__compute_lines()

        for line in self._computed_lines:
            yield line

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return

    def close(self):
        pass


T = TypeVar('T')
DirContent = Tuple[List[str], List[str]]
DiskAction = Callable[[Dir], str]


class FSType(IntEnum):
    DIRECTORY = auto()
    FILE = auto()
    SPECIAL = auto()


CACHE_TYPES = {
    '.': FSType.SPECIAL,
    '..': FSType.SPECIAL
}


def _provide_uniq_id(func):
    count = 0

    def inner(length: int):
        nonlocal count

        count += 1
        return func(length, count)
    return inner


@_provide_uniq_id
def _rand_ascii(length: int, id_: int) -> str:
    name = ''.join(random.choice(ascii_letters) for _ in range(length))
    return f"{id_}__{name}"


def _no_args(func: Callable[[], T]) -> Callable[[DirContent], T]:

    @wraps(func)
    def inner(_dirs=None, _files=None) -> T:
        return func()

    return inner


def create_file(cur_dir: Dir):
    filename = _rand_ascii(32)
    CACHE_TYPES[filename] = FSType.FILE
    disk.touch(filename)
    cur_dir.files.add(filename)
    return f"TOUCH {filename}"


def go_up(cur_dir: Dir):
    disk.cd('..')
    cur_dir.set_next_dir(cur_dir.parent)
    return "[CD] .."


def create_dir(cur_dir):
    dirname = _rand_ascii(32)
    CACHE_TYPES[dirname] = FSType.DIRECTORY
    disk.mkdir(dirname)
    cur_dir.dirs[dirname] = Dir(parent=cur_dir)
    return f"[MKDIR] {dirname}"


def read_file(cur_dir: Dir):
    filename = random.choice(tuple(cur_dir.files))
    disk.read(filename)
    return f'[READ] {filename}'


def write_file(cur_dir: Dir):
    filename = random.choice(tuple(cur_dir.files))
    content = _rand_ascii(random.randint(0, 1000))
    disk.write(filename, content)
    return f'[WRITE] {filename} - {len(content)} chars'


def remove(cur_dir: Dir):
    if cur_dir.files and random.randint(0, 1):
        filename = random.choice(tuple(cur_dir.files))
        disk.rm(filename)
        cur_dir.files.remove(filename)
        return f'[RM] {filename}'

    elif cur_dir.dirs:
        dirname = random.choice(tuple(cur_dir.dirs))
        disk.rm(dirname)
        cur_dir.dirs.pop(dirname)
        return f'[RM] {dirname}'

    else:
        filename = random.choice(tuple(cur_dir.files))
        disk.rm(filename)
        cur_dir.files.remove(filename)
        return f'[RM] {filename}'


def move_to_folder(cur_dir: Dir):
    folder = random.choice(tuple(cur_dir.dirs.keys()))
    cur_dir.set_next_dir(cur_dir.dirs[folder])
    disk.cd(folder)
    return f'[CD] {folder}'


@_no_args
def ls():
    disk.ls()


def main():
    _open = builtins.open
    builtins.open = FakeOpen

    fs.fs.get_file_line = FakeOpen.get_file_line
    fs.fs.write_block_to_disk = FakeOpen.write_block_to_disk

    disk_size = 500
    cache_size = 40
    FakeOpen.set_size(disk_size)

    disk_name = "experiment_disk"
    print("initializing disk...")
    disk.init(disk_name, disk_size, cache_size)

    fs_structure = Dir(None)
    current_dir = fs_structure

    print("start")
    for i in range(500):
        action: DiskAction = random.choice(current_dir.actions)

        try:
            log = action(current_dir)
        except Exception as e:
            break
        else:
            print("->", i, log)

        current_dir = current_dir.next_dir
        disk.sync()

    builtins.open = _open
    with open(disk_name, 'w') as f:
        f.write(FakeOpen.content)
    print('---')
    fs.fs_stats()


if __name__ == '__main__':
    main()
