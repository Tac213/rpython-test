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


def add(a, b):
    # type: (float, float) -> float
    """
    Add two floating numbers.
    """
    return a + b


def substract(a, b):
    # type: (float, float) -> float
    """
    Substract two floating numbers.
    """
    return a - b


def print_int(s):
    # type: (int) -> None
    """
    Print an interger.
    """
    print(s)


def target(driver, args):
    # type: (CPythonExtensionTranslationDriver, list[str]) -> CPythonModuleDef
    return {
        add.__name__: (add, [float, float]),
        substract.__name__: (substract, [float, float]),
        print_int.__name__: (print_int, [int]),
    }
