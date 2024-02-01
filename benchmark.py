from typing import Callable
import random
import string
import timeit
import typing

import tp_sgf_new as disk
from vendor import fs as base_fs


def _provide_uniq_id(func):
    count = 0

    def inner(length: int):
        nonlocal count

        count += 1
        return func(length, count)
    return inner


@_provide_uniq_id
def _rand_ascii(length: int, id_: int) -> str:
    name = ''.join(random.choice(string.ascii_letters) for _ in range(length))
    return f"{id_}__{name}"


class User:

    @staticmethod
    def _select(typ: str) -> str | None:
        content = typing.cast(list[str], disk.ls())
        if typ not in "fd":
            raise ValueError

        selection = [f for f in content if f.endswith(typ)]
        if typ == 'd':
            selection.extend([".."] * 3) # Favour moving up

        if not selection:
            return None

        random.shuffle(selection)
        item = random.choice(selection)
        print(selection, item)
        return item


    @classmethod
    def cd(cls) -> None:
        disk.cd(cls._select('d') or "..")

    @classmethod
    def create_file(cls) -> None:
        filename = _rand_ascii(16) + 'f'
        disk.touch(filename)

        # It is way more likely to write within the file you created
        if not random.randint(0, 10):
            return None

        disk.write(filename, _rand_ascii(1000))

    @classmethod
    def create_dir(cls) -> None:
        dirname = _rand_ascii(16) + 'd'
        disk.mkdir(dirname)

        # It is likely to cd in that dir
        if not random.randint(0, 5):
            return None

        disk.cd(dirname)

    @classmethod
    def remove_item(cls) -> None:
        target = cls._select(random.choice("fd"))

        if target == '..':
            target = cls._select("f")
        if not target:
            return None

        disk.rm(target)

    @classmethod
    def read_file(cls) -> None:
        filename = cls._select('f')

        if not filename:
            return

        disk.read(filename)


UserMethod = Callable[[], None]
ACTIONS: set[tuple[UserMethod, int]] = {
    (User.create_file, 3),
    (User.create_dir, 3),
    (User.cd, 2),
    (User.read_file, 2),
    (User.remove_item, 1),
}


DISK_SIZE = 1204


def tester(cache_size: int):
    disk_name = f"experiment.disk.{_rand_ascii(8)}"

    print("initializing disk...")
    disk.init(disk_name, DISK_SIZE, cache_size)

    possible_actions, weights = zip(*ACTIONS)

    random.seed(3301)
    actions = typing.cast(list[UserMethod],
        random.choices(possible_actions, k=DISK_SIZE,
            weights=typing.cast(tuple[int, ...], weights)))

    for action in actions:
        print(action.__name__)
        action()


def main():
    times = {}

    disk.fs = base_fs
    times["base fs - no cache"] = timeit.timeit(lambda: tester(1))
    times["base fs"] = timeit.timeit(lambda: tester(32))

    print('\n'.join(f"[{k}]: {v}" for k, v in times.items()))


if __name__ == "__main__":
    main()
