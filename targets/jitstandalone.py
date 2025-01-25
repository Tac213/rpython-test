"""
Only the JIT
"""

from __future__ import print_function, absolute_import, division
try:
    from typing import Callable, TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False
import sys
import time
if TYPE_CHECKING:
    from rpython.translator.driver import TranslationDriver
try:
    from rpython.rlib.jit import JitDriver
except ImportError:
    class JitDriver(object):
        def __init__(self, greens, reds, is_recursive=False):  # type: (list[str], str, bool) -> None
            pass

        def jit_merge_point(self):  # type: () -> None
            pass


driver = JitDriver(greens=[], reds="auto")
driver2 = JitDriver(greens=[], reds="auto", is_recursive=True)


def main(count):  # type: (int) -> list[int]
    i = 0
    l = []  # type: list[int]
    while i < count:
        driver.jit_merge_point()
        l.append(i)
        i += 1
    l = main2(l, count)
    return l


def main2(l, count):  # type: (list[int], int) -> list[int]
    i = 0
    while i < count:
        driver2.jit_merge_point()
        l.pop()
        i += 1
    return l


def entry_point(argv):  # type: (list[str]) -> int
    if len(argv) < 3:
        print("Usage: jitstandalone <count1> <count2>")
        print("runs a total of '2 * count1 * count2' iterations")
        return 0
    t0 = time.time()
    count1 = int(argv[1])
    count2 = int(argv[2])
    s = 0
    for _ in range(count1):
        s += len(main(count2))
    print(s)
    print(time.time() - t0)
    return 0


def target(driver, args):  # type: (TranslationDriver, list[str]) -> Callable[[list[str]], int]
    driver.log.info(args)
    driver.log.info(driver.exe_name)
    return entry_point


if __name__ == "__main__":
    sys.exit(entry_point(sys.argv))
