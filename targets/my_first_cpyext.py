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
    return a + b


def substract(a, b):
    # type: (float, float) -> float
    return a - b


def target(driver, args):
    # type: (CPythonExtensionTranslationDriver, list[str]) -> CPythonModuleDef
    return {
        "add": (add, [float, float]),
        "substract": (substract, [float, float]),
    }
