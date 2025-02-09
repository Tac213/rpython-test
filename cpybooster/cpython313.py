# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division
import inspect

from rpython.rlib.objectmodel import not_rpython, always_inline
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


@not_rpython
def _unique_str(s):
    # type: (str) -> str
    f = inspect.currentframe()
    assert f
    f = f.f_back
    assert f
    return "{}{}/* FILE: {} LINE: {} */".format(s, "  " if s else "", __file__, f.f_lineno)


GLOBAL_ECI = ExternalCompilationInfo(
    post_include_bits=[
        _unique_str("static const _Py_CODEUNIT _Py_INTERPRETER_TRAMPOLINE_INSTRUCTIONS[5];"),
        _unique_str("#ifndef Py_BUILD_CORE"),
        _unique_str("#define Py_BUILD_CORE"),
        _unique_str("#endif"),
        _unique_str("#include <internal/pycore_ceval.h>"),
        _unique_str("#ifdef Py_BUILD_CORE"),
        _unique_str("#undef Py_BUILD_CORE"),
        _unique_str("#endif"),
        _unique_str("#define EMPTY_CONST_CHARP \"\""),
        _unique_str(""),
        _unique_str("static inline void _Py_LeaveRecursiveCallPy(PyThreadState *tstate) {"),
        _unique_str("    tstate->py_recursion_remaining++;"),
        _unique_str("}"),
        _unique_str(""),
    ],
    separate_module_sources=[_EXTRA_C_SOURCE],
)

_Py_INTERPRETER_TRAMPOLINE_INSTRUCTIONS = rffi.CConstant(
    "_Py_INTERPRETER_TRAMPOLINE_INSTRUCTIONS",
    rffi.CArrayPtr(cpython._Py_CODEUNIT),
)

_Py_EnsureTstateNotNULL = rffi.llexternal("_Py_EnsureTstateNotNULL", [cpython.PyThreadState_P], lltype.Void, **cpython._llextkws)
_Py_EnterRecursiveCallTstate = rffi.llexternal("_Py_EnterRecursiveCallTstate", [cpython.PyThreadState_P, rffi.CONST_CCHARP], lltype.Bool, **cpython._llextkws)
_Py_LeaveRecursiveCallPy = rffi.llexternal("_Py_LeaveRecursiveCallPy", [cpython.PyThreadState_P], lltype.Void, **cpython._llextkws)
_PyEval_FrameClearAndPop = rffi.llexternal("_PyEval_FrameClearAndPop", [cpython.PyThreadState_P, cpython._PyInterpreterFrame_P], lltype.Void, **cpython._llextkws)

EMPTY_CONST_CHARP = rffi.CConstant("EMPTY_CONST_CHARP", rffi.CONST_CCHARP)
PY_EVAL_C_STACK_UNITS = 2
# region goto labels
START_FRAME = 1
RESUME_FRAME = 2
POP_4_ERROR = 3
POP_3_ERROR = 4
POP_2_ERROR = 5
POP_1_ERROR = 6
ERROR = 7
EXCEPTION_UNWIND = 8
EXIT_UNWIND = 9
RESUME_WITH_ERROR = 10
# endregion goto labels


def eval_frame(tstate, frame, throwflag):
    """
    RPython function, translated directly from _PyEval_EvalFrameDefault (Python/ceval.c).
    """
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
        return _goto(EXIT_UNWIND, tstate, frame, entry_frame)

    lltype.free(entry_frame, flavor="raw", track_allocation=False)
    return lltype.nullptr(cpython.PyObject)


@always_inline
def _goto(label, tstate, frame, entry_frame):
    """
    Implement the 'goto' statement of C.
    """
    if label == EXIT_UNWIND:
        _Py_LeaveRecursiveCallPy(tstate)
        # GH-99729: We need to unlink the frame *before* clearing it:
        dying = frame
        tstate.c_current_frame = dying.c_previous
        frame = tstate.c_current_frame
        _PyEval_FrameClearAndPop(tstate, dying)
        frame.c_return_offset = r_uint16(0)
        if llop.ptr_eq(lltype.Bool, frame, entry_frame):
            # Restore previous frame and exit
            tstate.c_current_frame = frame.c_previous
            tstate.c_c_recursion_remaining = llop.int_add(rffi.INT, tstate.c_c_recursion_remaining, PY_EVAL_C_STACK_UNITS)
            return lltype.nullptr(cpython.PyObject)
    return lltype.nullptr(cpython.PyObject)
