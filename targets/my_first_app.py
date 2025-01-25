from __future__ import print_function, absolute_import, division
try:
    from typing import Callable, TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False
if TYPE_CHECKING:
    from rpython.translator.driver import TranslationDriver


take_options = True


def entry_point(argv):  # type: (list[str]) -> int
    print("Hello world!!!")
    for i, arg in enumerate(argv):
        print("arg", i, arg)
    return 0


def target(driver, args):  # type: (TranslationDriver, list[str]) -> Callable[[list[str]], int]
    driver.log.info(args)
    driver.log.info(driver.exe_name)
    return entry_point
