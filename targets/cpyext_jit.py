# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division
try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from rpython_ext.translator.driver import CPythonExtensionTranslationDriver, CPythonModuleDef

try:
    from rpython.rlib.jit import JitDriver
except ImportError:
    class JitDriver(object):
        def __init__(self, greens, reds, is_recursive=False):
            # type: (list[str], str, bool) -> None
            pass

        def jit_merge_point(self):
            # type: () -> None
            pass


driver = JitDriver(greens=[], reds="auto")
driver2 = JitDriver(greens=[], reds="auto", is_recursive=True)


def main(count):
    # type: (int) -> list[int]
    i = 0
    l = []  # type: list[int]
    while i < count:
        driver.jit_merge_point()
        l.append(i)
        i += 1
    l = main2(l, count)
    return l


def main2(l, count):
    # type: (list[int], int) -> list[int]
    i = 0
    while i < count:
        driver2.jit_merge_point()
        l.pop()
        i += 1
    return l


def entry_point(count1, count2):
    # type: (int, int) -> None
    s = 0
    for _ in range(count1):
        s += len(main(count2))
    print(s)


def target(driver, args):
    # type: (CPythonExtensionTranslationDriver, list[str]) -> CPythonModuleDef
    return {
        entry_point.__name__: (entry_point, [int, int]),
    }


jit_entry_point = entry_point
