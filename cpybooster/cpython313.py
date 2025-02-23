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
#include <internal/pycore_code.h>

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

int _Py_CheckRecursiveCallPy(
    PyThreadState *tstate)
{
    if (tstate->recursion_headroom) {
        if (tstate->py_recursion_remaining < -50) {
            /* Overflowing while handling an overflow. Give up. */
            Py_FatalError("Cannot recover from Python stack overflow.");
        }
    }
    else {
        if (tstate->py_recursion_remaining <= 0) {
            tstate->recursion_headroom++;
            _PyErr_Format(tstate, PyExc_RecursionError,
                        "maximum recursion depth exceeded");
            tstate->recursion_headroom--;
            return -1;
        }
    }
    return 0;
}

static inline unsigned char *
scan_back_to_entry_start(unsigned char *p) {
    for (; (p[0]&128) == 0; p--);
    return p;
}

static inline unsigned char *
skip_to_next_entry(unsigned char *p, unsigned char *end) {
    while (p < end && ((p[0] & 128) == 0)) {
        p++;
    }
    return p;
}

#define MAX_LINEAR_SEARCH 40

int get_exception_handler(PyCodeObject *code, int index, int *level, int *handler, int *lasti)
{
    unsigned char *start = (unsigned char *)PyBytes_AS_STRING(code->co_exceptiontable);
    unsigned char *end = start + PyBytes_GET_SIZE(code->co_exceptiontable);
    /* Invariants:
     * start_table == end_table OR
     * start_table points to a legal entry and end_table points
     * beyond the table or to a legal entry that is after index.
     */
    if (end - start > MAX_LINEAR_SEARCH) {
        int offset;
        parse_varint(start, &offset);
        if (offset > index) {
            return 0;
        }
        do {
            unsigned char * mid = start + ((end-start)>>1);
            mid = scan_back_to_entry_start(mid);
            parse_varint(mid, &offset);
            if (offset > index) {
                end = mid;
            }
            else {
                start = mid;
            }

        } while (end - start > MAX_LINEAR_SEARCH);
    }
    unsigned char *scan = start;
    while (scan < end) {
        int start_offset, size;
        scan = parse_varint(scan, &start_offset);
        if (start_offset > index) {
            break;
        }
        scan = parse_varint(scan, &size);
        if (start_offset + size > index) {
            scan = parse_varint(scan, handler);
            int depth_and_lasti;
            parse_varint(scan, &depth_and_lasti);
            *level = depth_and_lasti >> 1;
            *lasti = depth_and_lasti & 1;
            return 1;
        }
        scan = skip_to_next_entry(scan, end);
    }
    return 0;
}

static int
do_monitor_exc(PyThreadState *tstate, _PyInterpreterFrame *frame,
               _Py_CODEUNIT *instr, int event)
{
    assert(event < _PY_MONITORING_UNGROUPED_EVENTS);
    if (_PyFrame_GetCode(frame)->co_flags & CO_NO_MONITORING_EVENTS) {
        return 0;
    }
    PyObject *exc = PyErr_GetRaisedException();
    assert(exc != NULL);
    int err = _Py_call_instrumentation_arg(tstate, event, frame, instr, exc);
    if (err == 0) {
        PyErr_SetRaisedException(exc);
    }
    else {
        assert(PyErr_Occurred());
        Py_DECREF(exc);
    }
    return err;
}

static inline bool
no_tools_for_global_event(PyThreadState *tstate, int event)
{
    return tstate->interp->monitors.tools[event] == 0;
}

static inline bool
no_tools_for_local_event(PyThreadState *tstate, _PyInterpreterFrame *frame, int event)
{
    assert(event < _PY_MONITORING_LOCAL_EVENTS);
    _PyCoMonitoringData *data = _PyFrame_GetCode(frame)->_co_monitoring;
    if (data) {
        return data->active_monitors.tools[event] == 0;
    }
    else {
        return no_tools_for_global_event(tstate, event);
    }
}

void
monitor_reraise(PyThreadState *tstate, _PyInterpreterFrame *frame,
              _Py_CODEUNIT *instr)
{
    if (no_tools_for_global_event(tstate, PY_MONITORING_EVENT_RERAISE)) {
        return;
    }
    do_monitor_exc(tstate, frame, instr, PY_MONITORING_EVENT_RERAISE);
}

int
monitor_stop_iteration(PyThreadState *tstate, _PyInterpreterFrame *frame,
                       _Py_CODEUNIT *instr, PyObject *value)
{
    if (no_tools_for_local_event(tstate, frame, PY_MONITORING_EVENT_STOP_ITERATION)) {
        return 0;
    }
    assert(!PyErr_Occurred());
    PyErr_SetObject(PyExc_StopIteration, value);
    int res = do_monitor_exc(tstate, frame, instr, PY_MONITORING_EVENT_STOP_ITERATION);
    if (res < 0) {
        return res;
    }
    PyErr_SetRaisedException(NULL);
    return 0;
}

void
monitor_unwind(PyThreadState *tstate,
               _PyInterpreterFrame *frame,
               _Py_CODEUNIT *instr)
{
    if (no_tools_for_global_event(tstate, PY_MONITORING_EVENT_PY_UNWIND)) {
        return;
    }
    do_monitor_exc(tstate, frame, instr, PY_MONITORING_EVENT_PY_UNWIND);
}


int
monitor_handled(PyThreadState *tstate,
                _PyInterpreterFrame *frame,
                _Py_CODEUNIT *instr, PyObject *exc)
{
    if (no_tools_for_global_event(tstate, PY_MONITORING_EVENT_EXCEPTION_HANDLED)) {
        return 0;
    }
    return _Py_call_instrumentation_arg(tstate, PY_MONITORING_EVENT_EXCEPTION_HANDLED, frame, instr, exc);
}

void
monitor_throw(PyThreadState *tstate,
              _PyInterpreterFrame *frame,
              _Py_CODEUNIT *instr)
{
    if (no_tools_for_global_event(tstate, PY_MONITORING_EVENT_PY_THROW)) {
        return;
    }
    do_monitor_exc(tstate, frame, instr, PY_MONITORING_EVENT_PY_THROW);
}
"""

_INSTRUMENTATION_SOURCE = r"""
#include "opcode_ids.h"
#ifndef Py_BUILD_CORE
#define Py_BUILD_CORE
#endif
#include "internal/pycore_bitutils.h"      // _Py_popcount32
#include "internal/pycore_call.h"
#include "internal/pycore_ceval.h"         // _PY_EVAL_EVENTS_BITS
#include "internal/pycore_code.h"          // _PyCode_Clear_Executors()
#include "internal/pycore_critical_section.h"
#include "internal/pycore_frame.h"
#include "internal/pycore_interp.h"
#include "internal/pycore_long.h"
#include "internal/pycore_modsupport.h"    // _PyModule_CreateInitialized()
#include "internal/pycore_namespace.h"
#include "internal/pycore_object.h"
#include "internal/pycore_pyatomic_ft_wrappers.h" // FT_ATOMIC_STORE_UINTPTR_RELEASE
#include "internal/pycore_pyerrors.h"
#include "internal/pycore_pystate.h"       // _PyInterpreterState_GET()
#ifdef Py_BUILD_CORE
#undef Py_BUILD_CORE
#endif

/* Uncomment this to dump debugging output when assertions fail */
// #define INSTRUMENT_DEBUG 1

#if defined(Py_DEBUG) && defined(Py_GIL_DISABLED)

#define ASSERT_WORLD_STOPPED_OR_LOCKED(obj)                         \
    if (!_PyInterpreterState_GET()->stoptheworld.world_stopped) {   \
        _Py_CRITICAL_SECTION_ASSERT_OBJECT_LOCKED(obj);             \
    }
#define ASSERT_WORLD_STOPPED() assert(_PyInterpreterState_GET()->stoptheworld.world_stopped);

#else

#define ASSERT_WORLD_STOPPED_OR_LOCKED(obj)
#define ASSERT_WORLD_STOPPED()

#endif

#ifdef Py_GIL_DISABLED

#define LOCK_CODE(code)                                             \
    assert(!_PyInterpreterState_GET()->stoptheworld.world_stopped); \
    Py_BEGIN_CRITICAL_SECTION(code)

#define UNLOCK_CODE()   Py_END_CRITICAL_SECTION()

#else

#define LOCK_CODE(code)
#define UNLOCK_CODE()

#endif

typedef struct {
    PyObject_HEAD
    /* Type-specific fields go here. */
} CustomObject;

static PyTypeObject CustomType = {
    .ob_base = PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "custom.Custom",
    .tp_doc = PyDoc_STR("Custom objects"),
    .tp_basicsize = sizeof(CustomObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = PyType_GenericNew,
};

PyObject _PyInstrumentation_DISABLE = _PyObject_HEAD_INIT(&CustomType);

PyObject _PyInstrumentation_MISSING = _PyObject_HEAD_INIT(&CustomType);

static const int8_t EVENT_FOR_OPCODE[256] = {
    [RETURN_CONST] = PY_MONITORING_EVENT_PY_RETURN,
    [INSTRUMENTED_RETURN_CONST] = PY_MONITORING_EVENT_PY_RETURN,
    [RETURN_VALUE] = PY_MONITORING_EVENT_PY_RETURN,
    [INSTRUMENTED_RETURN_VALUE] = PY_MONITORING_EVENT_PY_RETURN,
    [CALL] = PY_MONITORING_EVENT_CALL,
    [INSTRUMENTED_CALL] = PY_MONITORING_EVENT_CALL,
    [CALL_KW] = PY_MONITORING_EVENT_CALL,
    [INSTRUMENTED_CALL_KW] = PY_MONITORING_EVENT_CALL,
    [CALL_FUNCTION_EX] = PY_MONITORING_EVENT_CALL,
    [INSTRUMENTED_CALL_FUNCTION_EX] = PY_MONITORING_EVENT_CALL,
    [LOAD_SUPER_ATTR] = PY_MONITORING_EVENT_CALL,
    [INSTRUMENTED_LOAD_SUPER_ATTR] = PY_MONITORING_EVENT_CALL,
    [RESUME] = -1,
    [YIELD_VALUE] = PY_MONITORING_EVENT_PY_YIELD,
    [INSTRUMENTED_YIELD_VALUE] = PY_MONITORING_EVENT_PY_YIELD,
    [JUMP_FORWARD] = PY_MONITORING_EVENT_JUMP,
    [JUMP_BACKWARD] = PY_MONITORING_EVENT_JUMP,
    [POP_JUMP_IF_FALSE] = PY_MONITORING_EVENT_BRANCH,
    [POP_JUMP_IF_TRUE] = PY_MONITORING_EVENT_BRANCH,
    [POP_JUMP_IF_NONE] = PY_MONITORING_EVENT_BRANCH,
    [POP_JUMP_IF_NOT_NONE] = PY_MONITORING_EVENT_BRANCH,
    [INSTRUMENTED_JUMP_FORWARD] = PY_MONITORING_EVENT_JUMP,
    [INSTRUMENTED_JUMP_BACKWARD] = PY_MONITORING_EVENT_JUMP,
    [INSTRUMENTED_POP_JUMP_IF_FALSE] = PY_MONITORING_EVENT_BRANCH,
    [INSTRUMENTED_POP_JUMP_IF_TRUE] = PY_MONITORING_EVENT_BRANCH,
    [INSTRUMENTED_POP_JUMP_IF_NONE] = PY_MONITORING_EVENT_BRANCH,
    [INSTRUMENTED_POP_JUMP_IF_NOT_NONE] = PY_MONITORING_EVENT_BRANCH,
    [FOR_ITER] = PY_MONITORING_EVENT_BRANCH,
    [INSTRUMENTED_FOR_ITER] = PY_MONITORING_EVENT_BRANCH,
    [END_FOR] = PY_MONITORING_EVENT_STOP_ITERATION,
    [INSTRUMENTED_END_FOR] = PY_MONITORING_EVENT_STOP_ITERATION,
    [END_SEND] = PY_MONITORING_EVENT_STOP_ITERATION,
    [INSTRUMENTED_END_SEND] = PY_MONITORING_EVENT_STOP_ITERATION,
};

static const uint8_t DE_INSTRUMENT[256] = {
    [INSTRUMENTED_RESUME] = RESUME,
    [INSTRUMENTED_RETURN_VALUE] = RETURN_VALUE,
    [INSTRUMENTED_RETURN_CONST] = RETURN_CONST,
    [INSTRUMENTED_CALL] = CALL,
    [INSTRUMENTED_CALL_KW] = CALL_KW,
    [INSTRUMENTED_CALL_FUNCTION_EX] = CALL_FUNCTION_EX,
    [INSTRUMENTED_YIELD_VALUE] = YIELD_VALUE,
    [INSTRUMENTED_JUMP_FORWARD] = JUMP_FORWARD,
    [INSTRUMENTED_JUMP_BACKWARD] = JUMP_BACKWARD,
    [INSTRUMENTED_POP_JUMP_IF_FALSE] = POP_JUMP_IF_FALSE,
    [INSTRUMENTED_POP_JUMP_IF_TRUE] = POP_JUMP_IF_TRUE,
    [INSTRUMENTED_POP_JUMP_IF_NONE] = POP_JUMP_IF_NONE,
    [INSTRUMENTED_POP_JUMP_IF_NOT_NONE] = POP_JUMP_IF_NOT_NONE,
    [INSTRUMENTED_FOR_ITER] = FOR_ITER,
    [INSTRUMENTED_END_FOR] = END_FOR,
    [INSTRUMENTED_END_SEND] = END_SEND,
    [INSTRUMENTED_LOAD_SUPER_ATTR] = LOAD_SUPER_ATTR,
};

static const uint8_t INSTRUMENTED_OPCODES[256] = {
    [RETURN_CONST] = INSTRUMENTED_RETURN_CONST,
    [INSTRUMENTED_RETURN_CONST] = INSTRUMENTED_RETURN_CONST,
    [RETURN_VALUE] = INSTRUMENTED_RETURN_VALUE,
    [INSTRUMENTED_RETURN_VALUE] = INSTRUMENTED_RETURN_VALUE,
    [CALL] = INSTRUMENTED_CALL,
    [INSTRUMENTED_CALL] = INSTRUMENTED_CALL,
    [CALL_KW] = INSTRUMENTED_CALL_KW,
    [INSTRUMENTED_CALL_KW] = INSTRUMENTED_CALL_KW,
    [CALL_FUNCTION_EX] = INSTRUMENTED_CALL_FUNCTION_EX,
    [INSTRUMENTED_CALL_FUNCTION_EX] = INSTRUMENTED_CALL_FUNCTION_EX,
    [YIELD_VALUE] = INSTRUMENTED_YIELD_VALUE,
    [INSTRUMENTED_YIELD_VALUE] = INSTRUMENTED_YIELD_VALUE,
    [RESUME] = INSTRUMENTED_RESUME,
    [INSTRUMENTED_RESUME] = INSTRUMENTED_RESUME,
    [JUMP_FORWARD] = INSTRUMENTED_JUMP_FORWARD,
    [INSTRUMENTED_JUMP_FORWARD] = INSTRUMENTED_JUMP_FORWARD,
    [JUMP_BACKWARD] = INSTRUMENTED_JUMP_BACKWARD,
    [INSTRUMENTED_JUMP_BACKWARD] = INSTRUMENTED_JUMP_BACKWARD,
    [POP_JUMP_IF_FALSE] = INSTRUMENTED_POP_JUMP_IF_FALSE,
    [INSTRUMENTED_POP_JUMP_IF_FALSE] = INSTRUMENTED_POP_JUMP_IF_FALSE,
    [POP_JUMP_IF_TRUE] = INSTRUMENTED_POP_JUMP_IF_TRUE,
    [INSTRUMENTED_POP_JUMP_IF_TRUE] = INSTRUMENTED_POP_JUMP_IF_TRUE,
    [POP_JUMP_IF_NONE] = INSTRUMENTED_POP_JUMP_IF_NONE,
    [INSTRUMENTED_POP_JUMP_IF_NONE] = INSTRUMENTED_POP_JUMP_IF_NONE,
    [POP_JUMP_IF_NOT_NONE] = INSTRUMENTED_POP_JUMP_IF_NOT_NONE,
    [INSTRUMENTED_POP_JUMP_IF_NOT_NONE] = INSTRUMENTED_POP_JUMP_IF_NOT_NONE,
    [END_FOR] = INSTRUMENTED_END_FOR,
    [INSTRUMENTED_END_FOR] = INSTRUMENTED_END_FOR,
    [END_SEND] = INSTRUMENTED_END_SEND,
    [INSTRUMENTED_END_SEND] = INSTRUMENTED_END_SEND,
    [FOR_ITER] = INSTRUMENTED_FOR_ITER,
    [INSTRUMENTED_FOR_ITER] = INSTRUMENTED_FOR_ITER,
    [LOAD_SUPER_ATTR] = INSTRUMENTED_LOAD_SUPER_ATTR,
    [INSTRUMENTED_LOAD_SUPER_ATTR] = INSTRUMENTED_LOAD_SUPER_ATTR,

    [INSTRUMENTED_LINE] = INSTRUMENTED_LINE,
    [INSTRUMENTED_INSTRUCTION] = INSTRUMENTED_INSTRUCTION,
};

static inline bool
opcode_has_event(int opcode)
{
    return (
        opcode != INSTRUMENTED_LINE &&
        INSTRUMENTED_OPCODES[opcode] > 0
    );
}

static inline bool
is_instrumented(int opcode)
{
    assert(opcode != 0);
    assert(opcode != RESERVED);
    return opcode >= MIN_INSTRUMENTED_OPCODE;
}

#ifndef NDEBUG
static inline bool
monitors_equals(_Py_LocalMonitors a, _Py_LocalMonitors b)
{
    for (int i = 0; i < _PY_MONITORING_LOCAL_EVENTS; i++) {
        if (a.tools[i] != b.tools[i]) {
            return false;
        }
    }
    return true;
}
#endif

static inline _Py_LocalMonitors
monitors_sub(_Py_LocalMonitors a, _Py_LocalMonitors b)
{
    _Py_LocalMonitors res;
    for (int i = 0; i < _PY_MONITORING_LOCAL_EVENTS; i++) {
        res.tools[i] = a.tools[i] & ~b.tools[i];
    }
    return res;
}

#ifndef NDEBUG
static inline _Py_LocalMonitors
monitors_and(_Py_LocalMonitors a, _Py_LocalMonitors b)
{
    _Py_LocalMonitors res;
    for (int i = 0; i < _PY_MONITORING_LOCAL_EVENTS; i++) {
        res.tools[i] = a.tools[i] & b.tools[i];
    }
    return res;
}
#endif

/* The union of the *local* events in a and b.
 * Global events like RAISE are ignored.
 * Used for instrumentation, as only local
 * events get instrumented.
 */
static inline _Py_LocalMonitors
local_union(_Py_GlobalMonitors a, _Py_LocalMonitors b)
{
    _Py_LocalMonitors res;
    for (int i = 0; i < _PY_MONITORING_LOCAL_EVENTS; i++) {
        res.tools[i] = a.tools[i] | b.tools[i];
    }
    return res;
}

static inline bool
monitors_are_empty(_Py_LocalMonitors m)
{
    for (int i = 0; i < _PY_MONITORING_LOCAL_EVENTS; i++) {
        if (m.tools[i]) {
            return false;
        }
    }
    return true;
}

static inline bool
multiple_tools(_Py_LocalMonitors *m)
{
    for (int i = 0; i < _PY_MONITORING_LOCAL_EVENTS; i++) {
        if (_Py_popcount32(m->tools[i]) > 1) {
            return true;
        }
    }
    return false;
}

static inline _PyMonitoringEventSet
get_local_events(_Py_LocalMonitors *m, int tool_id)
{
    _PyMonitoringEventSet result = 0;
    for (int e = 0; e < _PY_MONITORING_LOCAL_EVENTS; e++) {
        if ((m->tools[e] >> tool_id) & 1) {
            result |= (1 << e);
        }
    }
    return result;
}

static inline _PyMonitoringEventSet
get_events(_Py_GlobalMonitors *m, int tool_id)
{
    _PyMonitoringEventSet result = 0;
    for (int e = 0; e < _PY_MONITORING_UNGROUPED_EVENTS; e++) {
        if ((m->tools[e] >> tool_id) & 1) {
            result |= (1 << e);
        }
    }
    return result;
}

/* Line delta.
 * 8 bit value.
 * if line_delta == -128:
 *     line = None # represented as -1
 * elif line_delta == -127 or line_delta == -126:
 *     line = PyCode_Addr2Line(code, offset * sizeof(_Py_CODEUNIT));
 * else:
 *     line = first_line  + (offset >> OFFSET_SHIFT) + line_delta;
 */

#define NO_LINE -128
#define COMPUTED_LINE_LINENO_CHANGE -127
#define COMPUTED_LINE -126

#define OFFSET_SHIFT 4

static int8_t
compute_line_delta(PyCodeObject *code, int offset, int line)
{
    if (line < 0) {
        return NO_LINE;
    }
    int delta = line - code->co_firstlineno - (offset >> OFFSET_SHIFT);
    if (delta <= INT8_MAX && delta > COMPUTED_LINE) {
        return delta;
    }
    return COMPUTED_LINE;
}

static int
compute_line(PyCodeObject *code, int offset, int8_t line_delta)
{
    if (line_delta > COMPUTED_LINE) {
        return code->co_firstlineno + (offset >> OFFSET_SHIFT) + line_delta;
    }
    if (line_delta == NO_LINE) {

        return -1;
    }
    assert(line_delta == COMPUTED_LINE || line_delta == COMPUTED_LINE_LINENO_CHANGE);
    /* Look it up */
    return PyCode_Addr2Line(code, offset * sizeof(_Py_CODEUNIT));
}

int
_PyInstruction_GetLength(PyCodeObject *code, int offset)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);

    int opcode = _PyCode_CODE(code)[offset].op.code;
    assert(opcode != 0);
    assert(opcode != RESERVED);
    if (opcode == INSTRUMENTED_LINE) {
        opcode = code->_co_monitoring->lines[offset].original_opcode;
    }
    if (opcode == INSTRUMENTED_INSTRUCTION) {
        opcode = code->_co_monitoring->per_instruction_opcodes[offset];
    }
    int deinstrumented = DE_INSTRUMENT[opcode];
    if (deinstrumented) {
        opcode = deinstrumented;
    }
    else {
        opcode = _PyOpcode_Deopt[opcode];
    }
    assert(opcode != 0);
    assert(!is_instrumented(opcode));
    if (opcode == ENTER_EXECUTOR) {
        int exec_index = _PyCode_CODE(code)[offset].op.arg;
        _PyExecutorObject *exec = code->co_executors->executors[exec_index];
        opcode = _PyOpcode_Deopt[exec->vm_data.opcode];

    }
    assert(opcode != ENTER_EXECUTOR);
    assert(opcode == _PyOpcode_Deopt[opcode]);
    return 1 + _PyOpcode_Caches[opcode];
}

#ifdef INSTRUMENT_DEBUG

static void
dump_instrumentation_data_tools(PyCodeObject *code, uint8_t *tools, int i, FILE*out)
{
    if (tools == NULL) {
        fprintf(out, "tools = NULL");
    }
    else {
        fprintf(out, "tools = %d", tools[i]);
    }
}

static void
dump_instrumentation_data_lines(PyCodeObject *code, _PyCoLineInstrumentationData *lines, int i, FILE*out)
{
    if (lines == NULL) {
        fprintf(out, ", lines = NULL");
    }
    else if (lines[i].original_opcode == 0) {
        fprintf(out, ", lines = {original_opcode = No LINE (0), line_delta = %d)", lines[i].line_delta);
    }
    else {
        fprintf(out, ", lines = {original_opcode = %s, line_delta = %d)", _PyOpcode_OpName[lines[i].original_opcode], lines[i].line_delta);
    }
}

static void
dump_instrumentation_data_line_tools(PyCodeObject *code, uint8_t *line_tools, int i, FILE*out)
{
    if (line_tools == NULL) {
        fprintf(out, ", line_tools = NULL");
    }
    else {
        fprintf(out, ", line_tools = %d", line_tools[i]);
    }
}

static void
dump_instrumentation_data_per_instruction(PyCodeObject *code, _PyCoMonitoringData *data, int i, FILE*out)
{
    if (data->per_instruction_opcodes == NULL) {
        fprintf(out, ", per-inst opcode = NULL");
    }
    else {
        fprintf(out, ", per-inst opcode = %s", _PyOpcode_OpName[data->per_instruction_opcodes[i]]);
    }
    if (data->per_instruction_tools == NULL) {
        fprintf(out, ", per-inst tools = NULL");
    }
    else {
        fprintf(out, ", per-inst tools = %d", data->per_instruction_tools[i]);
    }
}

static void
dump_global_monitors(const char *prefix, _Py_GlobalMonitors monitors, FILE*out)
{
    fprintf(out, "%s monitors:\n", prefix);
    for (int event = 0; event < _PY_MONITORING_UNGROUPED_EVENTS; event++) {
        fprintf(out, "    Event %d: Tools %x\n", event, monitors.tools[event]);
    }
}

static void
dump_local_monitors(const char *prefix, _Py_LocalMonitors monitors, FILE*out)
{
    fprintf(out, "%s monitors:\n", prefix);
    for (int event = 0; event < _PY_MONITORING_LOCAL_EVENTS; event++) {
        fprintf(out, "    Event %d: Tools %x\n", event, monitors.tools[event]);
    }
}

/* No error checking -- Don't use this for anything but experimental debugging */
static void
dump_instrumentation_data(PyCodeObject *code, int star, FILE*out)
{
    _PyCoMonitoringData *data = code->_co_monitoring;
    fprintf(out, "\n");
    PyObject_Print(code->co_name, out, Py_PRINT_RAW);
    fprintf(out, "\n");
    if (data == NULL) {
        fprintf(out, "NULL\n");
        return;
    }
    dump_global_monitors("Global", _PyInterpreterState_GET()->monitors, out);
    dump_local_monitors("Code", data->local_monitors, out);
    dump_local_monitors("Active", data->active_monitors, out);
    int code_len = (int)Py_SIZE(code);
    bool starred = false;
    for (int i = 0; i < code_len; i += _PyInstruction_GetLength(code, i)) {
        _Py_CODEUNIT *instr = &_PyCode_CODE(code)[i];
        int opcode = instr->op.code;
        if (i == star) {
            fprintf(out, "**  ");
            starred = true;
        }
        fprintf(out, "Offset: %d, line: %d %s: ", i, PyCode_Addr2Line(code, i*2), _PyOpcode_OpName[opcode]);
        dump_instrumentation_data_tools(code, data->tools, i, out);
        dump_instrumentation_data_lines(code, data->lines, i, out);
        dump_instrumentation_data_line_tools(code, data->line_tools, i, out);
        dump_instrumentation_data_per_instruction(code, data, i, out);
        fprintf(out, "\n");
        ;
    }
    if (!starred && star >= 0) {
        fprintf(out, "Error offset not at valid instruction offset: %d\n", star);
        fprintf(out, "    ");
        dump_instrumentation_data_tools(code, data->tools, star, out);
        dump_instrumentation_data_lines(code, data->lines, star, out);
        dump_instrumentation_data_line_tools(code, data->line_tools, star, out);
        dump_instrumentation_data_per_instruction(code, data, star, out);
        fprintf(out, "\n");
    }
}

#define CHECK(test) do { \
    if (!(test)) { \
        dump_instrumentation_data(code, i, stderr); \
    } \
    assert(test); \
} while (0)

static bool
valid_opcode(int opcode)
{
    if (opcode == INSTRUMENTED_LINE) {
        return true;
    }
    if (IS_VALID_OPCODE(opcode) &&
        opcode != CACHE &&
        opcode != RESERVED &&
        opcode < 255)
    {
       return true;
    }
    return false;
}

static void
sanity_check_instrumentation(PyCodeObject *code)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);

    _PyCoMonitoringData *data = code->_co_monitoring;
    if (data == NULL) {
        return;
    }
    _Py_GlobalMonitors global_monitors = _PyInterpreterState_GET()->monitors;
    _Py_LocalMonitors active_monitors;
    if (code->_co_monitoring) {
        _Py_LocalMonitors local_monitors = code->_co_monitoring->local_monitors;
        active_monitors = local_union(global_monitors, local_monitors);
    }
    else {
        _Py_LocalMonitors empty = (_Py_LocalMonitors) { 0 };
        active_monitors = local_union(global_monitors, empty);
    }
    assert(monitors_equals(
        code->_co_monitoring->active_monitors,
        active_monitors));
    int code_len = (int)Py_SIZE(code);
    for (int i = 0; i < code_len;) {
        _Py_CODEUNIT *instr = &_PyCode_CODE(code)[i];
        int opcode = instr->op.code;
        int base_opcode = _Py_GetBaseOpcode(code, i);
        CHECK(valid_opcode(opcode));
        CHECK(valid_opcode(base_opcode));
        if (opcode == INSTRUMENTED_INSTRUCTION) {
            opcode = data->per_instruction_opcodes[i];
            if (!is_instrumented(opcode)) {
                CHECK(_PyOpcode_Deopt[opcode] == opcode);
            }
        }
        if (opcode == INSTRUMENTED_LINE) {
            CHECK(data->lines);
            CHECK(valid_opcode(data->lines[i].original_opcode));
            opcode = data->lines[i].original_opcode;
            CHECK(opcode != END_FOR);
            CHECK(opcode != RESUME);
            CHECK(opcode != RESUME_CHECK);
            CHECK(opcode != INSTRUMENTED_RESUME);
            if (!is_instrumented(opcode)) {
                CHECK(_PyOpcode_Deopt[opcode] == opcode);
            }
            CHECK(opcode != INSTRUMENTED_LINE);
        }
        else if (data->lines) {
            /* If original_opcode is INSTRUMENTED_INSTRUCTION
             * *and* we are executing a INSTRUMENTED_LINE instruction
             * that has de-instrumented itself, then we will execute
             * an invalid INSTRUMENTED_INSTRUCTION */
            CHECK(data->lines[i].original_opcode != INSTRUMENTED_INSTRUCTION);
        }
        if (opcode == INSTRUMENTED_INSTRUCTION) {
            CHECK(data->per_instruction_opcodes[i] != 0);
            opcode = data->per_instruction_opcodes[i];
        }
        if (is_instrumented(opcode)) {
            CHECK(DE_INSTRUMENT[opcode] == base_opcode);
            int event = EVENT_FOR_OPCODE[DE_INSTRUMENT[opcode]];
            if (event < 0) {
                /* RESUME fixup */
                event = instr->op.arg ? 1: 0;
            }
            CHECK(active_monitors.tools[event] != 0);
        }
        if (data->lines && base_opcode != END_FOR) {
            int line1 = compute_line(code, i, data->lines[i].line_delta);
            int line2 = PyCode_Addr2Line(code, i*sizeof(_Py_CODEUNIT));
            CHECK(line1 == line2);
        }
        CHECK(valid_opcode(opcode));
        if (data->tools) {
            uint8_t local_tools = data->tools[i];
            if (opcode_has_event(base_opcode)) {
                int event = EVENT_FOR_OPCODE[base_opcode];
                if (event == -1) {
                    /* RESUME fixup */
                    event = _PyCode_CODE(code)[i].op.arg;
                }
                CHECK((active_monitors.tools[event] & local_tools) == local_tools);
            }
            else {
                CHECK(local_tools == 0xff);
            }
        }
        i += _PyInstruction_GetLength(code, i);
        assert(i <= code_len);
    }
}
#else

#define CHECK(test) assert(test)

#endif

/* Get the underlying opcode, stripping instrumentation */
int _Py_GetBaseOpcode(PyCodeObject *code, int i)
{
    int opcode = _PyCode_CODE(code)[i].op.code;
    if (opcode == INSTRUMENTED_LINE) {
        opcode = code->_co_monitoring->lines[i].original_opcode;
    }
    if (opcode == INSTRUMENTED_INSTRUCTION) {
        opcode = code->_co_monitoring->per_instruction_opcodes[i];
    }
    CHECK(opcode != INSTRUMENTED_INSTRUCTION);
    CHECK(opcode != INSTRUMENTED_LINE);
    int deinstrumented = DE_INSTRUMENT[opcode];
    if (deinstrumented) {
        return deinstrumented;
    }
    return _PyOpcode_Deopt[opcode];
}

static void
de_instrument(PyCodeObject *code, int i, int event)
{
    assert(event != PY_MONITORING_EVENT_INSTRUCTION);
    assert(event != PY_MONITORING_EVENT_LINE);

    _Py_CODEUNIT *instr = &_PyCode_CODE(code)[i];
    uint8_t *opcode_ptr = &instr->op.code;
    int opcode = *opcode_ptr;
    assert(opcode != ENTER_EXECUTOR);
    if (opcode == INSTRUMENTED_LINE) {
        opcode_ptr = &code->_co_monitoring->lines[i].original_opcode;
        opcode = *opcode_ptr;
    }
    if (opcode == INSTRUMENTED_INSTRUCTION) {
        opcode_ptr = &code->_co_monitoring->per_instruction_opcodes[i];
        opcode = *opcode_ptr;
    }
    int deinstrumented = DE_INSTRUMENT[opcode];
    if (deinstrumented == 0) {
        return;
    }
    CHECK(_PyOpcode_Deopt[deinstrumented] == deinstrumented);
    FT_ATOMIC_STORE_UINT8_RELAXED(*opcode_ptr, deinstrumented);
    if (_PyOpcode_Caches[deinstrumented]) {
        FT_ATOMIC_STORE_UINT16_RELAXED(instr[1].counter.as_counter,
                                       adaptive_counter_warmup().as_counter);
    }
}

static void
de_instrument_line(PyCodeObject *code, int i)
{
    _Py_CODEUNIT *instr = &_PyCode_CODE(code)[i];
    int opcode = instr->op.code;
    if (opcode != INSTRUMENTED_LINE) {
        return;
    }
    _PyCoLineInstrumentationData *lines = &code->_co_monitoring->lines[i];
    int original_opcode = lines->original_opcode;
    if (original_opcode == INSTRUMENTED_INSTRUCTION) {
        lines->original_opcode = code->_co_monitoring->per_instruction_opcodes[i];
    }
    CHECK(original_opcode != 0);
    CHECK(original_opcode == _PyOpcode_Deopt[original_opcode]);
    instr->op.code = original_opcode;
    if (_PyOpcode_Caches[original_opcode]) {
        instr[1].counter = adaptive_counter_warmup();
    }
    assert(instr->op.code != INSTRUMENTED_LINE);
}

static void
de_instrument_per_instruction(PyCodeObject *code, int i)
{
    _Py_CODEUNIT *instr = &_PyCode_CODE(code)[i];
    uint8_t *opcode_ptr = &instr->op.code;
    int opcode = *opcode_ptr;
    if (opcode == INSTRUMENTED_LINE) {
        opcode_ptr = &code->_co_monitoring->lines[i].original_opcode;
        opcode = *opcode_ptr;
    }
    if (opcode != INSTRUMENTED_INSTRUCTION) {
        return;
    }
    int original_opcode = code->_co_monitoring->per_instruction_opcodes[i];
    CHECK(original_opcode != 0);
    CHECK(original_opcode == _PyOpcode_Deopt[original_opcode]);
    *opcode_ptr = original_opcode;
    if (_PyOpcode_Caches[original_opcode]) {
        instr[1].counter = adaptive_counter_warmup();
    }
    assert(*opcode_ptr != INSTRUMENTED_INSTRUCTION);
    assert(instr->op.code != INSTRUMENTED_INSTRUCTION);
}


static void
instrument(PyCodeObject *code, int i)
{
    _Py_CODEUNIT *instr = &_PyCode_CODE(code)[i];
    uint8_t *opcode_ptr = &instr->op.code;
    int opcode =*opcode_ptr;
    if (opcode == INSTRUMENTED_LINE) {
        _PyCoLineInstrumentationData *lines = &code->_co_monitoring->lines[i];
        opcode_ptr = &lines->original_opcode;
        opcode = *opcode_ptr;
    }
    if (opcode == INSTRUMENTED_INSTRUCTION) {
        opcode_ptr = &code->_co_monitoring->per_instruction_opcodes[i];
        opcode = *opcode_ptr;
        CHECK(opcode != INSTRUMENTED_INSTRUCTION && opcode != INSTRUMENTED_LINE);
        CHECK(opcode == _PyOpcode_Deopt[opcode]);
    }
    CHECK(opcode != 0);
    if (!is_instrumented(opcode)) {
        int deopt = _PyOpcode_Deopt[opcode];
        int instrumented = INSTRUMENTED_OPCODES[deopt];
        assert(instrumented);
        FT_ATOMIC_STORE_UINT8_RELAXED(*opcode_ptr, instrumented);
        if (_PyOpcode_Caches[deopt]) {
          FT_ATOMIC_STORE_UINT16_RELAXED(instr[1].counter.as_counter,
                                         adaptive_counter_warmup().as_counter);
            instr[1].counter = adaptive_counter_warmup();
        }
    }
}

static void
instrument_line(PyCodeObject *code, int i)
{
    uint8_t *opcode_ptr = &_PyCode_CODE(code)[i].op.code;
    int opcode = *opcode_ptr;
    if (opcode == INSTRUMENTED_LINE) {
        return;
    }
    _PyCoLineInstrumentationData *lines = &code->_co_monitoring->lines[i];
    lines->original_opcode = _PyOpcode_Deopt[opcode];
    CHECK(lines->original_opcode > 0);
    *opcode_ptr = INSTRUMENTED_LINE;
}

static void
instrument_per_instruction(PyCodeObject *code, int i)
{
    _Py_CODEUNIT *instr = &_PyCode_CODE(code)[i];
    uint8_t *opcode_ptr = &instr->op.code;
    int opcode = *opcode_ptr;
    if (opcode == INSTRUMENTED_LINE) {
        _PyCoLineInstrumentationData *lines = &code->_co_monitoring->lines[i];
        opcode_ptr = &lines->original_opcode;
        opcode = *opcode_ptr;
    }
    if (opcode == INSTRUMENTED_INSTRUCTION) {
        assert(code->_co_monitoring->per_instruction_opcodes[i] > 0);
        return;
    }
    CHECK(opcode != 0);
    if (is_instrumented(opcode)) {
        code->_co_monitoring->per_instruction_opcodes[i] = opcode;
    }
    else {
        assert(opcode != 0);
        assert(_PyOpcode_Deopt[opcode] != 0);
        assert(_PyOpcode_Deopt[opcode] != RESUME);
        code->_co_monitoring->per_instruction_opcodes[i] = _PyOpcode_Deopt[opcode];
    }
    assert(code->_co_monitoring->per_instruction_opcodes[i] > 0);
    *opcode_ptr = INSTRUMENTED_INSTRUCTION;
}

static void
remove_tools(PyCodeObject * code, int offset, int event, int tools)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);
    assert(event != PY_MONITORING_EVENT_LINE);
    assert(event != PY_MONITORING_EVENT_INSTRUCTION);
    assert(PY_MONITORING_IS_INSTRUMENTED_EVENT(event));
    assert(opcode_has_event(_Py_GetBaseOpcode(code, offset)));
    _PyCoMonitoringData *monitoring = code->_co_monitoring;
    if (monitoring && monitoring->tools) {
        monitoring->tools[offset] &= ~tools;
        if (monitoring->tools[offset] == 0) {
            de_instrument(code, offset, event);
        }
    }
    else {
        /* Single tool */
        uint8_t single_tool = code->_co_monitoring->active_monitors.tools[event];
        assert(_Py_popcount32(single_tool) <= 1);
        if (((single_tool & tools) == single_tool)) {
            de_instrument(code, offset, event);
        }
    }
}

#ifndef NDEBUG
static bool
tools_is_subset_for_event(PyCodeObject * code, int event, int tools)
{
    int global_tools = _PyInterpreterState_GET()->monitors.tools[event];
    int local_tools = code->_co_monitoring->local_monitors.tools[event];
    return tools == ((global_tools | local_tools) & tools);
}
#endif

static void
remove_line_tools(PyCodeObject * code, int offset, int tools)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);

    assert(code->_co_monitoring);
    if (code->_co_monitoring->line_tools)
    {
        uint8_t *toolsptr = &code->_co_monitoring->line_tools[offset];
        *toolsptr &= ~tools;
        if (*toolsptr == 0 ) {
            de_instrument_line(code, offset);
        }
    }
    else {
        /* Single tool */
        uint8_t single_tool = code->_co_monitoring->active_monitors.tools[PY_MONITORING_EVENT_LINE];
        assert(_Py_popcount32(single_tool) <= 1);
        if (((single_tool & tools) == single_tool)) {
            de_instrument_line(code, offset);
        }
    }
}

static void
add_tools(PyCodeObject * code, int offset, int event, int tools)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);
    assert(event != PY_MONITORING_EVENT_LINE);
    assert(event != PY_MONITORING_EVENT_INSTRUCTION);
    assert(PY_MONITORING_IS_INSTRUMENTED_EVENT(event));
    assert(code->_co_monitoring);
    if (code->_co_monitoring &&
        code->_co_monitoring->tools
    ) {
        code->_co_monitoring->tools[offset] |= tools;
    }
    else {
        /* Single tool */
        assert(_Py_popcount32(tools) == 1);
        assert(tools_is_subset_for_event(code, event, tools));
    }
    instrument(code, offset);
}

static void
add_line_tools(PyCodeObject * code, int offset, int tools)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);

    assert(tools_is_subset_for_event(code, PY_MONITORING_EVENT_LINE, tools));
    assert(code->_co_monitoring);
    if (code->_co_monitoring->line_tools) {
        code->_co_monitoring->line_tools[offset] |= tools;
    }
    else {
        /* Single tool */
        assert(_Py_popcount32(tools) == 1);
    }
    instrument_line(code, offset);
}


static void
add_per_instruction_tools(PyCodeObject * code, int offset, int tools)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);

    assert(tools_is_subset_for_event(code, PY_MONITORING_EVENT_INSTRUCTION, tools));
    assert(code->_co_monitoring);
    if (code->_co_monitoring->per_instruction_tools) {
        code->_co_monitoring->per_instruction_tools[offset] |= tools;
    }
    else {
        /* Single tool */
        assert(_Py_popcount32(tools) == 1);
    }
    instrument_per_instruction(code, offset);
}


static void
remove_per_instruction_tools(PyCodeObject * code, int offset, int tools)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);

    assert(code->_co_monitoring);
    if (code->_co_monitoring->per_instruction_tools) {
        uint8_t *toolsptr = &code->_co_monitoring->per_instruction_tools[offset];
        *toolsptr &= ~tools;
        if (*toolsptr == 0) {
            de_instrument_per_instruction(code, offset);
        }
    }
    else {
        /* Single tool */
        uint8_t single_tool = code->_co_monitoring->active_monitors.tools[PY_MONITORING_EVENT_INSTRUCTION];
        assert(_Py_popcount32(single_tool) <= 1);
        if (((single_tool & tools) == single_tool)) {
            de_instrument_per_instruction(code, offset);
        }
    }
}


/* Return 1 if DISABLE returned, -1 if error, 0 otherwise */
static int
call_one_instrument(
    PyInterpreterState *interp, PyThreadState *tstate, PyObject **args,
    size_t nargsf, int8_t tool, int event)
{
    assert(0 <= tool && tool < 8);
    assert(tstate->tracing == 0);
    PyObject *instrument = interp->monitoring_callables[tool][event];
    if (instrument == NULL) {
        return 0;
    }
    int old_what = tstate->what_event;
    tstate->what_event = event;
    tstate->tracing++;
    PyObject *res = _PyObject_VectorcallTstate(tstate, instrument, args, nargsf, NULL);
    tstate->tracing--;
    tstate->what_event = old_what;
    if (res == NULL) {
        return -1;
    }
    Py_DECREF(res);
    return (res == &_PyInstrumentation_DISABLE);
}

static const int8_t MOST_SIGNIFICANT_BITS[16] = {
    -1, 0, 1, 1,
    2, 2, 2, 2,
    3, 3, 3, 3,
    3, 3, 3, 3,
};

/* We could use _Py_bit_length here, but that is designed for larger (32/64)
 * bit ints, and can perform relatively poorly on platforms without the
 * necessary intrinsics. */
static inline int most_significant_bit(uint8_t bits) {
    assert(bits != 0);
    if (bits > 15) {
        return MOST_SIGNIFICANT_BITS[bits>>4]+4;
    }
    return MOST_SIGNIFICANT_BITS[bits];
}

static uint32_t
global_version(PyInterpreterState *interp)
{
    uint32_t version = (uint32_t)_Py_atomic_load_uintptr_relaxed(
        &interp->ceval.instrumentation_version);
#ifdef Py_DEBUG
    PyThreadState *tstate = _PyThreadState_GET();
    uint32_t thread_version =
        (uint32_t)(_Py_atomic_load_uintptr_relaxed(&tstate->eval_breaker) &
                   ~_PY_EVAL_EVENTS_MASK);
    assert(thread_version == version);
#endif
    return version;
}

/* Atomically set the given version in the given location, without touching
   anything in _PY_EVAL_EVENTS_MASK. */
static void
set_version_raw(uintptr_t *ptr, uint32_t version)
{
    uintptr_t old = _Py_atomic_load_uintptr_relaxed(ptr);
    uintptr_t new;
    do {
        new = (old & _PY_EVAL_EVENTS_MASK) | version;
    } while (!_Py_atomic_compare_exchange_uintptr(ptr, &old, new));
}

static void
set_global_version(PyThreadState *tstate, uint32_t version)
{
    assert((version & _PY_EVAL_EVENTS_MASK) == 0);
    PyInterpreterState *interp = tstate->interp;
    set_version_raw(&interp->ceval.instrumentation_version, version);

#ifdef Py_GIL_DISABLED
    // Set the version on all threads in free-threaded builds.
    _PyRuntimeState *runtime = &_PyRuntime;
    HEAD_LOCK(runtime);
    for (tstate = interp->threads.head; tstate;
         tstate = PyThreadState_Next(tstate)) {
        set_version_raw(&tstate->eval_breaker, version);
    };
    HEAD_UNLOCK(runtime);
#else
    // Normal builds take the current version from instrumentation_version when
    // attaching a thread, so we only have to set the current thread's version.
    set_version_raw(&tstate->eval_breaker, version);
#endif
}

static bool
is_version_up_to_date(PyCodeObject *code, PyInterpreterState *interp)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);
    return global_version(interp) == code->_co_instrumentation_version;
}

#ifndef NDEBUG
static bool
instrumentation_cross_checks(PyInterpreterState *interp, PyCodeObject *code)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);
    _Py_LocalMonitors expected = local_union(
        interp->monitors,
        code->_co_monitoring->local_monitors);
    return monitors_equals(code->_co_monitoring->active_monitors, expected);
}

static int
debug_check_sanity(PyInterpreterState *interp, PyCodeObject *code)
{
    int res;
    LOCK_CODE(code);
    res = is_version_up_to_date(code, interp) &&
          instrumentation_cross_checks(interp, code);
    UNLOCK_CODE();
    return res;
}

#endif

static inline uint8_t
get_tools_for_instruction(PyCodeObject *code, PyInterpreterState *interp, int i, int event)
{
    uint8_t tools;
    assert(event != PY_MONITORING_EVENT_LINE);
    assert(event != PY_MONITORING_EVENT_INSTRUCTION);
    if (event >= _PY_MONITORING_UNGROUPED_EVENTS) {
        assert(event == PY_MONITORING_EVENT_C_RAISE ||
                event == PY_MONITORING_EVENT_C_RETURN);
        event = PY_MONITORING_EVENT_CALL;
    }
    if (PY_MONITORING_IS_INSTRUMENTED_EVENT(event)) {
        CHECK(debug_check_sanity(interp, code));
        if (code->_co_monitoring->tools) {
            tools = code->_co_monitoring->tools[i];
        }
        else {
            tools = code->_co_monitoring->active_monitors.tools[event];
        }
    }
    else {
        tools = interp->monitors.tools[event];
    }
    return tools;
}

static const char *const event_names [] = {
    [PY_MONITORING_EVENT_PY_START] = "PY_START",
    [PY_MONITORING_EVENT_PY_RESUME] = "PY_RESUME",
    [PY_MONITORING_EVENT_PY_RETURN] = "PY_RETURN",
    [PY_MONITORING_EVENT_PY_YIELD] = "PY_YIELD",
    [PY_MONITORING_EVENT_CALL] = "CALL",
    [PY_MONITORING_EVENT_LINE] = "LINE",
    [PY_MONITORING_EVENT_INSTRUCTION] = "INSTRUCTION",
    [PY_MONITORING_EVENT_JUMP] = "JUMP",
    [PY_MONITORING_EVENT_BRANCH] = "BRANCH",
    [PY_MONITORING_EVENT_C_RETURN] = "C_RETURN",
    [PY_MONITORING_EVENT_PY_THROW] = "PY_THROW",
    [PY_MONITORING_EVENT_RAISE] = "RAISE",
    [PY_MONITORING_EVENT_RERAISE] = "RERAISE",
    [PY_MONITORING_EVENT_EXCEPTION_HANDLED] = "EXCEPTION_HANDLED",
    [PY_MONITORING_EVENT_C_RAISE] = "C_RAISE",
    [PY_MONITORING_EVENT_PY_UNWIND] = "PY_UNWIND",
    [PY_MONITORING_EVENT_STOP_ITERATION] = "STOP_ITERATION",
};

static int
call_instrumentation_vector(
    PyThreadState *tstate, int event,
    _PyInterpreterFrame *frame, _Py_CODEUNIT *instr, Py_ssize_t nargs, PyObject *args[])
{
    if (tstate->tracing) {
        return 0;
    }
    assert(!_PyErr_Occurred(tstate));
    assert(args[0] == NULL);
    PyCodeObject *code = _PyFrame_GetCode(frame);
    assert(args[1] == NULL);
    args[1] = (PyObject *)code;
    int offset = (int)(instr - _PyCode_CODE(code));
    /* Offset visible to user should be the offset in bytes, as that is the
     * convention for APIs involving code offsets. */
    int bytes_offset = offset * (int)sizeof(_Py_CODEUNIT);
    PyObject *offset_obj = PyLong_FromLong(bytes_offset);
    if (offset_obj == NULL) {
        return -1;
    }
    assert(args[2] == NULL);
    args[2] = offset_obj;
    PyInterpreterState *interp = tstate->interp;
    uint8_t tools = get_tools_for_instruction(code, interp, offset, event);
    size_t nargsf = (size_t) nargs | PY_VECTORCALL_ARGUMENTS_OFFSET;
    PyObject **callargs = &args[1];
    int err = 0;
    while (tools) {
        int tool = most_significant_bit(tools);
        assert(tool >= 0 && tool < 8);
        assert(tools & (1 << tool));
        tools ^= (1 << tool);
        int res = call_one_instrument(interp, tstate, callargs, nargsf, tool, event);
        if (res == 0) {
            /* Nothing to do */
        }
        else if (res < 0) {
            /* error */
            err = -1;
            break;
        }
        else {
            /* DISABLE */
            if (!PY_MONITORING_IS_INSTRUMENTED_EVENT(event)) {
                PyErr_Format(PyExc_ValueError,
                              "Cannot disable %s events. Callback removed.",
                             event_names[event]);
                /* Clear tool to prevent infinite loop */
                Py_CLEAR(interp->monitoring_callables[tool][event]);
                err = -1;
                break;
            }
            else {
                LOCK_CODE(code);
                remove_tools(code, offset, event, 1 << tool);
                UNLOCK_CODE();
            }
        }
    }
    Py_DECREF(offset_obj);
    return err;
}

int
_Py_call_instrumentation(
    PyThreadState *tstate, int event,
    _PyInterpreterFrame *frame, _Py_CODEUNIT *instr)
{
    PyObject *args[3] = { NULL, NULL, NULL };
    return call_instrumentation_vector(tstate, event, frame, instr, 2, args);
}

int
_Py_call_instrumentation_arg(
    PyThreadState *tstate, int event,
    _PyInterpreterFrame *frame, _Py_CODEUNIT *instr, PyObject *arg)
{
    PyObject *args[4] = { NULL, NULL, NULL, arg };
    return call_instrumentation_vector(tstate, event, frame, instr, 3, args);
}

int
_Py_call_instrumentation_2args(
    PyThreadState *tstate, int event,
    _PyInterpreterFrame *frame, _Py_CODEUNIT *instr, PyObject *arg0, PyObject *arg1)
{
    PyObject *args[5] = { NULL, NULL, NULL, arg0, arg1 };
    return call_instrumentation_vector(tstate, event, frame, instr, 4, args);
}

_Py_CODEUNIT *
_Py_call_instrumentation_jump(
    PyThreadState *tstate, int event,
    _PyInterpreterFrame *frame, _Py_CODEUNIT *instr, _Py_CODEUNIT *target)
{
    assert(event == PY_MONITORING_EVENT_JUMP ||
           event == PY_MONITORING_EVENT_BRANCH);
    assert(frame->instr_ptr == instr);
    PyCodeObject *code = _PyFrame_GetCode(frame);
    int to = (int)(target - _PyCode_CODE(code));
    PyObject *to_obj = PyLong_FromLong(to * (int)sizeof(_Py_CODEUNIT));
    if (to_obj == NULL) {
        return NULL;
    }
    PyObject *args[4] = { NULL, NULL, NULL, to_obj };
    int err = call_instrumentation_vector(tstate, event, frame, instr, 3, args);
    Py_DECREF(to_obj);
    if (err) {
        return NULL;
    }
    if (frame->instr_ptr != instr) {
        /* The callback has caused a jump (by setting the line number) */
        return frame->instr_ptr;
    }
    return target;
}

static void
call_instrumentation_vector_protected(
    PyThreadState *tstate, int event,
    _PyInterpreterFrame *frame, _Py_CODEUNIT *instr, Py_ssize_t nargs, PyObject *args[])
{
    assert(_PyErr_Occurred(tstate));
    PyObject *exc = _PyErr_GetRaisedException(tstate);
    int err = call_instrumentation_vector(tstate, event, frame, instr, nargs, args);
    if (err) {
        Py_XDECREF(exc);
    }
    else {
        _PyErr_SetRaisedException(tstate, exc);
    }
    assert(_PyErr_Occurred(tstate));
}

void
_Py_call_instrumentation_exc2(
    PyThreadState *tstate, int event,
    _PyInterpreterFrame *frame, _Py_CODEUNIT *instr, PyObject *arg0, PyObject *arg1)
{
    assert(_PyErr_Occurred(tstate));
    PyObject *args[5] = { NULL, NULL, NULL, arg0, arg1 };
    call_instrumentation_vector_protected(tstate, event, frame, instr, 4, args);
}


int
_Py_Instrumentation_GetLine(PyCodeObject *code, int index)
{
    _PyCoMonitoringData *monitoring = code->_co_monitoring;
    assert(monitoring != NULL);
    assert(monitoring->lines != NULL);
    assert(index >= code->_co_firsttraceable);
    assert(index < Py_SIZE(code));
    _PyCoLineInstrumentationData *line_data = &monitoring->lines[index];
    int8_t line_delta = line_data->line_delta;
    int line = compute_line(code, index, line_delta);
    return line;
}

int
_Py_call_instrumentation_line(PyThreadState *tstate, _PyInterpreterFrame* frame, _Py_CODEUNIT *instr, _Py_CODEUNIT *prev)
{
    PyCodeObject *code = _PyFrame_GetCode(frame);
    assert(tstate->tracing == 0);
    assert(debug_check_sanity(tstate->interp, code));
    int i = (int)(instr - _PyCode_CODE(code));

    _PyCoMonitoringData *monitoring = code->_co_monitoring;
    _PyCoLineInstrumentationData *line_data = &monitoring->lines[i];
    PyInterpreterState *interp = tstate->interp;
    int8_t line_delta = line_data->line_delta;
    int line = 0;

    if (line_delta == COMPUTED_LINE_LINENO_CHANGE) {
        // We know the line number must have changed, don't need to calculate
        // the line number for now because we might not need it.
        line = -1;
    } else {
        line = compute_line(code, i, line_delta);
        assert(line >= 0);
        assert(prev != NULL);
        int prev_index = (int)(prev - _PyCode_CODE(code));
        int prev_line = _Py_Instrumentation_GetLine(code, prev_index);
        if (prev_line == line) {
            int prev_opcode = _PyCode_CODE(code)[prev_index].op.code;
            /* RESUME and INSTRUMENTED_RESUME are needed for the operation of
             * instrumentation, so must never be hidden by an INSTRUMENTED_LINE.
             */
            if (prev_opcode != RESUME && prev_opcode != INSTRUMENTED_RESUME) {
                goto done;
            }
        }
    }

    uint8_t tools = code->_co_monitoring->line_tools != NULL ?
        code->_co_monitoring->line_tools[i] :
        (interp->monitors.tools[PY_MONITORING_EVENT_LINE] |
         code->_co_monitoring->local_monitors.tools[PY_MONITORING_EVENT_LINE]
        );
    /* Special case sys.settrace to avoid boxing the line number,
     * only to immediately unbox it. */
    if (tools & (1 << PY_MONITORING_SYS_TRACE_ID)) {
        if (tstate->c_tracefunc != NULL) {
            PyFrameObject *frame_obj = _PyFrame_GetFrameObject(frame);
            if (frame_obj == NULL) {
                return -1;
            }
            if (frame_obj->f_trace_lines) {
                /* Need to set tracing and what_event as if using
                 * the instrumentation call. */
                int old_what = tstate->what_event;
                tstate->what_event = PY_MONITORING_EVENT_LINE;
                tstate->tracing++;
                /* Call c_tracefunc directly, having set the line number. */
                Py_INCREF(frame_obj);
                if (line == -1 && line_delta > COMPUTED_LINE) {
                    /* Only assign f_lineno if it's easy to calculate, otherwise
                     * do lazy calculation by setting the f_lineno to 0.
                     */
                    line = compute_line(code, i, line_delta);
                }
                frame_obj->f_lineno = line;
                int err = tstate->c_tracefunc(tstate->c_traceobj, frame_obj, PyTrace_LINE, Py_None);
                frame_obj->f_lineno = 0;
                tstate->tracing--;
                tstate->what_event = old_what;
                Py_DECREF(frame_obj);
                if (err) {
                    return -1;
                }
            }
        }
        tools &= (255 - (1 << PY_MONITORING_SYS_TRACE_ID));
    }
    if (tools == 0) {
        goto done;
    }

    if (line == -1) {
        /* Need to calculate the line number now for monitoring events */
        line = compute_line(code, i, line_delta);
    }
    PyObject *line_obj = PyLong_FromLong(line);
    if (line_obj == NULL) {
        return -1;
    }
    PyObject *args[3] = { NULL, (PyObject *)code, line_obj };
    do {
        int tool = most_significant_bit(tools);
        assert(tool >= 0 && tool < PY_MONITORING_SYS_PROFILE_ID);
        assert(tools & (1 << tool));
        tools &= ~(1 << tool);
        int res = call_one_instrument(interp, tstate, &args[1],
                                      2 | PY_VECTORCALL_ARGUMENTS_OFFSET,
                                      tool, PY_MONITORING_EVENT_LINE);
        if (res == 0) {
            /* Nothing to do */
        }
        else if (res < 0) {
            /* error */
            Py_DECREF(line_obj);
            return -1;
        }
        else {
            /* DISABLE  */
            LOCK_CODE(code);
            remove_line_tools(code, i, 1 << tool);
            UNLOCK_CODE();
        }
    } while (tools);
    Py_DECREF(line_obj);
    uint8_t original_opcode;
done:
    original_opcode = line_data->original_opcode;
    assert(original_opcode != 0);
    assert(original_opcode != INSTRUMENTED_LINE);
    assert(_PyOpcode_Deopt[original_opcode] == original_opcode);
    return original_opcode;
}

int
_Py_call_instrumentation_instruction(PyThreadState *tstate, _PyInterpreterFrame* frame, _Py_CODEUNIT *instr)
{
    PyCodeObject *code = _PyFrame_GetCode(frame);
    int offset = (int)(instr - _PyCode_CODE(code));
    _PyCoMonitoringData *instrumentation_data = code->_co_monitoring;
    assert(instrumentation_data->per_instruction_opcodes);
    int next_opcode = instrumentation_data->per_instruction_opcodes[offset];
    if (tstate->tracing) {
        return next_opcode;
    }
    assert(debug_check_sanity(tstate->interp, code));
    PyInterpreterState *interp = tstate->interp;
    uint8_t tools = instrumentation_data->per_instruction_tools != NULL ?
        instrumentation_data->per_instruction_tools[offset] :
        (interp->monitors.tools[PY_MONITORING_EVENT_INSTRUCTION] |
         code->_co_monitoring->local_monitors.tools[PY_MONITORING_EVENT_INSTRUCTION]
        );
    int bytes_offset = offset * (int)sizeof(_Py_CODEUNIT);
    PyObject *offset_obj = PyLong_FromLong(bytes_offset);
    if (offset_obj == NULL) {
        return -1;
    }
    PyObject *args[3] = { NULL, (PyObject *)code, offset_obj };
    while (tools) {
        int tool = most_significant_bit(tools);
        assert(tool >= 0 && tool < 8);
        assert(tools & (1 << tool));
        tools &= ~(1 << tool);
        int res = call_one_instrument(interp, tstate, &args[1],
                                      2 | PY_VECTORCALL_ARGUMENTS_OFFSET,
                                      tool, PY_MONITORING_EVENT_INSTRUCTION);
        if (res == 0) {
            /* Nothing to do */
        }
        else if (res < 0) {
            /* error */
            Py_DECREF(offset_obj);
            return -1;
        }
        else {
            /* DISABLE  */
            LOCK_CODE(code);
            remove_per_instruction_tools(code, offset, 1 << tool);
            UNLOCK_CODE();
        }
    }
    Py_DECREF(offset_obj);
    assert(next_opcode != 0);
    return next_opcode;
}


PyObject *
_PyMonitoring_RegisterCallback(int tool_id, int event_id, PyObject *obj)
{
    PyInterpreterState *is = _PyInterpreterState_GET();
    assert(0 <= tool_id && tool_id < PY_MONITORING_TOOL_IDS);
    assert(0 <= event_id && event_id < _PY_MONITORING_EVENTS);
    PyObject *callback = _Py_atomic_exchange_ptr(&is->monitoring_callables[tool_id][event_id],
                                                 Py_XNewRef(obj));

    return callback;
}

static void
initialize_tools(PyCodeObject *code)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);
    uint8_t* tools = code->_co_monitoring->tools;

    assert(tools != NULL);
    int code_len = (int)Py_SIZE(code);
    for (int i = 0; i < code_len; i++) {
        _Py_CODEUNIT *instr = &_PyCode_CODE(code)[i];
        int opcode = instr->op.code;
        assert(opcode != ENTER_EXECUTOR);
        if (opcode == INSTRUMENTED_LINE) {
            opcode = code->_co_monitoring->lines[i].original_opcode;
        }
        if (opcode == INSTRUMENTED_INSTRUCTION) {
            opcode = code->_co_monitoring->per_instruction_opcodes[i];
        }
        bool instrumented = is_instrumented(opcode);
        if (instrumented) {
            opcode = DE_INSTRUMENT[opcode];
            assert(opcode != 0);
        }
        opcode = _PyOpcode_Deopt[opcode];
        if (opcode_has_event(opcode)) {
            if (instrumented) {
                int8_t event;
                if (opcode == RESUME) {
                    event = instr->op.arg != 0;
                }
                else {
                    event = EVENT_FOR_OPCODE[opcode];
                    assert(event > 0);
                }
                assert(event >= 0);
                assert(PY_MONITORING_IS_INSTRUMENTED_EVENT(event));
                tools[i] = code->_co_monitoring->active_monitors.tools[event];
                CHECK(tools[i] != 0);
            }
            else {
                tools[i] = 0;
            }
        }
#ifdef Py_DEBUG
        /* Initialize tools for invalid locations to all ones to try to catch errors */
        else {
            tools[i] = 0xff;
        }
        for (int j = 1; j <= _PyOpcode_Caches[opcode]; j++) {
            tools[i+j] = 0xff;
        }
#endif
        i += _PyOpcode_Caches[opcode];
    }
}

#define NO_LINE -128

static void
initialize_lines(PyCodeObject *code)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);
    _PyCoLineInstrumentationData *line_data = code->_co_monitoring->lines;

    assert(line_data != NULL);
    int code_len = (int)Py_SIZE(code);
    PyCodeAddressRange range;
    _PyCode_InitAddressRange(code, &range);
    for (int i = 0; i < code->_co_firsttraceable && i < code_len; i++) {
        line_data[i].original_opcode = 0;
        line_data[i].line_delta = -127;
    }
    int current_line = -1;
    for (int i = code->_co_firsttraceable; i < code_len; ) {
        int opcode = _Py_GetBaseOpcode(code, i);
        int line = _PyCode_CheckLineNumber(i*(int)sizeof(_Py_CODEUNIT), &range);
        line_data[i].line_delta = compute_line_delta(code, i, line);
        int length = _PyInstruction_GetLength(code, i);
        switch (opcode) {
            case END_ASYNC_FOR:
            case END_FOR:
            case END_SEND:
            case RESUME:
                /* END_FOR cannot start a line, as it is skipped by FOR_ITER
                 * END_SEND cannot start a line, as it is skipped by SEND
                 * RESUME must not be instrumented with INSTRUMENT_LINE */
                line_data[i].original_opcode = 0;
                break;
            default:
                /* Set original_opcode to the opcode iff the instruction
                 * starts a line, and thus should be instrumented.
                 * This saves having to perform this check every time the
                 * we turn instrumentation on or off, and serves as a sanity
                 * check when debugging.
                 */
                if (line != current_line && line >= 0) {
                    line_data[i].original_opcode = opcode;
                    if (line_data[i].line_delta == COMPUTED_LINE) {
                        /* Label this line as a line with a line number change
                         * which could help the monitoring callback to quickly
                         * identify the line number change.
                         */
                        line_data[i].line_delta = COMPUTED_LINE_LINENO_CHANGE;
                    }
                }
                else {
                    line_data[i].original_opcode = 0;
                }
                current_line = line;
        }
        for (int j = 1; j < length; j++) {
            line_data[i+j].original_opcode = 0;
            line_data[i+j].line_delta = NO_LINE;
        }
        i += length;
    }
    for (int i = code->_co_firsttraceable; i < code_len; ) {
        int opcode = _Py_GetBaseOpcode(code, i);
        int oparg = 0;
        while (opcode == EXTENDED_ARG) {
            oparg = (oparg << 8) | _PyCode_CODE(code)[i].op.arg;
            i++;
            opcode = _Py_GetBaseOpcode(code, i);
        }
        oparg = (oparg << 8) | _PyCode_CODE(code)[i].op.arg;
        i += _PyInstruction_GetLength(code, i);
        int target = -1;
        switch (opcode) {
            case POP_JUMP_IF_FALSE:
            case POP_JUMP_IF_TRUE:
            case POP_JUMP_IF_NONE:
            case POP_JUMP_IF_NOT_NONE:
            case JUMP_FORWARD:
            {
                target = i + oparg;
                break;
            }
            case FOR_ITER:
            case SEND:
            {
                /* Skip over END_FOR/END_SEND */
                target = i + oparg + 1;
                break;
            }
            case JUMP_BACKWARD:
            case JUMP_BACKWARD_NO_INTERRUPT:
            {
                target = i - oparg;
                break;
            }
            default:
                continue;
        }
        assert(target >= 0);
        if (line_data[target].line_delta != NO_LINE) {
            line_data[target].original_opcode = _Py_GetBaseOpcode(code, target);
            if (line_data[target].line_delta == COMPUTED_LINE_LINENO_CHANGE) {
                // If the line is a jump target, we are not sure if the line
                // number changes, so we set it to COMPUTED_LINE.
                line_data[target].line_delta = COMPUTED_LINE;
            }
        }
    }
    /* Scan exception table */
    unsigned char *start = (unsigned char *)PyBytes_AS_STRING(code->co_exceptiontable);
    unsigned char *end = start + PyBytes_GET_SIZE(code->co_exceptiontable);
    unsigned char *scan = start;
    while (scan < end) {
        int start_offset, size, handler;
        scan = parse_varint(scan, &start_offset);
        assert(start_offset >= 0 && start_offset < code_len);
        scan = parse_varint(scan, &size);
        assert(size >= 0 && start_offset+size <= code_len);
        scan = parse_varint(scan, &handler);
        assert(handler >= 0 && handler < code_len);
        int depth_and_lasti;
        scan = parse_varint(scan, &depth_and_lasti);
        int original_opcode = _Py_GetBaseOpcode(code, handler);
        /* Skip if not the start of a line.
         * END_ASYNC_FOR is a bit special as it marks the end of
         * an `async for` loop, which should not generate its own
         * line event. */
        if (line_data[handler].line_delta != NO_LINE &&
            original_opcode != END_ASYNC_FOR) {
            line_data[handler].original_opcode = original_opcode;
        }
    }
}

static void
initialize_line_tools(PyCodeObject *code, _Py_LocalMonitors *all_events)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);
    uint8_t *line_tools = code->_co_monitoring->line_tools;

    assert(line_tools != NULL);
    int code_len = (int)Py_SIZE(code);
    for (int i = 0; i < code_len; i++) {
        line_tools[i] = all_events->tools[PY_MONITORING_EVENT_LINE];
    }
}

static int
allocate_instrumentation_data(PyCodeObject *code)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);

    if (code->_co_monitoring == NULL) {
        code->_co_monitoring = PyMem_Malloc(sizeof(_PyCoMonitoringData));
        if (code->_co_monitoring == NULL) {
            PyErr_NoMemory();
            return -1;
        }
        code->_co_monitoring->local_monitors = (_Py_LocalMonitors){ 0 };
        code->_co_monitoring->active_monitors = (_Py_LocalMonitors){ 0 };
        code->_co_monitoring->tools = NULL;
        code->_co_monitoring->lines = NULL;
        code->_co_monitoring->line_tools = NULL;
        code->_co_monitoring->per_instruction_opcodes = NULL;
        code->_co_monitoring->per_instruction_tools = NULL;
    }
    return 0;
}

static int
update_instrumentation_data(PyCodeObject *code, PyInterpreterState *interp)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);

    int code_len = (int)Py_SIZE(code);
    if (allocate_instrumentation_data(code)) {
        return -1;
    }
    _Py_LocalMonitors all_events = local_union(
        interp->monitors,
        code->_co_monitoring->local_monitors);
    bool multitools = multiple_tools(&all_events);
    if (code->_co_monitoring->tools == NULL && multitools) {
        code->_co_monitoring->tools = PyMem_Malloc(code_len);
        if (code->_co_monitoring->tools == NULL) {
            PyErr_NoMemory();
            return -1;
        }
        initialize_tools(code);
    }
    if (all_events.tools[PY_MONITORING_EVENT_LINE]) {
        if (code->_co_monitoring->lines == NULL) {
            code->_co_monitoring->lines = PyMem_Malloc(code_len * sizeof(_PyCoLineInstrumentationData));
            if (code->_co_monitoring->lines == NULL) {
                PyErr_NoMemory();
                return -1;
            }
            initialize_lines(code);
        }
        if (multitools && code->_co_monitoring->line_tools == NULL) {
            code->_co_monitoring->line_tools = PyMem_Malloc(code_len);
            if (code->_co_monitoring->line_tools == NULL) {
                PyErr_NoMemory();
                return -1;
            }
            initialize_line_tools(code, &all_events);
        }
    }
    if (all_events.tools[PY_MONITORING_EVENT_INSTRUCTION]) {
        if (code->_co_monitoring->per_instruction_opcodes == NULL) {
            code->_co_monitoring->per_instruction_opcodes = PyMem_Malloc(code_len * sizeof(_PyCoLineInstrumentationData));
            if (code->_co_monitoring->per_instruction_opcodes == NULL) {
                PyErr_NoMemory();
                return -1;
            }
            // Initialize all of the instructions so if local events change while another thread is executing
            // we know what the original opcode was.
            for (int i = 0; i < code_len; i++) {
                int opcode = _PyCode_CODE(code)[i].op.code;
                code->_co_monitoring->per_instruction_opcodes[i] = _PyOpcode_Deopt[opcode];
            }
        }
        if (multitools && code->_co_monitoring->per_instruction_tools == NULL) {
            code->_co_monitoring->per_instruction_tools = PyMem_Malloc(code_len);
            if (code->_co_monitoring->per_instruction_tools == NULL) {
                PyErr_NoMemory();
                return -1;
            }
            for (int i = 0; i < code_len; i++) {
                code->_co_monitoring->per_instruction_tools[i] = 0;
            }
        }
    }
    return 0;
}

static int
force_instrument_lock_held(PyCodeObject *code, PyInterpreterState *interp)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);

#ifdef _Py_TIER2
    if (code->co_executors != NULL) {
        _PyCode_Clear_Executors(code);
    }
    _Py_Executors_InvalidateDependency(interp, code, 1);
#endif
    int code_len = (int)Py_SIZE(code);
    /* Exit early to avoid creating instrumentation
     * data for potential statically allocated code
     * objects.
     * See https://github.com/python/cpython/issues/108390 */
    if (code->co_flags & CO_NO_MONITORING_EVENTS) {
        return 0;
    }
    if (update_instrumentation_data(code, interp)) {
        return -1;
    }
    _Py_LocalMonitors active_events = local_union(
        interp->monitors,
        code->_co_monitoring->local_monitors);
    _Py_LocalMonitors new_events;
    _Py_LocalMonitors removed_events;

    bool restarted = interp->last_restart_version > code->_co_instrumentation_version;
    if (restarted) {
        removed_events = code->_co_monitoring->active_monitors;
        new_events = active_events;
    }
    else {
        removed_events = monitors_sub(code->_co_monitoring->active_monitors, active_events);
        new_events = monitors_sub(active_events, code->_co_monitoring->active_monitors);
        assert(monitors_are_empty(monitors_and(new_events, removed_events)));
    }
    code->_co_monitoring->active_monitors = active_events;
    if (monitors_are_empty(new_events) && monitors_are_empty(removed_events)) {
        goto done;
    }
    /* Insert instrumentation */
    for (int i = code->_co_firsttraceable; i < code_len; i+= _PyInstruction_GetLength(code, i)) {
        _Py_CODEUNIT *instr = &_PyCode_CODE(code)[i];
        CHECK(instr->op.code != 0);
        assert(instr->op.code != ENTER_EXECUTOR);
        int base_opcode = _Py_GetBaseOpcode(code, i);
        assert(base_opcode != ENTER_EXECUTOR);
        if (opcode_has_event(base_opcode)) {
            int8_t event;
            if (base_opcode == RESUME) {
                event = instr->op.arg > 0;
            }
            else {
                event = EVENT_FOR_OPCODE[base_opcode];
                assert(event > 0);
            }
            uint8_t removed_tools = removed_events.tools[event];
            if (removed_tools) {
                remove_tools(code, i, event, removed_tools);
            }
            uint8_t new_tools = new_events.tools[event];
            if (new_tools) {
                add_tools(code, i, event, new_tools);
            }
        }
    }

    // GH-103845: We need to remove both the line and instruction instrumentation before
    // adding new ones, otherwise we may remove the newly added instrumentation.
    uint8_t removed_line_tools = removed_events.tools[PY_MONITORING_EVENT_LINE];
    uint8_t removed_per_instruction_tools = removed_events.tools[PY_MONITORING_EVENT_INSTRUCTION];

    if (removed_line_tools) {
        _PyCoLineInstrumentationData *line_data = code->_co_monitoring->lines;
        for (int i = code->_co_firsttraceable; i < code_len;) {
            if (line_data[i].original_opcode) {
                remove_line_tools(code, i, removed_line_tools);
            }
            i += _PyInstruction_GetLength(code, i);
        }
    }
    if (removed_per_instruction_tools) {
        for (int i = code->_co_firsttraceable; i < code_len;) {
            int opcode = _Py_GetBaseOpcode(code, i);
            if (opcode == RESUME || opcode == END_FOR) {
                i += _PyInstruction_GetLength(code, i);
                continue;
            }
            remove_per_instruction_tools(code, i, removed_per_instruction_tools);
            i += _PyInstruction_GetLength(code, i);
        }
    }
#ifdef INSTRUMENT_DEBUG
    sanity_check_instrumentation(code);
#endif

    uint8_t new_line_tools = new_events.tools[PY_MONITORING_EVENT_LINE];
    uint8_t new_per_instruction_tools = new_events.tools[PY_MONITORING_EVENT_INSTRUCTION];

    if (new_line_tools) {
        _PyCoLineInstrumentationData *line_data = code->_co_monitoring->lines;
        for (int i = code->_co_firsttraceable; i < code_len;) {
            if (line_data[i].original_opcode) {
                add_line_tools(code, i, new_line_tools);
            }
            i += _PyInstruction_GetLength(code, i);
        }
    }
    if (new_per_instruction_tools) {
        for (int i = code->_co_firsttraceable; i < code_len;) {
            int opcode = _Py_GetBaseOpcode(code, i);
            if (opcode == RESUME || opcode == END_FOR) {
                i += _PyInstruction_GetLength(code, i);
                continue;
            }
            add_per_instruction_tools(code, i, new_per_instruction_tools);
            i += _PyInstruction_GetLength(code, i);
        }
    }

done:
    FT_ATOMIC_STORE_UINTPTR_RELEASE(code->_co_instrumentation_version,
                                    global_version(interp));

#ifdef INSTRUMENT_DEBUG
    sanity_check_instrumentation(code);
#endif
    return 0;
}

static int
instrument_lock_held(PyCodeObject *code, PyInterpreterState *interp)
{
    ASSERT_WORLD_STOPPED_OR_LOCKED(code);

    if (is_version_up_to_date(code, interp)) {
        assert(
            interp->ceval.instrumentation_version == 0 ||
            instrumentation_cross_checks(interp, code)
        );
        return 0;
    }

    return force_instrument_lock_held(code, interp);
}

int
_Py_Instrument(PyCodeObject *code, PyInterpreterState *interp)
{
    int res;
    LOCK_CODE(code);
    res = instrument_lock_held(code, interp);
    UNLOCK_CODE();
    return res;
}
"""

_CODE_OBJECT_SOURCE = r"""
#ifndef Py_BUILD_CORE
#define Py_BUILD_CORE
#endif
#include "internal/pycore_code.h"
#ifdef Py_BUILD_CORE
#undef Py_BUILD_CORE
#endif

void
_PyLineTable_InitAddressRange(const char *linetable, Py_ssize_t length, int firstlineno, PyCodeAddressRange *range)
{
    range->opaque.lo_next = (const uint8_t *)linetable;
    range->opaque.limit = range->opaque.lo_next + length;
    range->ar_start = -1;
    range->ar_end = 0;
    range->opaque.computed_line = firstlineno;
    range->ar_line = -1;
}

int
_PyCode_InitAddressRange(PyCodeObject* co, PyCodeAddressRange *bounds)
{
    assert(co->co_linetable != NULL);
    const char *linetable = PyBytes_AS_STRING(co->co_linetable);
    Py_ssize_t length = PyBytes_GET_SIZE(co->co_linetable);
    _PyLineTable_InitAddressRange(linetable, length, co->co_firstlineno, bounds);
    return bounds->ar_line;
}
"""

_FRAME_SOURCE = r"""
#ifndef Py_BUILD_CORE
#define Py_BUILD_CORE
#endif
#include "internal/pycore_frame.h"
#ifdef Py_BUILD_CORE
#undef Py_BUILD_CORE
#endif

PyFrameObject *
_PyFrame_MakeAndSetFrameObject(_PyInterpreterFrame *frame)
{
    assert(frame->frame_obj == NULL);
    PyObject *exc = PyErr_GetRaisedException();

    PyFrameObject *f = _PyFrame_New_NoTrack(_PyFrame_GetCode(frame));
    if (f == NULL) {
        Py_XDECREF(exc);
        return NULL;
    }
    PyErr_SetRaisedException(exc);

    // GH-97002: There was a time when a frame object could be created when we
    // are allocating the new frame object f above, so frame->frame_obj would
    // be assigned already. That path does not exist anymore. We won't call any
    // Python code in this function and garbage collection will not run.
    // Notice that _PyFrame_New_NoTrack() can potentially raise a MemoryError,
    // but it won't allocate a traceback until the frame unwinds, so we are safe
    // here.
    assert(frame->frame_obj == NULL);
    assert(frame->owner != FRAME_OWNED_BY_FRAME_OBJECT);
    assert(frame->owner != FRAME_CLEARED);
    f->f_frame = frame;
    frame->frame_obj = f;
    return f;
}
"""

_FRAME_OBJECT_SOURCE = r"""
#ifndef Py_BUILD_CORE
#define Py_BUILD_CORE
#endif
#include "internal/pycore_frame.h"
#include "internal/pycore_code.h"
#ifdef Py_BUILD_CORE
#undef Py_BUILD_CORE
#endif

PyFrameObject*
_PyFrame_New_NoTrack(PyCodeObject *code)
{
    CALL_STAT_INC(frame_objects_created);
    int slots = code->co_nlocalsplus + code->co_stacksize;
    PyFrameObject *f = PyObject_GC_NewVar(PyFrameObject, &PyFrame_Type, slots);
    if (f == NULL) {
        return NULL;
    }
    f->f_back = NULL;
    f->f_trace = NULL;
    f->f_trace_lines = 1;
    f->f_trace_opcodes = 0;
    f->f_lineno = 0;
    f->f_extra_locals = NULL;
    f->f_locals_cache = NULL;
    return f;
}
"""

_ERRORS_SOURCE = r"""
#ifndef Py_BUILD_CORE
#define Py_BUILD_CORE
#endif
#include "internal/pycore_pyerrors.h"
#ifdef Py_BUILD_CORE
#undef Py_BUILD_CORE
#endif

void
_PyErr_SetRaisedException(PyThreadState *tstate, PyObject *exc)
{
    PyObject *old_exc = tstate->current_exception;
    tstate->current_exception = exc;
    Py_XDECREF(old_exc);
}

PyObject *
_PyErr_GetRaisedException(PyThreadState *tstate) {
    PyObject *exc = tstate->current_exception;
    tstate->current_exception = NULL;
    return exc;
}
"""

_OPCODE_METADATA_SOURCE = r"""
const uint8_t _PyOpcode_Caches[256] = {
    [JUMP_BACKWARD] = 1,
    [TO_BOOL] = 3,
    [BINARY_SUBSCR] = 1,
    [STORE_SUBSCR] = 1,
    [SEND] = 1,
    [UNPACK_SEQUENCE] = 1,
    [STORE_ATTR] = 4,
    [LOAD_GLOBAL] = 4,
    [LOAD_SUPER_ATTR] = 1,
    [LOAD_ATTR] = 9,
    [COMPARE_OP] = 1,
    [CONTAINS_OP] = 1,
    [POP_JUMP_IF_TRUE] = 1,
    [POP_JUMP_IF_FALSE] = 1,
    [POP_JUMP_IF_NONE] = 1,
    [POP_JUMP_IF_NOT_NONE] = 1,
    [FOR_ITER] = 1,
    [CALL] = 3,
    [BINARY_OP] = 1,
};

const uint8_t _PyOpcode_Deopt[256] = {
    [BEFORE_ASYNC_WITH] = BEFORE_ASYNC_WITH,
    [BEFORE_WITH] = BEFORE_WITH,
    [BINARY_OP] = BINARY_OP,
    [BINARY_OP_ADD_FLOAT] = BINARY_OP,
    [BINARY_OP_ADD_INT] = BINARY_OP,
    [BINARY_OP_ADD_UNICODE] = BINARY_OP,
    [BINARY_OP_INPLACE_ADD_UNICODE] = BINARY_OP,
    [BINARY_OP_MULTIPLY_FLOAT] = BINARY_OP,
    [BINARY_OP_MULTIPLY_INT] = BINARY_OP,
    [BINARY_OP_SUBTRACT_FLOAT] = BINARY_OP,
    [BINARY_OP_SUBTRACT_INT] = BINARY_OP,
    [BINARY_SLICE] = BINARY_SLICE,
    [BINARY_SUBSCR] = BINARY_SUBSCR,
    [BINARY_SUBSCR_DICT] = BINARY_SUBSCR,
    [BINARY_SUBSCR_GETITEM] = BINARY_SUBSCR,
    [BINARY_SUBSCR_LIST_INT] = BINARY_SUBSCR,
    [BINARY_SUBSCR_STR_INT] = BINARY_SUBSCR,
    [BINARY_SUBSCR_TUPLE_INT] = BINARY_SUBSCR,
    [BUILD_CONST_KEY_MAP] = BUILD_CONST_KEY_MAP,
    [BUILD_LIST] = BUILD_LIST,
    [BUILD_MAP] = BUILD_MAP,
    [BUILD_SET] = BUILD_SET,
    [BUILD_SLICE] = BUILD_SLICE,
    [BUILD_STRING] = BUILD_STRING,
    [BUILD_TUPLE] = BUILD_TUPLE,
    [CACHE] = CACHE,
    [CALL] = CALL,
    [CALL_ALLOC_AND_ENTER_INIT] = CALL,
    [CALL_BOUND_METHOD_EXACT_ARGS] = CALL,
    [CALL_BOUND_METHOD_GENERAL] = CALL,
    [CALL_BUILTIN_CLASS] = CALL,
    [CALL_BUILTIN_FAST] = CALL,
    [CALL_BUILTIN_FAST_WITH_KEYWORDS] = CALL,
    [CALL_BUILTIN_O] = CALL,
    [CALL_FUNCTION_EX] = CALL_FUNCTION_EX,
    [CALL_INTRINSIC_1] = CALL_INTRINSIC_1,
    [CALL_INTRINSIC_2] = CALL_INTRINSIC_2,
    [CALL_ISINSTANCE] = CALL,
    [CALL_KW] = CALL_KW,
    [CALL_LEN] = CALL,
    [CALL_LIST_APPEND] = CALL,
    [CALL_METHOD_DESCRIPTOR_FAST] = CALL,
    [CALL_METHOD_DESCRIPTOR_FAST_WITH_KEYWORDS] = CALL,
    [CALL_METHOD_DESCRIPTOR_NOARGS] = CALL,
    [CALL_METHOD_DESCRIPTOR_O] = CALL,
    [CALL_NON_PY_GENERAL] = CALL,
    [CALL_PY_EXACT_ARGS] = CALL,
    [CALL_PY_GENERAL] = CALL,
    [CALL_STR_1] = CALL,
    [CALL_TUPLE_1] = CALL,
    [CALL_TYPE_1] = CALL,
    [CHECK_EG_MATCH] = CHECK_EG_MATCH,
    [CHECK_EXC_MATCH] = CHECK_EXC_MATCH,
    [CLEANUP_THROW] = CLEANUP_THROW,
    [COMPARE_OP] = COMPARE_OP,
    [COMPARE_OP_FLOAT] = COMPARE_OP,
    [COMPARE_OP_INT] = COMPARE_OP,
    [COMPARE_OP_STR] = COMPARE_OP,
    [CONTAINS_OP] = CONTAINS_OP,
    [CONTAINS_OP_DICT] = CONTAINS_OP,
    [CONTAINS_OP_SET] = CONTAINS_OP,
    [CONVERT_VALUE] = CONVERT_VALUE,
    [COPY] = COPY,
    [COPY_FREE_VARS] = COPY_FREE_VARS,
    [DELETE_ATTR] = DELETE_ATTR,
    [DELETE_DEREF] = DELETE_DEREF,
    [DELETE_FAST] = DELETE_FAST,
    [DELETE_GLOBAL] = DELETE_GLOBAL,
    [DELETE_NAME] = DELETE_NAME,
    [DELETE_SUBSCR] = DELETE_SUBSCR,
    [DICT_MERGE] = DICT_MERGE,
    [DICT_UPDATE] = DICT_UPDATE,
    [END_ASYNC_FOR] = END_ASYNC_FOR,
    [END_FOR] = END_FOR,
    [END_SEND] = END_SEND,
    [ENTER_EXECUTOR] = ENTER_EXECUTOR,
    [EXIT_INIT_CHECK] = EXIT_INIT_CHECK,
    [EXTENDED_ARG] = EXTENDED_ARG,
    [FORMAT_SIMPLE] = FORMAT_SIMPLE,
    [FORMAT_WITH_SPEC] = FORMAT_WITH_SPEC,
    [FOR_ITER] = FOR_ITER,
    [FOR_ITER_GEN] = FOR_ITER,
    [FOR_ITER_LIST] = FOR_ITER,
    [FOR_ITER_RANGE] = FOR_ITER,
    [FOR_ITER_TUPLE] = FOR_ITER,
    [GET_AITER] = GET_AITER,
    [GET_ANEXT] = GET_ANEXT,
    [GET_AWAITABLE] = GET_AWAITABLE,
    [GET_ITER] = GET_ITER,
    [GET_LEN] = GET_LEN,
    [GET_YIELD_FROM_ITER] = GET_YIELD_FROM_ITER,
    [IMPORT_FROM] = IMPORT_FROM,
    [IMPORT_NAME] = IMPORT_NAME,
    [INSTRUMENTED_CALL] = INSTRUMENTED_CALL,
    [INSTRUMENTED_CALL_FUNCTION_EX] = INSTRUMENTED_CALL_FUNCTION_EX,
    [INSTRUMENTED_CALL_KW] = INSTRUMENTED_CALL_KW,
    [INSTRUMENTED_END_FOR] = INSTRUMENTED_END_FOR,
    [INSTRUMENTED_END_SEND] = INSTRUMENTED_END_SEND,
    [INSTRUMENTED_FOR_ITER] = INSTRUMENTED_FOR_ITER,
    [INSTRUMENTED_INSTRUCTION] = INSTRUMENTED_INSTRUCTION,
    [INSTRUMENTED_JUMP_BACKWARD] = INSTRUMENTED_JUMP_BACKWARD,
    [INSTRUMENTED_JUMP_FORWARD] = INSTRUMENTED_JUMP_FORWARD,
    [INSTRUMENTED_LINE] = INSTRUMENTED_LINE,
    [INSTRUMENTED_LOAD_SUPER_ATTR] = INSTRUMENTED_LOAD_SUPER_ATTR,
    [INSTRUMENTED_POP_JUMP_IF_FALSE] = INSTRUMENTED_POP_JUMP_IF_FALSE,
    [INSTRUMENTED_POP_JUMP_IF_NONE] = INSTRUMENTED_POP_JUMP_IF_NONE,
    [INSTRUMENTED_POP_JUMP_IF_NOT_NONE] = INSTRUMENTED_POP_JUMP_IF_NOT_NONE,
    [INSTRUMENTED_POP_JUMP_IF_TRUE] = INSTRUMENTED_POP_JUMP_IF_TRUE,
    [INSTRUMENTED_RESUME] = INSTRUMENTED_RESUME,
    [INSTRUMENTED_RETURN_CONST] = INSTRUMENTED_RETURN_CONST,
    [INSTRUMENTED_RETURN_VALUE] = INSTRUMENTED_RETURN_VALUE,
    [INSTRUMENTED_YIELD_VALUE] = INSTRUMENTED_YIELD_VALUE,
    [INTERPRETER_EXIT] = INTERPRETER_EXIT,
    [IS_OP] = IS_OP,
    [JUMP_BACKWARD] = JUMP_BACKWARD,
    [JUMP_BACKWARD_NO_INTERRUPT] = JUMP_BACKWARD_NO_INTERRUPT,
    [JUMP_FORWARD] = JUMP_FORWARD,
    [LIST_APPEND] = LIST_APPEND,
    [LIST_EXTEND] = LIST_EXTEND,
    [LOAD_ASSERTION_ERROR] = LOAD_ASSERTION_ERROR,
    [LOAD_ATTR] = LOAD_ATTR,
    [LOAD_ATTR_CLASS] = LOAD_ATTR,
    [LOAD_ATTR_GETATTRIBUTE_OVERRIDDEN] = LOAD_ATTR,
    [LOAD_ATTR_INSTANCE_VALUE] = LOAD_ATTR,
    [LOAD_ATTR_METHOD_LAZY_DICT] = LOAD_ATTR,
    [LOAD_ATTR_METHOD_NO_DICT] = LOAD_ATTR,
    [LOAD_ATTR_METHOD_WITH_VALUES] = LOAD_ATTR,
    [LOAD_ATTR_MODULE] = LOAD_ATTR,
    [LOAD_ATTR_NONDESCRIPTOR_NO_DICT] = LOAD_ATTR,
    [LOAD_ATTR_NONDESCRIPTOR_WITH_VALUES] = LOAD_ATTR,
    [LOAD_ATTR_PROPERTY] = LOAD_ATTR,
    [LOAD_ATTR_SLOT] = LOAD_ATTR,
    [LOAD_ATTR_WITH_HINT] = LOAD_ATTR,
    [LOAD_BUILD_CLASS] = LOAD_BUILD_CLASS,
    [LOAD_CONST] = LOAD_CONST,
    [LOAD_DEREF] = LOAD_DEREF,
    [LOAD_FAST] = LOAD_FAST,
    [LOAD_FAST_AND_CLEAR] = LOAD_FAST_AND_CLEAR,
    [LOAD_FAST_CHECK] = LOAD_FAST_CHECK,
    [LOAD_FAST_LOAD_FAST] = LOAD_FAST_LOAD_FAST,
    [LOAD_FROM_DICT_OR_DEREF] = LOAD_FROM_DICT_OR_DEREF,
    [LOAD_FROM_DICT_OR_GLOBALS] = LOAD_FROM_DICT_OR_GLOBALS,
    [LOAD_GLOBAL] = LOAD_GLOBAL,
    [LOAD_GLOBAL_BUILTIN] = LOAD_GLOBAL,
    [LOAD_GLOBAL_MODULE] = LOAD_GLOBAL,
    [LOAD_LOCALS] = LOAD_LOCALS,
    [LOAD_NAME] = LOAD_NAME,
    [LOAD_SUPER_ATTR] = LOAD_SUPER_ATTR,
    [LOAD_SUPER_ATTR_ATTR] = LOAD_SUPER_ATTR,
    [LOAD_SUPER_ATTR_METHOD] = LOAD_SUPER_ATTR,
    [MAKE_CELL] = MAKE_CELL,
    [MAKE_FUNCTION] = MAKE_FUNCTION,
    [MAP_ADD] = MAP_ADD,
    [MATCH_CLASS] = MATCH_CLASS,
    [MATCH_KEYS] = MATCH_KEYS,
    [MATCH_MAPPING] = MATCH_MAPPING,
    [MATCH_SEQUENCE] = MATCH_SEQUENCE,
    [NOP] = NOP,
    [POP_EXCEPT] = POP_EXCEPT,
    [POP_JUMP_IF_FALSE] = POP_JUMP_IF_FALSE,
    [POP_JUMP_IF_NONE] = POP_JUMP_IF_NONE,
    [POP_JUMP_IF_NOT_NONE] = POP_JUMP_IF_NOT_NONE,
    [POP_JUMP_IF_TRUE] = POP_JUMP_IF_TRUE,
    [POP_TOP] = POP_TOP,
    [PUSH_EXC_INFO] = PUSH_EXC_INFO,
    [PUSH_NULL] = PUSH_NULL,
    [RAISE_VARARGS] = RAISE_VARARGS,
    [RERAISE] = RERAISE,
    [RESERVED] = RESERVED,
    [RESUME] = RESUME,
    [RESUME_CHECK] = RESUME,
    [RETURN_CONST] = RETURN_CONST,
    [RETURN_GENERATOR] = RETURN_GENERATOR,
    [RETURN_VALUE] = RETURN_VALUE,
    [SEND] = SEND,
    [SEND_GEN] = SEND,
    [SETUP_ANNOTATIONS] = SETUP_ANNOTATIONS,
    [SET_ADD] = SET_ADD,
    [SET_FUNCTION_ATTRIBUTE] = SET_FUNCTION_ATTRIBUTE,
    [SET_UPDATE] = SET_UPDATE,
    [STORE_ATTR] = STORE_ATTR,
    [STORE_ATTR_INSTANCE_VALUE] = STORE_ATTR,
    [STORE_ATTR_SLOT] = STORE_ATTR,
    [STORE_ATTR_WITH_HINT] = STORE_ATTR,
    [STORE_DEREF] = STORE_DEREF,
    [STORE_FAST] = STORE_FAST,
    [STORE_FAST_LOAD_FAST] = STORE_FAST_LOAD_FAST,
    [STORE_FAST_STORE_FAST] = STORE_FAST_STORE_FAST,
    [STORE_GLOBAL] = STORE_GLOBAL,
    [STORE_NAME] = STORE_NAME,
    [STORE_SLICE] = STORE_SLICE,
    [STORE_SUBSCR] = STORE_SUBSCR,
    [STORE_SUBSCR_DICT] = STORE_SUBSCR,
    [STORE_SUBSCR_LIST_INT] = STORE_SUBSCR,
    [SWAP] = SWAP,
    [TO_BOOL] = TO_BOOL,
    [TO_BOOL_ALWAYS_TRUE] = TO_BOOL,
    [TO_BOOL_BOOL] = TO_BOOL,
    [TO_BOOL_INT] = TO_BOOL,
    [TO_BOOL_LIST] = TO_BOOL,
    [TO_BOOL_NONE] = TO_BOOL,
    [TO_BOOL_STR] = TO_BOOL,
    [UNARY_INVERT] = UNARY_INVERT,
    [UNARY_NEGATIVE] = UNARY_NEGATIVE,
    [UNARY_NOT] = UNARY_NOT,
    [UNPACK_EX] = UNPACK_EX,
    [UNPACK_SEQUENCE] = UNPACK_SEQUENCE,
    [UNPACK_SEQUENCE_LIST] = UNPACK_SEQUENCE,
    [UNPACK_SEQUENCE_TUPLE] = UNPACK_SEQUENCE,
    [UNPACK_SEQUENCE_TWO_TUPLE] = UNPACK_SEQUENCE,
    [WITH_EXCEPT_START] = WITH_EXCEPT_START,
    [YIELD_VALUE] = YIELD_VALUE,
};
"""


_SPECIALIZE_SOURCE = r"""
#include "opcode.h"

#ifndef SPECIALIZATION_FAIL
#  define SPECIALIZATION_FAIL(opcode, kind) ((void)0)
#endif

#define SIMPLE_FUNCTION 0

/* Common */

#define SPEC_FAIL_OTHER 0
#define SPEC_FAIL_NO_DICT 1
#define SPEC_FAIL_OVERRIDDEN 2
#define SPEC_FAIL_OUT_OF_VERSIONS 3
#define SPEC_FAIL_OUT_OF_RANGE 4
#define SPEC_FAIL_EXPECTED_ERROR 5
#define SPEC_FAIL_WRONG_NUMBER_ARGUMENTS 6
#define SPEC_FAIL_CODE_COMPLEX_PARAMETERS 7
#define SPEC_FAIL_CODE_NOT_OPTIMIZED 8


#define SPEC_FAIL_LOAD_GLOBAL_NON_DICT 17
#define SPEC_FAIL_LOAD_GLOBAL_NON_STRING_OR_SPLIT 18

/* Super */

#define SPEC_FAIL_SUPER_BAD_CLASS 9
#define SPEC_FAIL_SUPER_SHADOWED 10

/* Attributes */

#define SPEC_FAIL_ATTR_OVERRIDING_DESCRIPTOR 9
#define SPEC_FAIL_ATTR_NON_OVERRIDING_DESCRIPTOR 10
#define SPEC_FAIL_ATTR_NOT_DESCRIPTOR 11
#define SPEC_FAIL_ATTR_METHOD 12
#define SPEC_FAIL_ATTR_MUTABLE_CLASS 13
#define SPEC_FAIL_ATTR_PROPERTY 14
#define SPEC_FAIL_ATTR_NON_OBJECT_SLOT 15
#define SPEC_FAIL_ATTR_READ_ONLY 16
#define SPEC_FAIL_ATTR_AUDITED_SLOT 17
#define SPEC_FAIL_ATTR_NOT_MANAGED_DICT 18
#define SPEC_FAIL_ATTR_NON_STRING_OR_SPLIT 19
#define SPEC_FAIL_ATTR_MODULE_ATTR_NOT_FOUND 20
#define SPEC_FAIL_ATTR_SHADOWED 21
#define SPEC_FAIL_ATTR_BUILTIN_CLASS_METHOD 22
#define SPEC_FAIL_ATTR_CLASS_METHOD_OBJ 23
#define SPEC_FAIL_ATTR_OBJECT_SLOT 24

#define SPEC_FAIL_ATTR_INSTANCE_ATTRIBUTE 26
#define SPEC_FAIL_ATTR_METACLASS_ATTRIBUTE 27
#define SPEC_FAIL_ATTR_PROPERTY_NOT_PY_FUNCTION 28
#define SPEC_FAIL_ATTR_NOT_IN_KEYS 29
#define SPEC_FAIL_ATTR_NOT_IN_DICT 30
#define SPEC_FAIL_ATTR_CLASS_ATTR_SIMPLE 31
#define SPEC_FAIL_ATTR_CLASS_ATTR_DESCRIPTOR 32
#define SPEC_FAIL_ATTR_BUILTIN_CLASS_METHOD_OBJ 33

/* Binary subscr and store subscr */

#define SPEC_FAIL_SUBSCR_ARRAY_INT 9
#define SPEC_FAIL_SUBSCR_ARRAY_SLICE 10
#define SPEC_FAIL_SUBSCR_LIST_SLICE 11
#define SPEC_FAIL_SUBSCR_TUPLE_SLICE 12
#define SPEC_FAIL_SUBSCR_STRING_SLICE 14
#define SPEC_FAIL_SUBSCR_BUFFER_INT 15
#define SPEC_FAIL_SUBSCR_BUFFER_SLICE 16
#define SPEC_FAIL_SUBSCR_SEQUENCE_INT 17

/* Store subscr */
#define SPEC_FAIL_SUBSCR_BYTEARRAY_INT 18
#define SPEC_FAIL_SUBSCR_BYTEARRAY_SLICE 19
#define SPEC_FAIL_SUBSCR_PY_SIMPLE 20
#define SPEC_FAIL_SUBSCR_PY_OTHER 21
#define SPEC_FAIL_SUBSCR_DICT_SUBCLASS_NO_OVERRIDE 22
#define SPEC_FAIL_SUBSCR_NOT_HEAP_TYPE 23

/* Binary op */

#define SPEC_FAIL_BINARY_OP_ADD_DIFFERENT_TYPES          9
#define SPEC_FAIL_BINARY_OP_ADD_OTHER                   10
#define SPEC_FAIL_BINARY_OP_AND_DIFFERENT_TYPES         11
#define SPEC_FAIL_BINARY_OP_AND_INT                     12
#define SPEC_FAIL_BINARY_OP_AND_OTHER                   13
#define SPEC_FAIL_BINARY_OP_FLOOR_DIVIDE                14
#define SPEC_FAIL_BINARY_OP_LSHIFT                      15
#define SPEC_FAIL_BINARY_OP_MATRIX_MULTIPLY             16
#define SPEC_FAIL_BINARY_OP_MULTIPLY_DIFFERENT_TYPES    17
#define SPEC_FAIL_BINARY_OP_MULTIPLY_OTHER              18
#define SPEC_FAIL_BINARY_OP_OR                          19
#define SPEC_FAIL_BINARY_OP_POWER                       20
#define SPEC_FAIL_BINARY_OP_REMAINDER                   21
#define SPEC_FAIL_BINARY_OP_RSHIFT                      22
#define SPEC_FAIL_BINARY_OP_SUBTRACT_DIFFERENT_TYPES    23
#define SPEC_FAIL_BINARY_OP_SUBTRACT_OTHER              24
#define SPEC_FAIL_BINARY_OP_TRUE_DIVIDE_DIFFERENT_TYPES 25
#define SPEC_FAIL_BINARY_OP_TRUE_DIVIDE_FLOAT           26
#define SPEC_FAIL_BINARY_OP_TRUE_DIVIDE_OTHER           27
#define SPEC_FAIL_BINARY_OP_XOR                         28

/* Calls */

#define SPEC_FAIL_CALL_INSTANCE_METHOD 11
#define SPEC_FAIL_CALL_CMETHOD 12
#define SPEC_FAIL_CALL_CFUNC_VARARGS 13
#define SPEC_FAIL_CALL_CFUNC_VARARGS_KEYWORDS 14
#define SPEC_FAIL_CALL_CFUNC_NOARGS 15
#define SPEC_FAIL_CALL_CFUNC_METHOD_FASTCALL_KEYWORDS 16
#define SPEC_FAIL_CALL_METH_DESCR_VARARGS 17
#define SPEC_FAIL_CALL_METH_DESCR_VARARGS_KEYWORDS 18
#define SPEC_FAIL_CALL_METH_DESCR_METHOD_FASTCALL_KEYWORDS 19
#define SPEC_FAIL_CALL_BAD_CALL_FLAGS 20
#define SPEC_FAIL_CALL_INIT_NOT_PYTHON 21
#define SPEC_FAIL_CALL_PEP_523 22
#define SPEC_FAIL_CALL_BOUND_METHOD 23
#define SPEC_FAIL_CALL_STR 24
#define SPEC_FAIL_CALL_CLASS_NO_VECTORCALL 25
#define SPEC_FAIL_CALL_CLASS_MUTABLE 26
#define SPEC_FAIL_CALL_METHOD_WRAPPER 28
#define SPEC_FAIL_CALL_OPERATOR_WRAPPER 29
#define SPEC_FAIL_CALL_INIT_NOT_SIMPLE 30
#define SPEC_FAIL_CALL_METACLASS 31
#define SPEC_FAIL_CALL_INIT_NOT_INLINE_VALUES 32

/* COMPARE_OP */
#define SPEC_FAIL_COMPARE_OP_DIFFERENT_TYPES 12
#define SPEC_FAIL_COMPARE_OP_STRING 13
#define SPEC_FAIL_COMPARE_OP_BIG_INT 14
#define SPEC_FAIL_COMPARE_OP_BYTES 15
#define SPEC_FAIL_COMPARE_OP_TUPLE 16
#define SPEC_FAIL_COMPARE_OP_LIST 17
#define SPEC_FAIL_COMPARE_OP_SET 18
#define SPEC_FAIL_COMPARE_OP_BOOL 19
#define SPEC_FAIL_COMPARE_OP_BASEOBJECT 20
#define SPEC_FAIL_COMPARE_OP_FLOAT_LONG 21
#define SPEC_FAIL_COMPARE_OP_LONG_FLOAT 22

/* FOR_ITER and SEND */
#define SPEC_FAIL_ITER_GENERATOR 10
#define SPEC_FAIL_ITER_COROUTINE 11
#define SPEC_FAIL_ITER_ASYNC_GENERATOR 12
#define SPEC_FAIL_ITER_LIST 13
#define SPEC_FAIL_ITER_TUPLE 14
#define SPEC_FAIL_ITER_SET 15
#define SPEC_FAIL_ITER_STRING 16
#define SPEC_FAIL_ITER_BYTES 17
#define SPEC_FAIL_ITER_RANGE 18
#define SPEC_FAIL_ITER_ITERTOOLS 19
#define SPEC_FAIL_ITER_DICT_KEYS 20
#define SPEC_FAIL_ITER_DICT_ITEMS 21
#define SPEC_FAIL_ITER_DICT_VALUES 22
#define SPEC_FAIL_ITER_ENUMERATE 23
#define SPEC_FAIL_ITER_MAP 24
#define SPEC_FAIL_ITER_ZIP 25
#define SPEC_FAIL_ITER_SEQ_ITER 26
#define SPEC_FAIL_ITER_REVERSED_LIST 27
#define SPEC_FAIL_ITER_CALLABLE 28
#define SPEC_FAIL_ITER_ASCII_STRING 29
#define SPEC_FAIL_ITER_ASYNC_GENERATOR_SEND 30

// UNPACK_SEQUENCE

#define SPEC_FAIL_UNPACK_SEQUENCE_ITERATOR 9
#define SPEC_FAIL_UNPACK_SEQUENCE_SEQUENCE 10

// TO_BOOL
#define SPEC_FAIL_TO_BOOL_BYTEARRAY    9
#define SPEC_FAIL_TO_BOOL_BYTES       10
#define SPEC_FAIL_TO_BOOL_DICT        11
#define SPEC_FAIL_TO_BOOL_FLOAT       12
#define SPEC_FAIL_TO_BOOL_MAPPING     13
#define SPEC_FAIL_TO_BOOL_MEMORY_VIEW 14
#define SPEC_FAIL_TO_BOOL_NUMBER      15
#define SPEC_FAIL_TO_BOOL_SEQUENCE    16
#define SPEC_FAIL_TO_BOOL_SET         17
#define SPEC_FAIL_TO_BOOL_TUPLE       18

// CONTAINS_OP
#define SPEC_FAIL_CONTAINS_OP_STR        9
#define SPEC_FAIL_CONTAINS_OP_TUPLE      10
#define SPEC_FAIL_CONTAINS_OP_LIST       11
#define SPEC_FAIL_CONTAINS_OP_USER_CLASS 12

static int
function_kind(PyCodeObject *code) {
    int flags = code->co_flags;
    if ((flags & (CO_VARKEYWORDS | CO_VARARGS)) || code->co_kwonlyargcount) {
        return SPEC_FAIL_CODE_COMPLEX_PARAMETERS;
    }
    if ((flags & CO_OPTIMIZED) == 0) {
        return SPEC_FAIL_CODE_NOT_OPTIMIZED;
    }
    return SIMPLE_FUNCTION;
}

void
_Py_Specialize_BinarySubscr(
     PyObject *container, PyObject *sub, _Py_CODEUNIT *instr)
{
    assert(ENABLE_SPECIALIZATION);
    assert(_PyOpcode_Caches[BINARY_SUBSCR] ==
           INLINE_CACHE_ENTRIES_BINARY_SUBSCR);
    _PyBinarySubscrCache *cache = (_PyBinarySubscrCache *)(instr + 1);
    PyTypeObject *container_type = Py_TYPE(container);
    if (container_type == &PyList_Type) {
        if (PyLong_CheckExact(sub)) {
            if (_PyLong_IsNonNegativeCompact((PyLongObject *)sub)) {
                instr->op.code = BINARY_SUBSCR_LIST_INT;
                goto success;
            }
            SPECIALIZATION_FAIL(BINARY_SUBSCR, SPEC_FAIL_OUT_OF_RANGE);
            goto fail;
        }
        SPECIALIZATION_FAIL(BINARY_SUBSCR,
            PySlice_Check(sub) ? SPEC_FAIL_SUBSCR_LIST_SLICE : SPEC_FAIL_OTHER);
        goto fail;
    }
    if (container_type == &PyTuple_Type) {
        if (PyLong_CheckExact(sub)) {
            if (_PyLong_IsNonNegativeCompact((PyLongObject *)sub)) {
                instr->op.code = BINARY_SUBSCR_TUPLE_INT;
                goto success;
            }
            SPECIALIZATION_FAIL(BINARY_SUBSCR, SPEC_FAIL_OUT_OF_RANGE);
            goto fail;
        }
        SPECIALIZATION_FAIL(BINARY_SUBSCR,
            PySlice_Check(sub) ? SPEC_FAIL_SUBSCR_TUPLE_SLICE : SPEC_FAIL_OTHER);
        goto fail;
    }
    if (container_type == &PyUnicode_Type) {
        if (PyLong_CheckExact(sub)) {
            if (_PyLong_IsNonNegativeCompact((PyLongObject *)sub)) {
                instr->op.code = BINARY_SUBSCR_STR_INT;
                goto success;
            }
            SPECIALIZATION_FAIL(BINARY_SUBSCR, SPEC_FAIL_OUT_OF_RANGE);
            goto fail;
        }
        SPECIALIZATION_FAIL(BINARY_SUBSCR,
            PySlice_Check(sub) ? SPEC_FAIL_SUBSCR_STRING_SLICE : SPEC_FAIL_OTHER);
        goto fail;
    }
    if (container_type == &PyDict_Type) {
        instr->op.code = BINARY_SUBSCR_DICT;
        goto success;
    }
    PyTypeObject *cls = Py_TYPE(container);
    PyObject *descriptor = _PyType_Lookup(cls, &_Py_ID(__getitem__));
    if (descriptor && Py_TYPE(descriptor) == &PyFunction_Type) {
        if (!(container_type->tp_flags & Py_TPFLAGS_HEAPTYPE)) {
            SPECIALIZATION_FAIL(BINARY_SUBSCR, SPEC_FAIL_SUBSCR_NOT_HEAP_TYPE);
            goto fail;
        }
        PyFunctionObject *func = (PyFunctionObject *)descriptor;
        PyCodeObject *fcode = (PyCodeObject *)func->func_code;
        int kind = function_kind(fcode);
        if (kind != SIMPLE_FUNCTION) {
            SPECIALIZATION_FAIL(BINARY_SUBSCR, kind);
            goto fail;
        }
        if (fcode->co_argcount != 2) {
            SPECIALIZATION_FAIL(BINARY_SUBSCR, SPEC_FAIL_WRONG_NUMBER_ARGUMENTS);
            goto fail;
        }
        uint32_t version = func->func_version;
        if (version == 0) {
            SPECIALIZATION_FAIL(BINARY_SUBSCR, SPEC_FAIL_OUT_OF_VERSIONS);
            goto fail;
        }
        if (_PyInterpreterState_GET()->eval_frame) {
            SPECIALIZATION_FAIL(BINARY_SUBSCR, SPEC_FAIL_OTHER);
            goto fail;
        }
        PyHeapTypeObject *ht = (PyHeapTypeObject *)container_type;
        // This pointer is invalidated by PyType_Modified (see the comment on
        // struct _specialization_cache):
        ht->_spec_cache.getitem = descriptor;
        ht->_spec_cache.getitem_version = version;
        instr->op.code = BINARY_SUBSCR_GETITEM;
        goto success;
    }
    SPECIALIZATION_FAIL(BINARY_SUBSCR,
                        binary_subscr_fail_kind(container_type, sub));
fail:
    STAT_INC(BINARY_SUBSCR, failure);
    assert(!PyErr_Occurred());
    instr->op.code = BINARY_SUBSCR;
    cache->counter = adaptive_counter_backoff(cache->counter);
    return;
success:
    STAT_INC(BINARY_SUBSCR, success);
    assert(!PyErr_Occurred());
    cache->counter = adaptive_counter_cooldown();
}

void
_Py_Specialize_BinaryOp(PyObject *lhs, PyObject *rhs, _Py_CODEUNIT *instr,
                        int oparg, PyObject **locals)
{
    assert(ENABLE_SPECIALIZATION);
    assert(_PyOpcode_Caches[BINARY_OP] == INLINE_CACHE_ENTRIES_BINARY_OP);
    _PyBinaryOpCache *cache = (_PyBinaryOpCache *)(instr + 1);
    switch (oparg) {
        case NB_ADD:
        case NB_INPLACE_ADD:
            if (!Py_IS_TYPE(lhs, Py_TYPE(rhs))) {
                break;
            }
            if (PyUnicode_CheckExact(lhs)) {
                _Py_CODEUNIT next = instr[INLINE_CACHE_ENTRIES_BINARY_OP + 1];
                bool to_store = (next.op.code == STORE_FAST);
                if (to_store && locals[next.op.arg] == lhs) {
                    instr->op.code = BINARY_OP_INPLACE_ADD_UNICODE;
                    goto success;
                }
                instr->op.code = BINARY_OP_ADD_UNICODE;
                goto success;
            }
            if (PyLong_CheckExact(lhs)) {
                instr->op.code = BINARY_OP_ADD_INT;
                goto success;
            }
            if (PyFloat_CheckExact(lhs)) {
                instr->op.code = BINARY_OP_ADD_FLOAT;
                goto success;
            }
            break;
        case NB_MULTIPLY:
        case NB_INPLACE_MULTIPLY:
            if (!Py_IS_TYPE(lhs, Py_TYPE(rhs))) {
                break;
            }
            if (PyLong_CheckExact(lhs)) {
                instr->op.code = BINARY_OP_MULTIPLY_INT;
                goto success;
            }
            if (PyFloat_CheckExact(lhs)) {
                instr->op.code = BINARY_OP_MULTIPLY_FLOAT;
                goto success;
            }
            break;
        case NB_SUBTRACT:
        case NB_INPLACE_SUBTRACT:
            if (!Py_IS_TYPE(lhs, Py_TYPE(rhs))) {
                break;
            }
            if (PyLong_CheckExact(lhs)) {
                instr->op.code = BINARY_OP_SUBTRACT_INT;
                goto success;
            }
            if (PyFloat_CheckExact(lhs)) {
                instr->op.code = BINARY_OP_SUBTRACT_FLOAT;
                goto success;
            }
            break;
    }
    SPECIALIZATION_FAIL(BINARY_OP, binary_op_fail_kind(oparg, lhs, rhs));
    STAT_INC(BINARY_OP, failure);
    instr->op.code = BINARY_OP;
    cache->counter = adaptive_counter_backoff(cache->counter);
    return;
success:
    STAT_INC(BINARY_OP, success);
    cache->counter = adaptive_counter_cooldown();
}
"""


@not_rpython
def _unique_str(s):
    # type: (str) -> str
    f = inspect.currentframe()
    assert f
    f = f.f_back
    assert f
    if s.endswith("\\"):
        s = s[:-1]
        return "{}{}/* FILE: {} LINE: {} */  \\".format(s, "  " if s else "", __file__, f.f_lineno)
    return "{}{}/* FILE: {} LINE: {} */".format(s, "  " if s else "", __file__, f.f_lineno)


GLOBAL_ECI = ExternalCompilationInfo(
    post_include_bits=[
        _unique_str("static const _Py_CODEUNIT _Py_INTERPRETER_TRAMPOLINE_INSTRUCTIONS[5];"),
        _unique_str("#ifndef Py_BUILD_CORE"),
        _unique_str("#define Py_BUILD_CORE"),
        _unique_str("#endif"),
        _unique_str("#include <opcode_ids.h>"),
        _unique_str("#include <internal/pycore_call.h>"),
        _unique_str("#include <internal/pycore_ceval.h>"),
        _unique_str("#include <internal/pycore_pyerrors.h>"),
        _unique_str("#include <internal/pycore_opcode_metadata.h>"),
        _unique_str("#include <internal/pycore_pyatomic_ft_wrappers.h>"),
        _unique_str("#include <internal/pycore_object.h>"),
        _unique_str("#include <internal/pycore_floatobject.h>"),
        _unique_str("#include <internal/pycore_long.h>"),
        _unique_str("#include <internal/pycore_unicodeobject.h>"),
        _unique_str("#ifdef Py_BUILD_CORE"),
        _unique_str("#undef Py_BUILD_CORE"),
        _unique_str("#endif"),
        _unique_str("#define EMPTY_CONST_CHARP \"\""),
        _unique_str("#define _STR_RETURN_WITHOUT_EXCEPTION \"error return without exception set\""),
        _unique_str("#define _STR_UNKNOWN_OPCODE \"%U:%d: unknown opcode %d\""),
        _unique_str("#define _STR_NO_AENTER \"'%.200s' object does not support the asynchronous context manager protocol\""),
        _unique_str("#define _STR_NO_AEXIT \"'%.200s' object does not support the asynchronous context manager protocol (missed __aexit__ method)\""),
        _unique_str("#define _STR_NO_ENTER \"'%.200s' object does not support the context manager protocol\""),
        _unique_str("#define _STR_NO_EXIT \"'%.200s' object does not support the context manager protocol (missed __exit__ method)\""),
        _unique_str("#define _INT_DECLARE() 0"),
        _unique_str("#define _INT_ADDRESS(var) &(var)"),
        _unique_str("#define _DEREFERENCE(var) *(var)"),
        _unique_str("#define _POINTER_ADD(ptr, n) (ptr) + (n)"),
        _unique_str("#define _POINTER_SUB(ptr, n) (ptr) - (n)"),
        _unique_str("#define _POINTER_INPLACE_ADD(ptr, n) (ptr) += (n)"),
        _unique_str("#define _INIT_NULL_PTR() NULL"),
        _unique_str("#define _GET_FRAME_INSTR_PTR(frame) (frame)->instr_ptr"),
        _unique_str("#define _GET_INSTR_PTR_OPCODE(next_instr) (next_instr)->op.code"),
        _unique_str("#define _GET_INSTR_PTR_OPARG(next_instr) (next_instr)->op.arg"),
        _unique_str("#define _GET_LOCAL_AS_ARRAY(frame, i) &GETLOCAL(frame, i)"),
        _unique_str("#define _ADVANCE_ADAPTIVE_COUNTER(instr_ptr) ADVANCE_ADAPTIVE_COUNTER((instr_ptr)[1].counter)"),
        _unique_str("#define _PAUSE_ADAPTIVE_COUNTER(next_instr) \\"),
        _unique_str("    { \\"),
        _unique_str("        _PyBinaryOpCache *cache = (_PyBinaryOpCache *)((next_instr) + 1); \\"),
        _unique_str("        PAUSE_ADAPTIVE_COUNTER(cache->counter); \\"),
        _unique_str("    }"),
        _unique_str("#define _GET_CODE_OBJECT_ORIGINAL_OPCODE(code, here) (code)->_co_monitoring->lines[(int)((here) - _PyCode_CODE((code)))].original_opcode"),
        _unique_str("#define _GET_LONG_OBJECT_VALUE(obj) ((PyLongObject *)obj)->long_value.ob_digit[0]"),
        _unique_str("#define _GET_FLOAT_OBJECT_VALUE(obj) ((PyFloatObject *)obj)->ob_fval"),
        _unique_str("#define _SET_FLOAT_OBJECT_VALUE(obj, value) ((PyFloatObject *)obj)->ob_fval = value"),
        _unique_str("#define _GET_EVAL_FRAME_FUNC(tstate) (tstate)->interp->eval_frame"),
        _unique_str("#define _GET_HEAP_GET_ITEM(ht) (ht)->_spec_cache.getitem"),
        _unique_str("#define _GET_HEAP_GET_ITEM_VERSION(ht) (ht)->_spec_cache.getitem_version"),
        _unique_str("#define _SET_FRAME_LOCALSPLUS(frame, i, v) (frame)->localsplus[(i)] = (v)"),
        _unique_str("#define _CPYBOOSTER_Py_ID(NAME) &_Py_ID(NAME)"),
        _unique_str("#define _CPYBOOSTER_PyEval_BinaryOps(oparg, lhs, rhs) _PyEval_BinaryOps[(oparg)]((lhs), (rhs))"),
        _unique_str("#define _CPYBOOSTER_PyEval_ConversionFuncs(oparg, value) _PyEval_ConversionFuncs[(oparg)]((value))"),
        _unique_str("#define _CPYBOOSTER_read_u16_1(instr_ptr) read_u16(&(instr_ptr)[1].cache)"),
        _unique_str("#define _CPYBOOSTER_read_u16_2(instr_ptr) read_u16(&(instr_ptr)[2].cache)"),
        _unique_str("#define _CPYBOOSTER_read_u16_3(instr_ptr) read_u16(&(instr_ptr)[3].cache)"),
        _unique_str("#define _CPYBOOSTER_read_u16_4(instr_ptr) read_u16(&(instr_ptr)[4].cache)"),
        _unique_str("// Python/ceval_macros.h"),
        _unique_str("#define INSTR_OFFSET(next_instr, frame)    ((int)((next_instr) - _PyCode_CODE(_PyFrame_GetCode((frame)))))"),
        _unique_str("#define NEXTOPARG(next_instr, opcode, oparg)  do { \\"),
        _unique_str("        _Py_CODEUNIT word  = {.cache = FT_ATOMIC_LOAD_UINT16_RELAXED(*(uint16_t*)(next_instr))}; \\"),
        _unique_str("        (opcode) = word.op.code; \\"),
        _unique_str("        (oparg) = word.op.arg; \\"),
        _unique_str("    } while (0)"),
        _unique_str(""),
        _unique_str("#define JUMPBY(next_instr, x)       (next_instr += (x))"),
        _unique_str("#define SKIP_OVER(next_instr, x)    (next_instr += (x))"),
        _unique_str(""),
        _unique_str("#define DISPATCH(next_instr, opcode, oparg) \\"),
        _unique_str("    { \\"),
        _unique_str("        NEXTOPARG((next_instr), (opcode), (oparg)); \\"),
        _unique_str("        PRE_DISPATCH_GOTO(); \\"),
        _unique_str("    }"),
        _unique_str(""),
        _unique_str("#define DISPATCH_SAME_OPARG(next_instr, opcode) \\"),
        _unique_str("    { \\"),
        _unique_str("        opcode = next_instr->op.code; \\"),
        _unique_str("        PRE_DISPATCH_GOTO(); \\"),
        _unique_str("    }"),
        _unique_str(""),
        _unique_str("#define PRE_DISPATCH_GOTO() ((void)0)"),
        _unique_str("#define STACK_LEVEL(stack_pointer, frame)  ((int)((stack_pointer) - _PyFrame_Stackbase((frame))))"),
        _unique_str("#define STACK_SIZE(frame)                  (_PyFrame_GetCode((frame))->co_stacksize)"),
        _unique_str("#define EMPTY(stack_pointer, frame)        (STACK_LEVEL((stack_pointer), (frame)) == 0)"),
        _unique_str("#define TOP(stack_pointer)                 ((stack_pointer)[-1])"),
        _unique_str("#define SECOND(stack_pointer)              ((stack_pointer)[-2])"),
        _unique_str("#define THIRD(stack_pointer)               ((stack_pointer)[-3])"),
        _unique_str("#define FOURTH(stack_pointer)              ((stack_pointer)[-4])"),
        _unique_str("#define PEEK(stack_pointer, n)             ((stack_pointer)[-(n)])"),
        _unique_str("#define POKE(stack_pointer, n, v)          ((stack_pointer)[-(n)] = (v))"),
        _unique_str("#define SET_TOP(stack_pointer, v)          ((stack_pointer)[-1] = (v))"),
        _unique_str("#define SET_SECOND(stack_pointer, v)       ((stack_pointer)[-2] = (v))"),
        _unique_str("#define BASIC_STACKADJ(stack_pointer, n)   ((stack_pointer) += n)"),
        _unique_str("#define BASIC_PUSH(stack_pointer, v)       (*(stack_pointer)++ = (v))"),
        _unique_str("#define BASIC_POP(stack_pointer)           (*--(stack_pointer))"),
        _unique_str("#define PUSH(stack_pointer, v)             BASIC_PUSH((stack_pointer), (v))"),
        _unique_str("#define POP(stack_pointer)                 BASIC_POP((stack_pointer))"),
        _unique_str("#define STACK_GROW(stack_pointer, n)       BASIC_STACKADJ((stack_pointer), n)"),
        _unique_str("#define STACK_SHRINK(stack_pointer, n)     BASIC_STACKADJ((stack_pointer), -(n))"),
        _unique_str(""),
        _unique_str("#define LOCALS_ARRAY(frame)    (frame->localsplus)"),
        _unique_str("#define GETLOCAL(frame, i)     (frame->localsplus[i])"),
        _unique_str(""),
        _unique_str("#define ADAPTIVE_COUNTER_TRIGGERS(COUNTER) backoff_counter_triggers(forge_backoff_counter((COUNTER)))"),
        _unique_str("#ifdef Py_GIL_DISABLED"),
        _unique_str("#define ADVANCE_ADAPTIVE_COUNTER(COUNTER) \\"),
        _unique_str("    do { \\"),
        _unique_str("        /* gh-115999 tracks progress on addressing this. */ \\"),
        _unique_str("        static_assert(0, \"The specializing interpreter is not yet thread-safe\"); \\"),
        _unique_str("    } while (0);"),
        _unique_str("#define PAUSE_ADAPTIVE_COUNTER(COUNTER) ((void)COUNTER)"),
        _unique_str("#else"),
        _unique_str("#define ADVANCE_ADAPTIVE_COUNTER(COUNTER) \\"),
        _unique_str("    do { \\"),
        _unique_str("        (COUNTER) = advance_backoff_counter((COUNTER)); \\"),
        _unique_str("    } while (0);"),
        _unique_str("#define PAUSE_ADAPTIVE_COUNTER(COUNTER) \\"),
        _unique_str("    do { \\"),
        _unique_str("        (COUNTER) = pause_backoff_counter((COUNTER)); \\"),
        _unique_str("    } while (0);"),
        _unique_str("#endif"),
        _unique_str(""),
        _unique_str("static inline int _Py_EnterRecursivePy(PyThreadState *tstate) {"),
        _unique_str("    return (tstate->py_recursion_remaining-- <= 0) && _Py_CheckRecursiveCallPy(tstate);"),
        _unique_str("}"),
        _unique_str(""),
        _unique_str("static inline void _Py_LeaveRecursiveCallPy(PyThreadState *tstate) {"),
        _unique_str("    tstate->py_recursion_remaining++;"),
        _unique_str("}"),
        _unique_str(""),
        _unique_str("extern void monitor_reraise(PyThreadState *tstate,  _PyInterpreterFrame *frame, _Py_CODEUNIT *instr);"),
        _unique_str("extern int monitor_stop_iteration(PyThreadState *tstate,  _PyInterpreterFrame *frame, _Py_CODEUNIT *instr, PyObject *value);"),
        _unique_str("extern void monitor_unwind(PyThreadState *tstate,  _PyInterpreterFrame *frame, _Py_CODEUNIT *instr);"),
        _unique_str("extern int monitor_handled(PyThreadState *tstate,  _PyInterpreterFrame *frame, _Py_CODEUNIT *instr, PyObject *exc);"),
        _unique_str("extern void monitor_throw(PyThreadState *tstate,  _PyInterpreterFrame *frame, _Py_CODEUNIT *instr);"),
        _unique_str(""),
        _unique_str("extern int get_exception_handler(PyCodeObject *code, int index, int *level, int *handler, int *lasti);"),
        _unique_str(""),
    ],
    separate_module_sources=[
        _EXTRA_C_SOURCE,
        _INSTRUMENTATION_SOURCE,
        _CODE_OBJECT_SOURCE,
        _FRAME_SOURCE,
        _FRAME_OBJECT_SOURCE,
        _ERRORS_SOURCE,
        _OPCODE_METADATA_SOURCE,
        _SPECIALIZE_SOURCE,
    ],
)

_Py_INTERPRETER_TRAMPOLINE_INSTRUCTIONS = rffi.CConstant(
    "_Py_INTERPRETER_TRAMPOLINE_INSTRUCTIONS",
    rffi.CArrayPtr(cpython._Py_CODEUNIT),
)

_PyOpcode_Caches = rffi.CConstant(
    "_PyOpcode_Caches",
    rffi.CArrayPtr(rffi.UCHAR),
)

_Py_EnsureTstateNotNULL = rffi.llexternal("_Py_EnsureTstateNotNULL", [cpython.PyThreadState_P], lltype.Void, **cpython._llextkws)
_Py_EnterRecursiveCallTstate = rffi.llexternal("_Py_EnterRecursiveCallTstate", [cpython.PyThreadState_P, rffi.CONST_CCHARP], lltype.Bool, **cpython._llextkws)
_Py_EnterRecursivePy = rffi.llexternal("_Py_EnterRecursivePy", [cpython.PyThreadState_P], lltype.Bool, **cpython._llextkws)
_Py_LeaveRecursiveCallPy = rffi.llexternal("_Py_LeaveRecursiveCallPy", [cpython.PyThreadState_P], lltype.Void, **cpython._llextkws)
_PyEval_MonitorRaise = rffi.llexternal("_PyEval_MonitorRaise", [cpython.PyThreadState_P, cpython._PyInterpreterFrame_P, cpython._Py_CODEUNIT_P], lltype.Void, **cpython._llextkws)
_PyEval_FrameClearAndPop = rffi.llexternal("_PyEval_FrameClearAndPop", [cpython.PyThreadState_P, cpython._PyInterpreterFrame_P], lltype.Void, **cpython._llextkws)
_PyEval_BinaryOps = rffi.llexternal("_CPYBOOSTER_PyEval_BinaryOps", [rffi.INT, cpython.PyObject_P, cpython.PyObject_P], cpython.PyObject_P, **cpython._llextkws)
_PyEval_ConversionFuncs = rffi.llexternal("_CPYBOOSTER_PyEval_ConversionFuncs", [rffi.INT, cpython.PyObject_P], cpython.PyObject_P, **cpython._llextkws)
_PyCode_CODE = rffi.llexternal("_PyCode_CODE", [cpython.PyCodeObject_P], cpython._Py_CODEUNIT_P, **cpython._llextkws)
_PyInterpreterFrame_LASTI = rffi.llexternal("_PyInterpreterFrame_LASTI", [cpython._PyInterpreterFrame_P], rffi.INT, **cpython._llextkws)
_PyThreadState_HasStackSpace = rffi.llexternal("_PyThreadState_HasStackSpace", [cpython.PyThreadState_P, rffi.INT], lltype.Bool, **cpython._llextkws)
_PyFrame_PushUnchecked = rffi.llexternal("_PyFrame_PushUnchecked", [cpython.PyThreadState_P, cpython.PyFunctionObject_P, rffi.INT], cpython._PyInterpreterFrame_P, **cpython._llextkws)
_PyFrame_GetStackPointer = rffi.llexternal("_PyFrame_GetStackPointer", [cpython._PyInterpreterFrame_P], rffi.CArrayPtr(cpython.PyObject_P), **cpython._llextkws)
_PyFrame_SetStackPointer = rffi.llexternal("_PyFrame_SetStackPointer", [cpython._PyInterpreterFrame_P, rffi.CArrayPtr(cpython.PyObject_P)], lltype.Void, **cpython._llextkws)
_PyFrame_GetCode = rffi.llexternal("_PyFrame_GetCode", [cpython._PyInterpreterFrame_P], cpython.PyCodeObject_P, **cpython._llextkws)
_PyFrame_Stackbase = rffi.llexternal("_PyFrame_Stackbase", [cpython._PyInterpreterFrame_P], rffi.CArrayPtr(cpython.PyObject_P), **cpython._llextkws)
_PyFrame_GetFrameObject = rffi.llexternal("_PyFrame_GetFrameObject", [cpython._PyInterpreterFrame_P], cpython.PyFrameObject_P, **cpython._llextkws)
_PyFrame_IsIncomplete = rffi.llexternal("_PyFrame_IsIncomplete", [cpython._PyInterpreterFrame_P], lltype.Bool, **cpython._llextkws)
PyUnstable_InterpreterFrame_GetLine = rffi.llexternal("PyUnstable_InterpreterFrame_GetLine", [cpython._PyInterpreterFrame_P], rffi.INT, **cpython._llextkws)
_Py_Instrument = rffi.llexternal("_Py_Instrument", [cpython.PyCodeObject_P, cpython.PyInterpreterState_P], rffi.INT, **cpython._llextkws)
_Py_call_instrumentation_line = rffi.llexternal("_Py_call_instrumentation_line", [cpython.PyThreadState_P, cpython._PyInterpreterFrame_P, cpython._Py_CODEUNIT_P, cpython._Py_CODEUNIT_P], rffi.INT, **cpython._llextkws)
_PyErr_Occurred = rffi.llexternal("_PyErr_Occurred", [cpython.PyThreadState_P], cpython.PyObject_P, **cpython._llextkws)
_PyErr_SetString = rffi.llexternal("_PyErr_SetString", [cpython.PyThreadState_P, cpython.PyObject_P, rffi.CONST_CCHARP], lltype.Void, **cpython._llextkws)
_PyErr_GetRaisedException = rffi.llexternal("_PyErr_GetRaisedException", [cpython.PyThreadState_P], cpython.PyObject_P, **cpython._llextkws)
_PyErr_Format_PyObject_Int_Uchar = rffi.llexternal("_PyErr_Format", [cpython.PyThreadState_P, cpython.PyObject_P, rffi.CONST_CCHARP, cpython.PyObject_P, rffi.INT, rffi.UCHAR], cpython.PyObject_P, **cpython._llextkws)
_PyErr_Format_Constccharp = rffi.llexternal("_PyErr_Format", [cpython.PyThreadState_P, cpython.PyObject_P, rffi.CONST_CCHARP, rffi.CONST_CCHARP], cpython.PyObject_P, **cpython._llextkws)
_PyErr_SetKeyError = rffi.llexternal("_PyErr_SetKeyError", [cpython.PyObject_P], lltype.Void, **cpython._llextkws)
_PyObject_CallNoArgs = rffi.llexternal("_PyObject_CallNoArgs", [cpython.PyObject_P], cpython.PyObject_P, **cpython._llextkws)
_PyObject_LookupSpecial = rffi.llexternal("_PyObject_LookupSpecial", [cpython.PyObject_P, cpython.PyObject_P], cpython.PyObject_P, **cpython._llextkws)
_Py_ID = rffi.llexternal("_CPYBOOSTER_Py_ID", [rffi.CONST_CCHARP], cpython.PyObject_P, **cpython._llextkws)

_Py_Specialize_BinaryOp = rffi.llexternal("_Py_Specialize_BinaryOp", [cpython.PyObject_P, cpython.PyObject_P, cpython._Py_CODEUNIT_P, rffi.INT, rffi.CArrayPtr(cpython.PyObject_P)], lltype.Void, **cpython._llextkws)
_Py_Specialize_BinarySubscr = rffi.llexternal("_Py_Specialize_BinarySubscr", [cpython.PyObject_P, cpython.PyObject_P, cpython._Py_CODEUNIT_P], lltype.Void, **cpython._llextkws)

_Py_DECREF_SPECIALIZED = rffi.llexternal("_Py_DECREF_SPECIALIZED", [cpython.PyObject_P, cpython.destructor], lltype.Void, **cpython._llextkws)
_Py_DECREF_NO_DEALLOC = rffi.llexternal("_Py_DECREF_NO_DEALLOC", [cpython.PyObject_P], lltype.Void, **cpython._llextkws)

_PyFloat_ExactDealloc = rffi.llexternal("_PyFloat_ExactDealloc", [cpython.PyObject_P], lltype.Void, **cpython._llextkws)

_PyLong_Add = rffi.llexternal("_PyLong_Add", [cpython.PyLongObject_P, cpython.PyLongObject_P], cpython.PyObject_P, **cpython._llextkws)
_PyLong_Multiply = rffi.llexternal("_PyLong_Multiply", [cpython.PyLongObject_P, cpython.PyLongObject_P], cpython.PyObject_P, **cpython._llextkws)
_PyLong_Subtract = rffi.llexternal("_PyLong_Subtract", [cpython.PyLongObject_P, cpython.PyLongObject_P], cpython.PyObject_P, **cpython._llextkws)
_PyLong_IsNonNegativeCompact = rffi.llexternal("_PyLong_IsNonNegativeCompact", [cpython.PyLongObject_P], lltype.Bool, **cpython._llextkws)

_PyUnicode_ExactDealloc = rffi.llexternal("_PyUnicode_ExactDealloc", [cpython.PyObject_P], lltype.Void, **cpython._llextkws)

read_u16_1 = rffi.llexternal("_CPYBOOSTER_read_u16_1", [cpython._Py_CODEUNIT_P], rffi.USHORT, **cpython._llextkws)
read_u16_2 = rffi.llexternal("_CPYBOOSTER_read_u16_2", [cpython._Py_CODEUNIT_P], rffi.USHORT, **cpython._llextkws)
read_u16_3 = rffi.llexternal("_CPYBOOSTER_read_u16_3", [cpython._Py_CODEUNIT_P], rffi.USHORT, **cpython._llextkws)
read_u16_4 = rffi.llexternal("_CPYBOOSTER_read_u16_4", [cpython._Py_CODEUNIT_P], rffi.USHORT, **cpython._llextkws)

get_exception_handler = rffi.llexternal("get_exception_handler", [cpython.PyCodeObject_P, rffi.INT, rffi.INT_realP, rffi.INT_realP, rffi.INT_realP], rffi.INT, **cpython._llextkws)
monitor_reraise = rffi.llexternal("monitor_reraise", [cpython.PyThreadState_P, cpython._PyInterpreterFrame_P, cpython._Py_CODEUNIT_P], lltype.Void, **cpython._llextkws)
monitor_stop_iteration = rffi.llexternal("monitor_stop_iteration", [cpython.PyThreadState_P, cpython._PyInterpreterFrame_P, cpython._Py_CODEUNIT_P, cpython.PyObject_P], lltype.Bool, **cpython._llextkws)
monitor_unwind = rffi.llexternal("monitor_unwind", [cpython.PyThreadState_P, cpython._PyInterpreterFrame_P, cpython._Py_CODEUNIT_P], lltype.Void, **cpython._llextkws)
monitor_handled = rffi.llexternal("monitor_handled", [cpython.PyThreadState_P, cpython._PyInterpreterFrame_P, cpython._Py_CODEUNIT_P, cpython.PyObject_P], rffi.INT, **cpython._llextkws)
monitor_throw = rffi.llexternal("monitor_throw", [cpython.PyThreadState_P, cpython._PyInterpreterFrame_P, cpython._Py_CODEUNIT_P], lltype.Void, **cpython._llextkws)

__aenter__ = rffi.CConstant("__aenter__", rffi.CONST_CCHARP)
__aexit__ = rffi.CConstant("__aexit__", rffi.CONST_CCHARP)
__enter__ = rffi.CConstant("__enter__", rffi.CONST_CCHARP)
__exit__ = rffi.CConstant("__exit__", rffi.CONST_CCHARP)

EMPTY_CONST_CHARP = rffi.CConstant("EMPTY_CONST_CHARP", rffi.CONST_CCHARP)
_STR_RETURN_WITHOUT_EXCEPTION = rffi.CConstant("_STR_RETURN_WITHOUT_EXCEPTION", rffi.CONST_CCHARP)
_STR_UNKNOWN_OPCODE = rffi.CConstant("_STR_UNKNOWN_OPCODE", rffi.CONST_CCHARP)
_STR_NO_AENTER = rffi.CConstant("_STR_NO_AENTER", rffi.CONST_CCHARP)
_STR_NO_AEXIT = rffi.CConstant("_STR_NO_AEXIT", rffi.CONST_CCHARP)
_STR_NO_ENTER = rffi.CConstant("_STR_NO_ENTER", rffi.CONST_CCHARP)
_STR_NO_EXIT = rffi.CConstant("_STR_NO_EXIT", rffi.CONST_CCHARP)
_INT_DECLARE = rffi.llexternal("_INT_DECLARE", [], rffi.INT, **cpython._llextkws)
_UINT8_DECLARE = rffi.llexternal("_INT_DECLARE", [], rffi.UCHAR, **cpython._llextkws)
_INT_ADDRESS = rffi.llexternal("_INT_ADDRESS", [rffi.INT], rffi.INT_realP, **cpython._llextkws)
_INIT_PYOBJECT = rffi.llexternal("_INIT_NULL_PTR", [], cpython.PyObject_P, **cpython._llextkws)
_INIT_NEXT_INSTR = rffi.llexternal("_INIT_NULL_PTR", [], cpython._Py_CODEUNIT_P, **cpython._llextkws)
_INIT_STACK_POINTER = rffi.llexternal("_INIT_NULL_PTR", [], rffi.CArrayPtr(cpython.PyObject_P), **cpython._llextkws)
_INSTR_PTR_ADD = rffi.llexternal("_POINTER_ADD", [cpython._Py_CODEUNIT_P, rffi.INT], cpython._Py_CODEUNIT_P, **cpython._llextkws)
_INSTR_PTR_SUB = rffi.llexternal("_POINTER_SUB", [cpython._Py_CODEUNIT_P, rffi.INT], cpython._Py_CODEUNIT_P, **cpython._llextkws)
_INSTR_PTRS_SUB = rffi.llexternal("_POINTER_SUB", [cpython._Py_CODEUNIT_P, cpython._Py_CODEUNIT_P], cpython.Py_ssize_t, **cpython._llextkws)
_INSTR_PTR_INPLACE_ADD = rffi.llexternal("_POINTER_INPLACE_ADD", [cpython._Py_CODEUNIT_P, rffi.INT], lltype.Void, **cpython._llextkws)
_GET_FRAME_INSTR_PTR = rffi.llexternal("_GET_FRAME_INSTR_PTR", [cpython._PyInterpreterFrame_P], cpython._Py_CODEUNIT_P, **cpython._llextkws)
_GET_INSTR_PTR_OPCODE = rffi.llexternal("_GET_INSTR_PTR_OPCODE", [cpython._Py_CODEUNIT_P], rffi.UCHAR, **cpython._llextkws)
_GET_INSTR_PTR_OPARG = rffi.llexternal("_GET_INSTR_PTR_OPARG", [cpython._Py_CODEUNIT_P], rffi.INT, **cpython._llextkws)
_GET_CODE_OBJECT_ORIGINAL_OPCODE = rffi.llexternal("_GET_CODE_OBJECT_ORIGINAL_OPCODE", [cpython.PyCodeObject_P, cpython._Py_CODEUNIT_P], rffi.INT, **cpython._llextkws)
_GET_LONG_OBJECT_VALUE = rffi.llexternal("_GET_LONG_OBJECT_VALUE", [cpython.PyObject_P], cpython.Py_ssize_t, **cpython._llextkws)
_GET_FLOAT_OBJECT_VALUE = rffi.llexternal("_GET_FLOAT_OBJECT_VALUE", [cpython.PyObject_P], lltype.Float, **cpython._llextkws)
_SET_FLOAT_OBJECT_VALUE = rffi.llexternal("_SET_FLOAT_OBJECT_VALUE", [cpython.PyObject_P, lltype.Float], lltype.Void, **cpython._llextkws)
_GET_EVAL_FRAME_FUNC = rffi.llexternal("_GET_EVAL_FRAME_FUNC", [cpython.PyThreadState_P], cpython._PyFrameEvalFunction, **cpython._llextkws)
_GET_HEAP_GET_ITEM = rffi.llexternal("_GET_HEAP_GET_ITEM", [cpython.PyHeapTypeObject_P], cpython.PyObject_P, **cpython._llextkws)
_GET_HEAP_GET_ITEM_VERSION = rffi.llexternal("_GET_HEAP_GET_ITEM_VERSION", [cpython.PyHeapTypeObject_P], rffi.UINT, **cpython._llextkws)
_SET_FRAME_LOCALSPLUS = rffi.llexternal("_SET_FRAME_LOCALSPLUS", [cpython._PyInterpreterFrame_P, rffi.INT, cpython.PyObject_P], lltype.Void, **cpython._llextkws)
_ADVANCE_ADAPTIVE_COUNTER = rffi.llexternal("_ADVANCE_ADAPTIVE_COUNTER", [cpython._Py_CODEUNIT_P], lltype.Void, **cpython._llextkws)
_PAUSE_ADAPTIVE_COUNTER = rffi.llexternal("_PAUSE_ADAPTIVE_COUNTER", [cpython._Py_CODEUNIT_P], lltype.Void, **cpython._llextkws)
_GET_LOCAL_AS_ARRAY = rffi.llexternal("_GET_LOCAL_AS_ARRAY", [cpython._PyInterpreterFrame_P, rffi.INT], rffi.CArrayPtr(cpython.PyObject_P), **cpython._llextkws)
_PYOBJECT_ADDRESS = rffi.llexternal("_INT_ADDRESS", [cpython.PyObject_P], rffi.CArrayPtr(cpython.PyObject_P), **cpython._llextkws)
_DEREF_LOCAL_ARRAY = rffi.llexternal("_DEREFERENCE", [rffi.CArrayPtr(cpython.PyObject_P)], cpython.PyObject_P, **cpython._llextkws)

JUMPBY = rffi.llexternal("JUMPBY", [cpython._Py_CODEUNIT_P, rffi.INT], lltype.Void, **cpython._llextkws)
SKIP_OVER = rffi.llexternal("SKIP_OVER", [cpython._Py_CODEUNIT_P, rffi.INT], lltype.Void, **cpython._llextkws)
INSTR_OFFSET = rffi.llexternal("INSTR_OFFSET", [cpython._Py_CODEUNIT_P, cpython._PyInterpreterFrame_P], rffi.INT, **cpython._llextkws)
DISPATCH = rffi.llexternal("DISPATCH", [cpython._Py_CODEUNIT_P, rffi.UCHAR, rffi.INT], lltype.Void, **cpython._llextkws)
DISPATCH_SAME_OPARG = rffi.llexternal("DISPATCH_SAME_OPARG", [cpython._Py_CODEUNIT_P, rffi.UCHAR], lltype.Void, **cpython._llextkws)
PRE_DISPATCH_GOTO = rffi.llexternal("PRE_DISPATCH_GOTO", [], lltype.Void, **cpython._llextkws)
STACK_LEVEL = rffi.llexternal("STACK_LEVEL", [rffi.CArrayPtr(cpython.PyObject_P), cpython._PyInterpreterFrame_P], rffi.INT, **cpython._llextkws)
STACK_SIZE = rffi.llexternal("STACK_SIZE", [cpython._PyInterpreterFrame_P], rffi.INT, **cpython._llextkws)
EMPTY = rffi.llexternal("EMPTY", [rffi.CArrayPtr(cpython.PyObject_P), cpython._PyInterpreterFrame_P], lltype.Bool, **cpython._llextkws)
TOP = rffi.llexternal("TOP", [rffi.CArrayPtr(cpython.PyObject_P)], cpython.PyObject_P, **cpython._llextkws)
SECOND = rffi.llexternal("SECOND", [rffi.CArrayPtr(cpython.PyObject_P)], cpython.PyObject_P, **cpython._llextkws)
THIRD = rffi.llexternal("THIRD", [rffi.CArrayPtr(cpython.PyObject_P)], cpython.PyObject_P, **cpython._llextkws)
FOURTH = rffi.llexternal("FOURTH", [rffi.CArrayPtr(cpython.PyObject_P)], cpython.PyObject_P, **cpython._llextkws)
PEEK = rffi.llexternal("PEEK", [rffi.CArrayPtr(cpython.PyObject_P), rffi.INT], cpython.PyObject_P, **cpython._llextkws)
POKE = rffi.llexternal("POKE", [rffi.CArrayPtr(cpython.PyObject_P), rffi.INT, cpython.PyObject_P], lltype.Void, **cpython._llextkws)
SET_TOP = rffi.llexternal("SET_TOP", [rffi.CArrayPtr(cpython.PyObject_P), cpython.PyObject_P], lltype.Void, **cpython._llextkws)
SET_SECOND = rffi.llexternal("SET_SECOND", [rffi.CArrayPtr(cpython.PyObject_P), cpython.PyObject_P], lltype.Void, **cpython._llextkws)
BASIC_STACKADJ = rffi.llexternal("BASIC_STACKADJ", [rffi.CArrayPtr(cpython.PyObject_P), rffi.INT], lltype.Void, **cpython._llextkws)
BASIC_PUSH = rffi.llexternal("BASIC_PUSH", [rffi.CArrayPtr(cpython.PyObject_P), cpython.PyObject_P], lltype.Void, **cpython._llextkws)
BASIC_POP = rffi.llexternal("BASIC_POP", [rffi.CArrayPtr(cpython.PyObject_P)], cpython.PyObject_P, **cpython._llextkws)
PUSH = rffi.llexternal("PUSH", [rffi.CArrayPtr(cpython.PyObject_P), cpython.PyObject_P], lltype.Void, **cpython._llextkws)
POP = rffi.llexternal("POP", [rffi.CArrayPtr(cpython.PyObject_P)], cpython.PyObject_P, **cpython._llextkws)
STACK_GROW = rffi.llexternal("STACK_GROW", [rffi.CArrayPtr(cpython.PyObject_P), rffi.INT], lltype.Void, **cpython._llextkws)
STACK_SHRINK = rffi.llexternal("STACK_SHRINK", [rffi.CArrayPtr(cpython.PyObject_P), rffi.INT], lltype.Void, **cpython._llextkws)
LOCALS_ARRAY = rffi.llexternal("LOCALS_ARRAY", [cpython._PyInterpreterFrame_P], rffi.CArrayPtr(cpython.PyObject_P), **cpython._llextkws)
GETLOCAL = rffi.llexternal("GETLOCAL", [cpython._PyInterpreterFrame_P, rffi.INT], cpython.PyObject_P, **cpython._llextkws)
ADAPTIVE_COUNTER_TRIGGERS = rffi.llexternal("ADAPTIVE_COUNTER_TRIGGERS", [rffi.USHORT], lltype.Bool, **cpython._llextkws)

PY_EVAL_C_STACK_UNITS = 2


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

    opcode = _UINT8_DECLARE()
    oparg = _INT_DECLARE()
    next_instr = _INIT_NEXT_INSTR()
    stack_pointer = _INIT_STACK_POINTER()

    tstate.c_c_recursion_remaining = r_int32(PY_EVAL_C_STACK_UNITS - 1)
    if _Py_EnterRecursiveCallTstate(tstate, EMPTY_CONST_CHARP):
        tstate.c_c_recursion_remaining = llop.int_sub(rffi.INT, tstate.c_c_recursion_remaining, 1)
        tstate.c_py_recursion_remaining = llop.int_sub(rffi.INT, tstate.c_py_recursion_remaining, 1)
        return _exit_unwind(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)

    if llop.int_is_true(lltype.Bool, throwflag):
        if _Py_EnterRecursivePy(tstate):
            return _exit_unwind(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
        # Because this avoids the RESUME,
        # we need to update instrumentation
        _Py_Instrument(_PyFrame_GetCode(frame), tstate.c_interp)
        # TO DO -- Monitor throw entry.
        monitor_throw(tstate, frame, frame.c_instr_ptr)
        return _resume_with_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)

    return _start_frame(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _start_frame(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    if _Py_EnterRecursivePy(tstate):
        return _exit_unwind(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    next_instr = _GET_FRAME_INSTR_PTR(frame)
    return _resume_frame(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _resume_frame(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    stack_pointer = _PyFrame_GetStackPointer(frame)
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


def _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    if llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BEFORE_ASYNC_WITH):
        return _target_before_async_with(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BEFORE_WITH):
        return _target_before_with(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_OP):
        return _target_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_OP_ADD_FLOAT):
        return _target_binary_op_add_float(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_OP_ADD_INT):
        return _target_binary_op_add_int(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_OP_ADD_UNICODE):
        return _target_binary_op_add_unicode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_OP_INPLACE_ADD_UNICODE):
        return _target_binary_op_inplace_add_unicode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_OP_MULTIPLY_FLOAT):
        return _target_binary_op_multiply_float(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_OP_MULTIPLY_INT):
        return _target_binary_op_multiply_int(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_OP_SUBTRACT_FLOAT):
        return _target_binary_op_subtract_float(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_OP_SUBTRACT_INT):
        return _target_binary_op_subtract_int(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_SLICE):
        return _target_binary_slice(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_SUBSCR):
        return _target_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_SUBSCR_DICT):
        return _target_binary_subscr_dict(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_SUBSCR_GETITEM):
        return _target_binary_subscr_getitem(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.BINARY_SUBSCR_LIST_INT):
        return _target_binary_subscr_list_int(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.INTERPRETER_EXIT):
        return _target_interpreter_exit(tstate, frame, entry_frame, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.STORE_SLICE):
        return _target_store_slice(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    elif llop.char_eq(lltype.Bool, opcode, cpython.opcode_ids.INSTRUMENTED_LINE):
        prev = _GET_FRAME_INSTR_PTR(frame)
        frame.c_instr_ptr = next_instr
        here = _GET_FRAME_INSTR_PTR(frame)
        original_opcode = _INT_DECLARE()
        if llop.int_is_true(lltype.Bool, tstate.c_tracing):
            code = _PyFrame_GetCode(frame)
            original_opcode = _GET_CODE_OBJECT_ORIGINAL_OPCODE(code, here)
        else:
            _PyFrame_SetStackPointer(frame, stack_pointer)
            original_opcode = _Py_call_instrumentation_line(tstate, frame, here, prev)
            stack_pointer = _PyFrame_GetStackPointer(frame)
            if llop.int_lt(lltype.Bool, original_opcode, 0):
                next_instr = _INSTR_PTR_ADD(here, r_int32(1))
                return _error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
            next_instr = _GET_FRAME_INSTR_PTR(frame)
            if not llop.ptr_eq(lltype.Bool, next_instr, here):
                DISPATCH(next_instr, opcode, oparg)
                return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
        if llop.int_is_true(lltype.Bool, _PyOpcode_Caches[original_opcode]):
            # Prevent the underlying instruction from specializing
            # and overwriting the instrumentation.
            _PAUSE_ADAPTIVE_COUNTER(next_instr)
        opcode = rffi.cast(rffi.UCHAR, original_opcode)
        return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    else:
        # Tell C compilers not to hold the opcode variable in the loop.
        # next_instr points the current instruction without TARGET().
        opcode = _GET_INSTR_PTR_OPCODE(next_instr)
        _PyErr_Format_PyObject_Int_Uchar(tstate, cpython.PyExc_SystemError,
                                         _STR_UNKNOWN_OPCODE,
                                         _PyFrame_GetCode(frame).c_co_filename,
                                         PyUnstable_InterpreterFrame_GetLine(frame),
                                         opcode)
        return _error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    # End instructions

    # This should never be reached. Every opcode should end with DISPATCH()
    # or goto error.
    cpython.Py_UNREACHABLE()
    return lltype.nullptr(cpython.PyObject)


@always_inline
def _pop_4_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    STACK_SHRINK(stack_pointer, r_int32(1))
    return _pop_3_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _pop_3_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    STACK_SHRINK(stack_pointer, r_int32(1))
    return _pop_2_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _pop_2_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    STACK_SHRINK(stack_pointer, r_int32(1))
    return _pop_1_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _pop_1_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    STACK_SHRINK(stack_pointer, r_int32(1))
    return _error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    # Double-check exception status.
    if llop.ptr_nonzero(lltype.Bool, _PyErr_Occurred(tstate)):
        _PyErr_SetString(tstate, cpython.PyExc_SystemError, _STR_RETURN_WITHOUT_EXCEPTION)

    if not _PyFrame_IsIncomplete(frame):
        f = _PyFrame_GetFrameObject(frame)
        if llop.ptr_nonzero(lltype.Bool, f):
            cpython.PyTraceBack_Here(f)
    _PyEval_MonitorRaise(tstate, frame, lltype.direct_ptradd(next_instr, -1))
    return _exception_unwind(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


# @always_inline
def _exception_unwind(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    offset = llop.int_sub(rffi.INT, INSTR_OFFSET(next_instr, frame), 1)
    level = _INT_DECLARE()
    handler = _INT_DECLARE()
    lasti = _INT_DECLARE()
    if llop.int_eq(lltype.Bool, get_exception_handler(_PyFrame_GetCode(frame), offset, _INT_ADDRESS(level), _INT_ADDRESS(handler), _INT_ADDRESS(lasti)), 0):
        # No handlers, so exit.
        # Pop remaining stack entries.
        stackbase = _PyFrame_Stackbase(frame)
        while llop.adr_gt(lltype.Bool, stack_pointer, stackbase):
            o = POP(stack_pointer)
            cpython.Py_XDECREF(o)
        _PyFrame_SetStackPointer(frame, stack_pointer)
        monitor_unwind(tstate, frame, _INSTR_PTR_SUB(next_instr, r_int32(1)))
        return _exit_unwind(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)

    new_top = rffi.ptradd(_PyFrame_Stackbase(frame), level)
    while llop.adr_gt(lltype.Bool, stack_pointer, new_top):
        v = POP(stack_pointer)
        cpython.Py_XDECREF(v)
    if llop.int_is_true(lltype.Bool, lasti):
        frame_lasti = _PyInterpreterFrame_LASTI(frame)
        py_lasti = cpython.PyLong_FromLong(frame_lasti)
        if llop.ptr_iszero(lltype.Bool, py_lasti):
            return _exception_unwind(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
        PUSH(stack_pointer, py_lasti)

    # Make the raw exception data
    # available to the handler,
    # so a program can emulate the
    # Python main loop. 
    exc = _PyErr_GetRaisedException(tstate)
    PUSH(stack_pointer, exc)
    next_instr = _INSTR_PTR_ADD(_PyCode_CODE(_PyFrame_GetCode(frame)), handler)

    if llop.int_lt(lltype.Bool, monitor_handled(tstate, frame, next_instr, exc), 0):
        return _exception_unwind(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _exit_unwind(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
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
        lltype.free(entry_frame, flavor="raw", track_allocation=False)
        return lltype.nullptr(cpython.PyObject)
    return _resume_with_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _resume_with_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    next_instr = _GET_FRAME_INSTR_PTR(frame)
    stack_pointer = _PyFrame_GetStackPointer(frame)
    return _error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_before_async_with(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(1))
    mgr = lltype.nullptr(cpython.PyObject)
    exit = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    mgr = TOP(stack_pointer)
    enter = _PyObject_LookupSpecial(mgr, _Py_ID(__aenter__))
    if llop.ptr_iszero(lltype.Bool, enter):
        if llop.ptr_nonzero(lltype.Bool, _PyErr_Occurred(tstate)):
            _PyErr_Format_Constccharp(tstate, cpython.PyExc_TypeError, _STR_NO_AENTER, cpython.Py_TYPE(mgr).c_tp_name)
        return _error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    exit = _PyObject_LookupSpecial(mgr, _Py_ID(__aexit__))
    if llop.ptr_iszero(lltype.Bool, exit):
        if llop.ptr_nonzero(lltype.Bool, _PyErr_Occurred(tstate)):
            _PyErr_Format_Constccharp(tstate, cpython.PyExc_TypeError, _STR_NO_AEXIT, cpython.Py_TYPE(mgr).c_tp_name)
        cpython.Py_DECREF(enter)
        return _error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    cpython.Py_DECREF(mgr)
    res = cpython.PyObject_CallNoArgs(enter)
    cpython.Py_DECREF(enter)
    if llop.ptr_iszero(lltype.Bool, res):
        cpython.Py_DECREF(exit)
        return _pop_1_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    SET_TOP(stack_pointer, exit)
    POKE(stack_pointer, r_int32(0), res)
    STACK_GROW(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_before_with(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(1))
    mgr = lltype.nullptr(cpython.PyObject)
    exit = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    mgr = TOP(stack_pointer)
    # pop the context manager, push its __exit__ and the
    # value returned from calling its __enter__
    enter = _PyObject_LookupSpecial(mgr, _Py_ID(__enter__))
    if llop.ptr_iszero(lltype.Bool, enter):
        if llop.ptr_nonzero(lltype.Bool, _PyErr_Occurred(tstate)):
            _PyErr_Format_Constccharp(tstate, cpython.PyExc_TypeError, _STR_NO_ENTER, cpython.Py_TYPE(mgr).c_tp_name)
        return _error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    exit = _PyObject_LookupSpecial(mgr, _Py_ID(__exit__))
    if llop.ptr_iszero(lltype.Bool, exit):
        if llop.ptr_nonzero(lltype.Bool, _PyErr_Occurred(tstate)):
            _PyErr_Format_Constccharp(tstate, cpython.PyExc_TypeError, _STR_NO_EXIT, cpython.Py_TYPE(mgr).c_tp_name)
        cpython.Py_DECREF(enter)
        return _error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    cpython.Py_DECREF(mgr)
    res = cpython.PyObject_CallNoArgs(enter)
    cpython.Py_DECREF(enter)
    if llop.ptr_iszero(lltype.Bool, res):
        cpython.Py_DECREF(exit)
        return _pop_1_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    SET_TOP(stack_pointer, exit)
    POKE(stack_pointer, r_int32(0), res)
    STACK_GROW(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer, lhs, rhs):
    res = _PyEval_BinaryOps(oparg, lhs, rhs)
    cpython.Py_DECREF(lhs)
    cpython.Py_DECREF(rhs)
    if llop.ptr_iszero(lltype.Bool, res):
        return _pop_2_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    SET_SECOND(stack_pointer, res)
    STACK_SHRINK(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer, container, sub):
    res = cpython.PyObject_GetItem(container, sub)
    cpython.Py_DECREF(container)
    cpython.Py_DECREF(sub)
    if llop.ptr_iszero(lltype.Bool, res):
        return _pop_2_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    SET_SECOND(stack_pointer, res)
    STACK_SHRINK(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


if cpython.ENABLE_SPECIALIZATION:
    @always_inline
    def _specialized_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer, this_instr, lhs, rhs):
        counter = read_u16_1(this_instr)
        if ADAPTIVE_COUNTER_TRIGGERS(counter):
            next_instr = this_instr
            _Py_Specialize_BinaryOp(lhs, rhs, next_instr, oparg, LOCALS_ARRAY(frame))
            DISPATCH_SAME_OPARG(next_instr, opcode)
            return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
        _ADVANCE_ADAPTIVE_COUNTER(this_instr)
        return _binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer, lhs, rhs)


    @always_inline
    def _specialized_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer, this_instr, container, sub):
        counter = read_u16_1(this_instr)
        if ADAPTIVE_COUNTER_TRIGGERS(counter):
            next_instr = this_instr
            _Py_Specialize_BinarySubscr(container, sub, next_instr)
            DISPATCH_SAME_OPARG(next_instr, opcode)
            return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
        _ADVANCE_ADAPTIVE_COUNTER(this_instr)
        return _binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer, container, sub)

else:
    @always_inline
    def _specialized_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer, this_instr, lhs, rhs):
        return _binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer, lhs, rhs)


    @always_inline
    def _specialized_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer, this_instr, container, sub):
        return _binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer, container, sub)


@always_inline
def _target_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(2))
    return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    this_instr = _INSTR_PTR_SUB(next_instr, r_int32(2))
    rhs = lltype.nullptr(cpython.PyObject)
    lhs = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    # _SPECIALIZED_BINARY_OP
    rhs = TOP(stack_pointer)
    lhs = SECOND(stack_pointer)
    # _BINARY_OP
    return _specialized_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer, this_instr, lhs, rhs)


@always_inline
def _target_binary_op_add_float(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(2))
    right = lltype.nullptr(cpython.PyObject)
    left = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    # _GUARD_BOTH_FLOAT
    right = TOP(stack_pointer)
    left = SECOND(stack_pointer)
    if not cpython.PyFloat_CheckExact(left):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    if not cpython.PyFloat_CheckExact(right):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    # Skip 1 cache entry
    # _BINARY_OP_ADD_FLOAT
    dres = _GET_FLOAT_OBJECT_VALUE(left) + _GET_FLOAT_OBJECT_VALUE(right)
    if llop.int_eq(lltype.Bool, cpython.Py_REFCNT(left), 1):
        _SET_FLOAT_OBJECT_VALUE(left, dres)
        _Py_DECREF_SPECIALIZED(right, _PyFloat_ExactDealloc)
        res = left
    elif llop.int_eq(lltype.Bool, cpython.Py_REFCNT(right), 1):
        _SET_FLOAT_OBJECT_VALUE(right, dres)
        _Py_DECREF_NO_DEALLOC(left)
        res = right
    else:
        res = cpython.PyFloat_FromDouble(dres)
        if llop.ptr_iszero(lltype.Bool, res):
            return _error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
        _Py_DECREF_NO_DEALLOC(left)
        _Py_DECREF_NO_DEALLOC(right)
    SET_SECOND(stack_pointer, res)
    STACK_SHRINK(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_binary_op_add_int(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(2))
    right = lltype.nullptr(cpython.PyObject)
    left = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    # _GUARD_BOTH_INT
    right = TOP(stack_pointer)
    left = SECOND(stack_pointer)
    if not cpython.PyLong_CheckExact(left):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    if not cpython.PyLong_CheckExact(right):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    # Skip 1 cache entry
    # _BINARY_OP_ADD_INT
    res = _PyLong_Add(rffi.cast(cpython.PyLongObject_P, left), rffi.cast(cpython.PyLongObject_P, right))
    _Py_DECREF_SPECIALIZED(right, rffi.cast(cpython.destructor, cpython.PyObject_Free))
    _Py_DECREF_SPECIALIZED(left, rffi.cast(cpython.destructor, cpython.PyObject_Free))
    if llop.ptr_iszero(lltype.Bool, res):
        return _pop_2_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    SET_SECOND(stack_pointer, res)
    STACK_SHRINK(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_binary_op_add_unicode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(2))
    right = lltype.nullptr(cpython.PyObject)
    left = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    # _GUARD_BOTH_UNICODE
    right = TOP(stack_pointer)
    left = SECOND(stack_pointer)
    if not cpython.PyUnicode_CheckExact(left):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    if not cpython.PyUnicode_CheckExact(right):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    # Skip 1 cache entry
    # _BINARY_OP_ADD_UNICODE
    res = cpython.PyUnicode_Concat(left, right)
    _Py_DECREF_SPECIALIZED(left, _PyUnicode_ExactDealloc)
    _Py_DECREF_SPECIALIZED(right, _PyUnicode_ExactDealloc)
    if llop.ptr_iszero(lltype.Bool, res):
        return _pop_2_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    SET_SECOND(stack_pointer, res)
    STACK_SHRINK(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_binary_op_inplace_add_unicode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(2))
    right = lltype.nullptr(cpython.PyObject)
    left = lltype.nullptr(cpython.PyObject)
    # _GUARD_BOTH_UNICODE
    right = TOP(stack_pointer)
    left = SECOND(stack_pointer)
    if not cpython.PyUnicode_CheckExact(left):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    if not cpython.PyUnicode_CheckExact(right):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    # Skip 1 cache entry
    # _BINARY_OP_INPLACE_ADD_UNICODE
    target_local = _GET_LOCAL_AS_ARRAY(frame, _GET_INSTR_PTR_OPARG(next_instr))
    if not llop.ptr_eq(lltype.Bool, _DEREF_LOCAL_ARRAY(target_local), left):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    # Handle `left = left + right` or `left += right` for str.
    #
    # When possible, extend `left` in place rather than
    # allocating a new PyUnicodeObject. This attempts to avoid
    # quadratic behavior when one neglects to use str.join().
    #
    # If `left` has only two references remaining (one from
    # the stack, one in the locals), DECREFing `left` leaves
    # only the locals reference, so PyUnicode_Append knows
    # that the string is safe to mutate.
    #
    cpython.PyUnicode_Append(target_local, right)
    _Py_DECREF_SPECIALIZED(right, _PyUnicode_ExactDealloc)
    if llop.ptr_iszero(lltype.Bool, _DEREF_LOCAL_ARRAY(target_local)):
        return _pop_2_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    # The STORE_FAST is already done.
    # assert(next_instr->op.code == STORE_FAST);
    SKIP_OVER(next_instr, r_int32(1))
    STACK_SHRINK(stack_pointer, r_int32(2))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_binary_op_multiply_float(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(2))
    right = lltype.nullptr(cpython.PyObject)
    left = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    # _GUARD_BOTH_FLOAT
    right = TOP(stack_pointer)
    left = SECOND(stack_pointer)
    if not cpython.PyFloat_CheckExact(left):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    if not cpython.PyFloat_CheckExact(right):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    # Skip 1 cache entry
    # _BINARY_OP_MULTIPLY_FLOAT
    dres = _GET_FLOAT_OBJECT_VALUE(left) * _GET_FLOAT_OBJECT_VALUE(right)
    if llop.int_eq(lltype.Bool, cpython.Py_REFCNT(left), 1):
        _SET_FLOAT_OBJECT_VALUE(left, dres)
        _Py_DECREF_SPECIALIZED(right, _PyFloat_ExactDealloc)
        res = left
    elif llop.int_eq(lltype.Bool, cpython.Py_REFCNT(right), 1):
        _SET_FLOAT_OBJECT_VALUE(right, dres)
        _Py_DECREF_NO_DEALLOC(left)
        res = right
    else:
        res = cpython.PyFloat_FromDouble(dres)
        if llop.ptr_iszero(lltype.Bool, res):
            return _error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
        _Py_DECREF_NO_DEALLOC(left)
        _Py_DECREF_NO_DEALLOC(right)
    SET_SECOND(stack_pointer, res)
    STACK_SHRINK(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_binary_op_multiply_int(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(2))
    right = lltype.nullptr(cpython.PyObject)
    left = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    # _GUARD_BOTH_INT
    right = TOP(stack_pointer)
    left = SECOND(stack_pointer)
    if not cpython.PyLong_CheckExact(left):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    if not cpython.PyLong_CheckExact(right):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    # Skip 1 cache entry
    # _BINARY_OP_MULTIPLY_INT
    res = _PyLong_Multiply(rffi.cast(cpython.PyLongObject_P, left), rffi.cast(cpython.PyLongObject_P, right))
    _Py_DECREF_SPECIALIZED(right, rffi.cast(cpython.destructor, cpython.PyObject_Free))
    _Py_DECREF_SPECIALIZED(left, rffi.cast(cpython.destructor, cpython.PyObject_Free))
    if llop.ptr_iszero(lltype.Bool, res):
        return _pop_2_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    SET_SECOND(stack_pointer, res)
    STACK_SHRINK(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_binary_op_subtract_float(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(2))
    right = lltype.nullptr(cpython.PyObject)
    left = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    # _GUARD_BOTH_FLOAT
    right = TOP(stack_pointer)
    left = SECOND(stack_pointer)
    if not cpython.PyFloat_CheckExact(left):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    if not cpython.PyFloat_CheckExact(right):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    # Skip 1 cache entry
    # _BINARY_OP_SUBTRACT_FLOAT
    dres = _GET_FLOAT_OBJECT_VALUE(left) - _GET_FLOAT_OBJECT_VALUE(right)
    if llop.int_eq(lltype.Bool, cpython.Py_REFCNT(left), 1):
        _SET_FLOAT_OBJECT_VALUE(left, dres)
        _Py_DECREF_SPECIALIZED(right, _PyFloat_ExactDealloc)
        res = left
    elif llop.int_eq(lltype.Bool, cpython.Py_REFCNT(right), 1):
        _SET_FLOAT_OBJECT_VALUE(right, dres)
        _Py_DECREF_NO_DEALLOC(left)
        res = right
    else:
        res = cpython.PyFloat_FromDouble(dres)
        if llop.ptr_iszero(lltype.Bool, res):
            return _error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
        _Py_DECREF_NO_DEALLOC(left)
        _Py_DECREF_NO_DEALLOC(right)
    SET_SECOND(stack_pointer, res)
    STACK_SHRINK(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_binary_op_subtract_int(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(2))
    right = lltype.nullptr(cpython.PyObject)
    left = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    # _GUARD_BOTH_INT
    right = TOP(stack_pointer)
    left = SECOND(stack_pointer)
    if not cpython.PyLong_CheckExact(left):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    if not cpython.PyLong_CheckExact(right):
        return _predicted_binary_op(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    # Skip 1 cache entry
    # _BINARY_OP_SUBTRACT_INT
    res = _PyLong_Subtract(rffi.cast(cpython.PyLongObject_P, left), rffi.cast(cpython.PyLongObject_P, right))
    _Py_DECREF_SPECIALIZED(right, rffi.cast(cpython.destructor, cpython.PyObject_Free))
    _Py_DECREF_SPECIALIZED(left, rffi.cast(cpython.destructor, cpython.PyObject_Free))
    if llop.ptr_iszero(lltype.Bool, res):
        return _pop_2_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    SET_SECOND(stack_pointer, res)
    STACK_SHRINK(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_binary_slice(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(1))
    stop = lltype.nullptr(cpython.PyObject)
    start = lltype.nullptr(cpython.PyObject)
    container = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    stop = TOP(stack_pointer)
    start = SECOND(stack_pointer)
    container = THIRD(stack_pointer)
    # `_PyBuildSlice_ConsumeRefs` can't be used, the following error will be encoutered:
    # cpybooster_cpython313.obj : error LNK2019: unresolved external symbol __imp__PyBuildSlice_ConsumeRefs referenced in function pypy_g__dispatch_opcode
    # Use the public API `PySlice_New` instead.
    slice = cpython.PySlice_New(start, stop, cpython.Py_None)
    # `PySlice_New` does `Py_NewRef` for `start` and `stop`.
    # So we need to do `Py_DECREF` for `start` and `stop` as well.
    cpython.Py_DECREF(start)
    cpython.Py_DECREF(stop)
    # Can't use ERROR_IF() here, because we haven't
    # DECREF'ed container yet, and we still own slice.
    if llop.ptr_iszero(lltype.Bool, slice):
        res = lltype.nullptr(cpython.PyObject)
    else:
        res = cpython.PyObject_GetItem(container, slice)
        cpython.Py_DECREF(slice)
    cpython.Py_DECREF(container)
    if llop.ptr_iszero(lltype.Bool, res):
        return _pop_3_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    POKE(stack_pointer, r_int32(3), res)
    STACK_SHRINK(stack_pointer, r_int32(2))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(2))
    return _predicted_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _predicted_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    this_instr = _INSTR_PTR_SUB(next_instr, r_int32(2))
    sub = lltype.nullptr(cpython.PyObject)
    container = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    # _SPECIALIZE_BINARY_SUBSCR
    sub = TOP(stack_pointer)
    container = SECOND(stack_pointer)
    # _BIANRY_SUBSCR
    return _specialized_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer, this_instr, container, sub)


@always_inline
def _target_binary_subscr_dict(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(2))
    sub = lltype.nullptr(cpython.PyObject)
    dict = lltype.nullptr(cpython.PyObject)
    res = _INIT_PYOBJECT()
    # Skip 1 cache entry
    sub = TOP(stack_pointer)
    dict = SECOND(stack_pointer)
    if not cpython.PyDict_CheckExact(dict):
        return _predicted_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    rc = cpython.PyDict_GetItemRef(dict, sub, _PYOBJECT_ADDRESS(res))
    if llop.int_eq(lltype.Bool, rc, 0):
        _PyErr_SetKeyError(sub)
    cpython.Py_DECREF(dict)
    cpython.Py_DECREF(sub)
    if llop.int_le(lltype.Bool, rc, 0):
        return _pop_2_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    SET_SECOND(stack_pointer, res)
    STACK_SHRINK(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_binary_subscr_getitem(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    this_instr = next_instr
    next_instr = _INSTR_PTR_ADD(next_instr, r_int32(2))
    sub = lltype.nullptr(cpython.PyObject)
    container = lltype.nullptr(cpython.PyObject)
    # Skip 1 cache entry
    sub = TOP(stack_pointer)
    container = SECOND(stack_pointer)
    if llop.ptr_nonzero(lltype.Bool, _GET_EVAL_FRAME_FUNC(tstate)):
        return _predicted_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    tp = cpython.Py_TYPE(container)
    if not cpython.PyType_HasFeature(tp, cpython.Py_TPFLAGS_HEAPTYPE):
        return _predicted_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    ht = rffi.cast(cpython.PyHeapTypeObject_P, tp)
    cached = _GET_HEAP_GET_ITEM(ht)
    if llop.ptr_iszero(lltype.Bool, cached):
        return _predicted_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    getitem = rffi.cast(cpython.PyFunctionObject_P, cached)
    cached_version = _GET_HEAP_GET_ITEM_VERSION(ht)
    if llop.int_ne(lltype.Bool, getitem.c_func_version, cached_version):
        return _predicted_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    code = rffi.cast(cpython.PyCodeObject_P, getitem.c_func_code)
    if not _PyThreadState_HasStackSpace(tstate, code.c_co_framesize):
        return _predicted_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    cpython.Py_INCREF(cached)
    new_frame = _PyFrame_PushUnchecked(tstate, getitem, r_int32(2))
    STACK_SHRINK(stack_pointer, r_int32(2))
    _SET_FRAME_LOCALSPLUS(new_frame, r_int32(0), container)
    _SET_FRAME_LOCALSPLUS(new_frame, r_int32(1), sub)
    frame.c_return_offset = rffi.cast(rffi.USHORT, _INSTR_PTRS_SUB(next_instr, this_instr))
    _PyFrame_SetStackPointer(frame, stack_pointer)
    new_frame.c_previous = frame
    tstate.c_current_frame = new_frame
    frame = new_frame
    return _start_frame(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_binary_subscr_list_int(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(2))
    sub = lltype.nullptr(cpython.PyObject)
    list = lltype.nullptr(cpython.PyObject)
    res = lltype.nullptr(cpython.PyObject)
    # Skip 1 cache entry
    sub = TOP(stack_pointer)
    list = SECOND(stack_pointer)
    if not cpython.PyLong_CheckExact(sub):
        return _predicted_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    if not cpython.PyList_CheckExact(list):
        return _predicted_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    # Deopt unless 0 <= sub < PyList_Size(list)
    if not _PyLong_IsNonNegativeCompact(rffi.cast(cpython.PyLongObject_P, sub)):
        return _predicted_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    index = _GET_LONG_OBJECT_VALUE(sub)
    if llop.int_le(lltype.Bool, index, cpython.PyList_GET_SIZE(list)):
        return _predicted_binary_subscr(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    res = cpython.PyList_GET_ITEM(list, index)
    cpython.Py_INCREF(res)
    _Py_DECREF_SPECIALIZED(sub, rffi.cast(cpython.destructor, cpython.PyObject_Free))
    cpython.Py_DECREF(list)
    SET_SECOND(stack_pointer, res)
    STACK_SHRINK(stack_pointer, r_int32(1))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)


@always_inline
def _target_interpreter_exit(tstate, frame, entry_frame, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(1))
    retval = lltype.nullptr(cpython.PyObject)
    retval = TOP(stack_pointer)
    # Restore previous frame and return.
    tstate.c_current_frame = frame.c_previous
    tstate.c_c_recursion_remaining = llop.int_add(rffi.INT, tstate.c_c_recursion_remaining, PY_EVAL_C_STACK_UNITS)
    lltype.free(entry_frame, flavor="raw", track_allocation=False)
    return retval


@always_inline
def _target_store_slice(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer):
    frame.c_instr_ptr = next_instr
    _INSTR_PTR_INPLACE_ADD(next_instr, r_int32(1))
    stop = lltype.nullptr(cpython.PyObject)
    start = lltype.nullptr(cpython.PyObject)
    container = lltype.nullptr(cpython.PyObject)
    v = lltype.nullptr(cpython.PyObject)
    stop = TOP(stack_pointer)
    start = SECOND(stack_pointer)
    container = THIRD(stack_pointer)
    v = FOURTH(stack_pointer)
    # `_PyBuildSlice_ConsumeRefs` can't be used, the following error will be encoutered:
    # cpybooster_cpython313.obj : error LNK2019: unresolved external symbol __imp__PyBuildSlice_ConsumeRefs referenced in function pypy_g__dispatch_opcode
    # Use the public API `PySlice_New` instead.
    slice = cpython.PySlice_New(start, stop, cpython.Py_None)
    # `PySlice_New` does `Py_NewRef` for `start` and `stop`.
    # So we need to do `Py_DECREF` for `start` and `stop` as well.
    cpython.Py_DECREF(start)
    cpython.Py_DECREF(stop)
    err = _INT_DECLARE()
    if llop.ptr_iszero(lltype.Bool, slice):
        err = r_int32(1)
    else:
        err = cpython.PyObject_SetItem(container, slice, v)
        cpython.Py_DECREF(slice)
    cpython.Py_DECREF(v)
    cpython.Py_DECREF(container)
    if llop.int_is_true(lltype.Bool, err):
        return _pop_4_error(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
    STACK_SHRINK(stack_pointer, r_int32(4))
    DISPATCH(next_instr, opcode, oparg)
    return _dispatch_opcode(tstate, frame, entry_frame, opcode, oparg, next_instr, stack_pointer)
