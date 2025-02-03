# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com
"""
Entry point of the `cpybooster` module.
https://peps.python.org/pep-0523/
"""

from __future__ import print_function, absolute_import, division

from rpython_ext.rlib import cpython
if cpython.PY_MAJOR_VERSION == 3 and cpython.PY_MINOR_VERSION == 13:
    from cpybooster.cpython313 import eval_frame as cpybooster_eval_frame
else:
    assert False, "Unsupported python version: {}.{}.{}".format(cpython.PY_MAJOR_VERSION, cpython.PY_MINOR_VERSION, cpython.PY_MICRO_VERSION)
