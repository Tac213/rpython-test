# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com
"""
Entry point of the `cpybooster` module.
"""

from __future__ import print_function, absolute_import, division

from rpython.rlib.rarithmetic import r_int32
from rpython_ext.rlib import cpython


def cpybooster_eval_frame(tstate, frame, throwflag):
    return cpython.PyLong_FromLong(r_int32(0))
