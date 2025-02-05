# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division

from rpython.rlib.rarithmetic import r_int32
from rpython.rtyper.lltypesystem import lltype

from rpython_ext.rlib.rarithmetic import r_int8, r_uint16
from rpython_ext.rlib import cpython


PY_EVAL_C_STACK_UNITS = 2


def eval_frame(tstate, frame, throwflag):
    entry_frame = lltype.malloc(cpython._PyInterpreterFrame, flavor="raw", track_allocation=False)
    entry_frame.c_f_executable = cpython.Py_None
    # f_executable
    # instr_ptr
    entry_frame.c_stacktop = r_int32(0)
    entry_frame.c_owner = r_int8(cpython.FRAME_OWNED_BY_CSTACK)
    entry_frame.c_return_offset = r_uint16(0)
    # Push frame
    entry_frame.c_previous = tstate.c_current_frame
    frame.c_previous = entry_frame
    tstate.c_current_frame = frame
    tstate.c_c_recursion_remaining = r_int32(PY_EVAL_C_STACK_UNITS - 1)

    lltype.free(entry_frame, flavor="raw", track_allocation=False)
    return cpython.PyLong_FromLong(r_int32(0))
