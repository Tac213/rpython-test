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

from rpython_ext.rlib import cpython


def test(ts):
    a = cpython.PyThreadState_Get()
    cpython.PyThreadState_Clear(a)
    return


def target(driver, args):
    # type: (CPythonExtensionTranslationDriver, list[str]) -> CPythonModuleDef
    return {
        test.__name__: (test, [cpython.PyThreadState_P]),
    }
