# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division

from rpython.rlib.rarithmetic import r_int32
from rpython.rtyper.debug import ll_assert, ll_assert_not_none
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.translator.tool.cbuild import ExternalCompilationInfo

from rpython_ext.rlib.rarithmetic import r_int8, r_uint16
from rpython_ext.rlib import cpython

_EXTRA_C_SOURCE = r"""
#include <opcode.h>

#define RESUME_AT_FUNC_START 0
#define RESUME_AFTER_YIELD 1
#define RESUME_AFTER_YIELD_FROM 2
#define RESUME_AFTER_AWAIT 3

#define RESUME_OPARG_LOCATION_MASK 0x3
#define RESUME_OPARG_DEPTH1_MASK 0x4

const _Py_CODEUNIT _Py_INTERPRETER_TRAMPOLINE_INSTRUCTIONS[5] = {
    /* Put a NOP at the start, so that the IP points into
    * the code, rather than before it */
    { .op.code = NOP, .op.arg = 0 },
    { .op.code = INTERPRETER_EXIT, .op.arg = 0 },  /* reached on return */
    { .op.code = NOP, .op.arg = 0 },
    { .op.code = INTERPRETER_EXIT, .op.arg = 0 },  /* reached on yield */
    { .op.code = RESUME, .op.arg = RESUME_OPARG_DEPTH1_MASK | RESUME_AT_FUNC_START }
};
"""

GLOBAL_ECI = ExternalCompilationInfo(
    post_include_bits=[
        "static const _Py_CODEUNIT _Py_INTERPRETER_TRAMPOLINE_INSTRUCTIONS[5];",
        "#ifndef Py_BUILD_CORE  // {}".format(__file__),
        "#define Py_BUILD_CORE  // {}".format(__file__),
        "#endif  // {}.{}".format(__file__, 0),
        "#include <internal/pycore_ceval.h>  // {}".format(__file__),
        "#ifdef Py_BUILD_CORE  // {}".format(__file__),
        "#undef Py_BUILD_CORE  // {}".format(__file__),
        "#endif  // {}.{}".format(__file__, 1),
        "#define EMPTY_CONST_CHARP \"\"",
    ],
    separate_module_sources=[_EXTRA_C_SOURCE],
)

_Py_INTERPRETER_TRAMPOLINE_INSTRUCTIONS = rffi.CConstant(
    "_Py_INTERPRETER_TRAMPOLINE_INSTRUCTIONS",
    rffi.CArrayPtr(cpython._Py_CODEUNIT),
)

_Py_EnsureTstateNotNULL = rffi.llexternal("_Py_EnsureTstateNotNULL", [cpython.PyThreadState_P], lltype.Void, **cpython._llextkws)
_Py_EnterRecursiveCallTstate = rffi.llexternal("_Py_EnterRecursiveCallTstate", [cpython.PyThreadState_P, rffi.CONST_CCHARP], lltype.Bool, **cpython._llextkws)

EMPTY_CONST_CHARP = rffi.CConstant("EMPTY_CONST_CHARP", rffi.CONST_CCHARP)
PY_EVAL_C_STACK_UNITS = 2


def eval_frame(tstate, frame, throwflag):
    _Py_EnsureTstateNotNULL(tstate)

    entry_frame = lltype.malloc(cpython._PyInterpreterFrame, flavor="raw", track_allocation=False)
    entry_frame.c_f_executable = cpython.Py_None
    entry_frame.c_instr_ptr = rffi.cast(cpython._Py_CODEUNIT_P, rffi.ptradd(_Py_INTERPRETER_TRAMPOLINE_INSTRUCTIONS, 1))
    entry_frame.c_stacktop = r_int32(0)
    entry_frame.c_owner = r_int8(cpython.FRAME_OWNED_BY_CSTACK)
    entry_frame.c_return_offset = r_uint16(0)
    # Push frame
    entry_frame.c_previous = tstate.c_current_frame
    frame.c_previous = entry_frame
    tstate.c_current_frame = frame

    tstate.c_c_recursion_remaining = r_int32(PY_EVAL_C_STACK_UNITS - 1)
    if _Py_EnterRecursiveCallTstate(tstate, EMPTY_CONST_CHARP):
        tstate.c_c_recursion_remaining = llop.int_sub(rffi.INT, tstate.c_c_recursion_remaining, 1)
        tstate.c_py_recursion_remaining = llop.int_sub(rffi.INT, tstate.c_py_recursion_remaining, 1)

    lltype.free(entry_frame, flavor="raw", track_allocation=False)
    return cpython.PyLong_FromLong(r_int32(0))


def clear_thread_frame(tstate, frame):
    ll_assert(llop.int_eq(lltype.Bool, frame.c_owner, r_int8(cpython.FRAME_OWNED_BY_THREAD)), "")
    tstate.c_c_recursion_remaining = llop.int_sub(rffi.INT, tstate.c_c_recursion_remaining, 1)
    _PyFrame_ClearExceptCode(frame)
    cpython.Py_DECREF(frame.c_f_executable)
    tstate.c_c_recursion_remaining = llop.int_add(rffi.INT, tstate.c_c_recursion_remaining, 1)
    cpython._PyThreadState_PopFrame(tstate, frame)


def _PyFrame_ClearExceptCode(frame):
    cpython.Py_DECREF(frame.c_f_funcobj)
