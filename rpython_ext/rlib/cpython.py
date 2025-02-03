# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division

from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.tool import rffi_platform
from rpython_ext.tool.cpython_config import get_cpython_eci

_CPYTHON_VERSION_INFO, _ECI = get_cpython_eci()
_llextkws = {"compilation_info": _ECI, "_nowrapper": True}


class _CPyBasicConfig:
    """
    pyconfig.h
    patchlevel.h
    pyport.h
    """
    _compilation_info_ = _ECI

    # pyconfig.h
    Py_ssize_t = rffi_platform.SimpleType("Py_ssize_t", rffi.LONGLONG)
    PY_SSIZE_T_MAX = rffi_platform.DefinedConstantInteger("PY_SSIZE_T_MAX")
    pid_t = rffi_platform.SimpleType("pid_t", rffi.INT)

    # patchlevel.h
    PY_MAJOR_VERSION = rffi_platform.DefinedConstantInteger("PY_MAJOR_VERSION")
    PY_MINOR_VERSION = rffi_platform.DefinedConstantInteger("PY_MINOR_VERSION")
    PY_MICRO_VERSION = rffi_platform.DefinedConstantInteger("PY_MICRO_VERSION")
    PY_VERSION = rffi_platform.DefinedConstantString("PY_VERSION")

    # pyport.h
    Py_uintptr_t = rffi_platform.SimpleType("Py_uintptr_t", rffi.UINTPTR_T)
    Py_intptr_t = rffi_platform.SimpleType("Py_intptr_t", rffi.INTPTR_T)
    Py_hash_t = rffi_platform.SimpleType("Py_hash_t", rffi.LONGLONG)
    Py_uhash_t = rffi_platform.SimpleType("Py_uhash_t", rffi.SIZE_T)


config = rffi_platform.configure(_CPyBasicConfig)

Py_ssize_t = config["Py_ssize_t"]
PY_SSIZE_T_MAX = config["PY_SSIZE_T_MAX"]
pid_t = config["pid_t"]

PY_MAJOR_VERSION = config["PY_MAJOR_VERSION"]
PY_MINOR_VERSION = config["PY_MINOR_VERSION"]
PY_MICRO_VERSION = config["PY_MICRO_VERSION"]
PY_VERSION = config["PY_VERSION"]

Py_uintptr_t = config["Py_uintptr_t"]
Py_intptr_t = config["Py_intptr_t"]
Py_hash_t = config["Py_hash_t"]
Py_uhash_t = config["Py_uhash_t"]


class _CPyTypeObjectConfig:
    """
    pytypedefs.h
    """
    _compilation_info_ = _ECI

    PyTypeObject = rffi_platform.Struct(
        "PyTypeObject",
        [],
    )


config = rffi_platform.configure(_CPyTypeObjectConfig)
PyTypeObject = config["PyTypeObject"]
PyTypeObject_P = lltype.Ptr(PyTypeObject)


class _CPyObjectConfig:
    """
    object.h
    """
    _compilation_info_ = _ECI

    PyObject = rffi_platform.Struct(
        "PyObject",
        [
            ("ob_refcnt", Py_ssize_t),
            ("ob_type", PyTypeObject_P)
        ],
    )


config = rffi_platform.configure(_CPyObjectConfig)

PyObject = config["PyObject"]
PyObject_P = lltype.Ptr(PyObject)

# object.h
unaryfunc = lltype.Ptr(lltype.FuncType([PyObject_P], PyObject_P))
binaryfunc = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P], PyObject_P))
ternaryfunc = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P, PyObject_P], PyObject_P))
inquiry = lltype.Ptr(lltype.FuncType([PyObject_P], rffi.INT))
lenfunc = lltype.Ptr(lltype.FuncType([PyObject_P], Py_ssize_t))
ssizeargfunc = lltype.Ptr(lltype.FuncType([PyObject_P, Py_ssize_t], PyObject_P))
ssizessizeargfunc = lltype.Ptr(lltype.FuncType([PyObject_P, Py_ssize_t, Py_ssize_t], PyObject_P))
ssizeobjargproc = lltype.Ptr(lltype.FuncType([PyObject_P, Py_ssize_t, PyObject_P], rffi.INT))
ssizessizeobjargproc = lltype.Ptr(lltype.FuncType([PyObject_P, Py_ssize_t, Py_ssize_t, PyObject_P], rffi.INT))
objobjargproc = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P, PyObject_P], rffi.INT))

objobjproc = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P], rffi.INT))
visitproc = lltype.Ptr(lltype.FuncType([PyObject_P, rffi.VOIDP], rffi.INT))
traverseproc = lltype.Ptr(lltype.FuncType([PyObject_P, visitproc, rffi.VOIDP], rffi.INT))

freefunc = lltype.Ptr(lltype.FuncType([rffi.VOIDP], lltype.Void))
destructor = lltype.Ptr(lltype.FuncType([PyObject_P], lltype.Void))
getattrfunc = lltype.Ptr(lltype.FuncType([PyObject_P, rffi.CCHARP], PyObject_P))
getattrofunc = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P], PyObject_P))
setattrfunc = lltype.Ptr(lltype.FuncType([PyObject_P, rffi.CCHARP, PyObject_P], PyObject_P))
setattrofunc = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P, PyObject_P], PyObject_P))
reprfunc = lltype.Ptr(lltype.FuncType([PyObject_P], PyObject_P))
hashfunc = lltype.Ptr(lltype.FuncType([PyObject_P], Py_hash_t))
richcmpfunc = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P, rffi.INT], PyObject_P))
getiterfunc = lltype.Ptr(lltype.FuncType([PyObject_P], PyObject_P))
iternextfunc = lltype.Ptr(lltype.FuncType([PyObject_P], PyObject_P))
descrgetfunc = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P, PyObject_P], PyObject_P))
descrsetfunc = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P, PyObject_P], rffi.INT))
initproc = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P, PyObject_P], rffi.INT))
newfunc = lltype.Ptr(lltype.FuncType([PyTypeObject_P, PyObject_P, PyObject_P], PyObject_P))
allocfunc = lltype.Ptr(lltype.FuncType([PyTypeObject_P, Py_ssize_t], PyObject_P))

# methodobject.h
PyCFunction = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P], PyObject_P))
PyCFunctionWithKeywords = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P, PyObject_P], PyObject_P))


class _CPyMethodObjectConfig:
    """
    methodobject.h
    """
    _compilation_info_ = _ECI

    PyMethodDef = rffi_platform.Struct(
        "PyMethodDef",
        [
            ("ml_name", rffi.CONST_CCHARP),
            ("ml_meth", PyCFunction),
            ("ml_flags", rffi.INT),
            ("ml_doc", rffi.CONST_CCHARP),
        ]
    )
    METH_VARARGS = rffi_platform.DefinedConstantInteger("METH_VARARGS")
    METH_KEYWORDS = rffi_platform.DefinedConstantInteger("METH_KEYWORDS")
    METH_NOARGS = rffi_platform.DefinedConstantInteger("METH_NOARGS")
    METH_O = rffi_platform.DefinedConstantInteger("METH_O")
    METH_CLASS = rffi_platform.DefinedConstantInteger("METH_CLASS")
    METH_STATIC = rffi_platform.DefinedConstantInteger("METH_STATIC")
    METH_COEXIST = rffi_platform.DefinedConstantInteger("METH_COEXIST")


config = rffi_platform.configure(_CPyMethodObjectConfig)
PyMethodDef = config["PyMethodDef"]
METH_VARARGS = config["METH_VARARGS"]
METH_KEYWORDS = config["METH_KEYWORDS"]
METH_NOARGS = config["METH_NOARGS"]
METH_O = config["METH_O"]
METH_CLASS = config["METH_CLASS"]
METH_STATIC = config["METH_STATIC"]
METH_COEXIST = config["METH_COEXIST"]


# descrobject.h
getter = lltype.Ptr(lltype.FuncType([PyObject_P, rffi.VOIDP], PyObject_P))
setter = lltype.Ptr(lltype.FuncType([PyObject_P, PyObject_P, rffi.VOIDP], rffi.INT))


class _CPyDescriptorObjectConfig:
    """
    descrobject.h
    """
    _compilation_info_ = _ECI

    PyGetSetDef = rffi_platform.Struct(
        "PyGetSetDef",
        [
            ("name", rffi.CONST_CCHARP),
            ("get", getter),
            ("set", setter),
            ("doc", rffi.CONST_CCHARP),
            ("closure", rffi.VOIDP),
        ],
    )
    PyMemberDef = rffi_platform.Struct(
        "PyMemberDef",
        [
            ("name", rffi.CONST_CCHARP),
            ("type", rffi.INT),
            ("offset", Py_ssize_t),
            ("flags", rffi.INT),
            ("doc", rffi.CONST_CCHARP),
        ]
    )
    Py_T_SHORT = rffi_platform.DefinedConstantInteger("Py_T_SHORT")
    Py_T_INT = rffi_platform.DefinedConstantInteger("Py_T_INT")
    Py_T_LONG = rffi_platform.DefinedConstantInteger("Py_T_LONG")
    Py_T_FLOAT = rffi_platform.DefinedConstantInteger("Py_T_FLOAT")
    Py_T_DOUBLE = rffi_platform.DefinedConstantInteger("Py_T_DOUBLE")
    Py_T_STRING = rffi_platform.DefinedConstantInteger("Py_T_STRING")
    Py_T_CHAR = rffi_platform.DefinedConstantInteger("Py_T_CHAR")
    Py_T_BYTE = rffi_platform.DefinedConstantInteger("Py_T_BYTE")
    Py_T_UBYTE = rffi_platform.DefinedConstantInteger("Py_T_UBYTE")
    Py_T_USHORT = rffi_platform.DefinedConstantInteger("Py_T_USHORT")
    Py_T_UINT = rffi_platform.DefinedConstantInteger("Py_T_UINT")
    Py_T_ULONG = rffi_platform.DefinedConstantInteger("Py_T_ULONG")
    Py_T_STRING_INPLACE = rffi_platform.DefinedConstantInteger("Py_T_STRING_INPLACE")
    Py_T_BOOL = rffi_platform.DefinedConstantInteger("Py_T_BOOL")
    Py_T_OBJECT_EX = rffi_platform.DefinedConstantInteger("Py_T_OBJECT_EX")
    Py_T_LONGLONG = rffi_platform.DefinedConstantInteger("Py_T_LONGLONG")
    Py_T_ULONGLONG = rffi_platform.DefinedConstantInteger("Py_T_ULONGLONG")
    Py_T_PYSSIZET = rffi_platform.DefinedConstantInteger("Py_T_PYSSIZET")

    Py_READONLY = rffi_platform.DefinedConstantInteger("Py_READONLY")
    Py_AUDIT_READ = rffi_platform.DefinedConstantInteger("Py_AUDIT_READ")
    Py_RELATIVE_OFFSET = rffi_platform.DefinedConstantInteger("Py_RELATIVE_OFFSET")


config = rffi_platform.configure(_CPyDescriptorObjectConfig)
PyGetSetDef = config["PyGetSetDef"]
PyMemberDef = config["PyMemberDef"]
Py_T_SHORT = config["Py_T_SHORT"]
Py_T_INT = config["Py_T_INT"]
Py_T_LONG = config["Py_T_LONG"]
Py_T_FLOAT = config["Py_T_FLOAT"]
Py_T_DOUBLE = config["Py_T_DOUBLE"]
Py_T_STRING = config["Py_T_STRING"]
Py_T_CHAR = config["Py_T_CHAR"]
Py_T_BYTE = config["Py_T_BYTE"]
Py_T_UBYTE = config["Py_T_UBYTE"]
Py_T_USHORT = config["Py_T_USHORT"]
Py_T_UINT = config["Py_T_UINT"]
Py_T_ULONG = config["Py_T_ULONG"]
Py_T_STRING_INPLACE = config["Py_T_STRING_INPLACE"]
Py_T_BOOL = config["Py_T_BOOL"]
Py_T_OBJECT_EX = config["Py_T_OBJECT_EX"]
Py_T_LONGLONG = config["Py_T_LONGLONG"]
Py_T_ULONGLONG = config["Py_T_ULONGLONG"]
Py_T_PYSSIZET = config["Py_T_PYSSIZET"]
Py_READONLY = config["Py_READONLY"]
Py_AUDIT_READ = config["Py_AUDIT_READ"]
Py_RELATIVE_OFFSET = config["Py_RELATIVE_OFFSET"]


class _CPyTypeMethodConfig:
    """
    cpython/object.h
    """
    _compilation_info_ = _ECI

    PyNumberMethods = rffi_platform.Struct(
        "PyNumberMethods",
        [
            ("nb_add", binaryfunc),
            ("nb_subtract", binaryfunc),
            ("nb_multiply", binaryfunc),
            ("nb_remainder", binaryfunc),
            ("nb_divmod", binaryfunc),
            ("nb_power", ternaryfunc),
            ("nb_negative", unaryfunc),
            ("nb_positive", unaryfunc),
            ("nb_absolute", unaryfunc),
            ("nb_bool", inquiry),
            ("nb_invert", unaryfunc),
            ("nb_lshift", binaryfunc),
            ("nb_rshift", binaryfunc),
            ("nb_and", binaryfunc),
            ("nb_xor", binaryfunc),
            ("nb_or", binaryfunc),
            ("nb_int", unaryfunc),
            ("nb_reserved", rffi.VOIDP),
            ("nb_float", unaryfunc),

            ("nb_inplace_add", binaryfunc),
            ("nb_inplace_subtract", binaryfunc),
            ("nb_inplace_multiply", binaryfunc),
            ("nb_inplace_remainder", binaryfunc),
            ("nb_inplace_power", ternaryfunc),
            ("nb_inplace_lshift", binaryfunc),
            ("nb_inplace_rshift", binaryfunc),
            ("nb_inplace_and", binaryfunc),
            ("nb_inplace_xor", binaryfunc),
            ("nb_inplace_or", binaryfunc),

            ("nb_floor_divide", binaryfunc),
            ("nb_true_divide", binaryfunc),
            ("nb_inplace_floor_divide", binaryfunc),
            ("nb_inplace_true_divide", binaryfunc),

            ("nb_index", unaryfunc),

            ("nb_matrix_multiply", binaryfunc),
            ("nb_inplace_matrix_multiply", binaryfunc),
        ]
    )
    PySequenceMethods = rffi_platform.Struct(
        "PySequenceMethods",
        [
            ("sq_length", lenfunc),
            ("sq_concat", binaryfunc),
            ("sq_repeat", ssizeargfunc),
            ("sq_item", ssizeargfunc),
            ("was_sq_slice", rffi.VOIDP),
            ("sq_ass_item", ssizeobjargproc),
            ("was_sq_ass_slice", rffi.VOIDP),
            ("sq_contains", objobjproc),

            ("sq_inplace_concat", binaryfunc),
            ("sq_inplace_repeat", ssizeargfunc),
        ]
    )
    PyMappingMethods = rffi_platform.Struct(
        "PyMappingMethods",
        [
            ("mp_length", lenfunc),
            ("mp_subscript", binaryfunc),
            ("mp_ass_subscript", objobjargproc),
        ]
    )
    printfunc = rffi_platform.SimpleType("printfunc", Py_ssize_t)



config = rffi_platform.configure(_CPyTypeMethodConfig)
PyNumberMethods = config["PyNumberMethods"]
PySequenceMethods = config["PySequenceMethods"]
PyMappingMethods = config["PyMappingMethods"]
printfunc = config["printfunc"]


class _CPyTypeObjectConfig:
    """
    cpython/object.h
    """
    _compilation_info_ = _ECI

    PyTypeObject = rffi_platform.Struct(
        "PyTypeObject",
        [
            ("tp_name", rffi.CONST_CCHARP),
            ("tp_basicsize", Py_ssize_t),
            ("tp_itemsize", Py_ssize_t),

            ("tp_dealloc", destructor),
            ("tp_vectorcall_offset", Py_ssize_t),
            ("tp_getattr", getattrfunc),
            ("tp_setattr", setattrfunc),
            ("tp_repr", reprfunc),

            ("tp_as_number", lltype.Ptr(PyNumberMethods)),
            ("tp_as_sequence", lltype.Ptr(PySequenceMethods)),
            ("tp_as_mapping", lltype.Ptr(PyMappingMethods)),

            ("tp_hash", hashfunc),
            ("tp_call", ternaryfunc),
            ("tp_str", reprfunc),
            ("tp_getattro", getattrofunc),
            ("tp_setattro", setattrofunc),

            ("tp_flags", rffi.ULONG),

            ("tp_doc", rffi.CONST_CCHARP),

            ("tp_traverse", traverseproc),

            ("tp_clear", inquiry),

            ("tp_richcompare", richcmpfunc),

            ("tp_weaklistoffset", Py_ssize_t),

            ("tp_iter", getiterfunc),
            ("tp_iternext", iternextfunc),

            ("tp_methods", lltype.Ptr(PyMethodDef)),
            ("tp_members", lltype.Ptr(PyMemberDef)),
            ("tp_getset", lltype.Ptr(PyGetSetDef)),

            ("tp_base", PyTypeObject_P),
            ("tp_dict", PyObject_P),
            ("tp_descr_get", descrgetfunc),
            ("tp_descr_set", descrsetfunc),
            ("tp_dictoffset", Py_ssize_t),
            ("tp_init", initproc),
            ("tp_alloc", allocfunc),
            ("tp_new", newfunc),
            ("tp_free", freefunc),
            ("tp_is_gc", inquiry),
            ("tp_bases", PyObject_P),
            ("tp_mro", PyObject_P),
            ("tp_cache", PyObject_P),
            ("tp_subclasses", rffi.VOIDP),
            ("tp_weaklist", PyObject_P),
            ("tp_del", destructor),

            ("tp_version_tag", rffi.UINT),

            ("tp_finalize", destructor),
        ],
    )


config = rffi_platform.configure(_CPyTypeObjectConfig)
PyTypeObject = config["PyTypeObject"]
PyTypeObject_P = lltype.Ptr(PyTypeObject)


class _CPyModuleObjectConfig:
    """
    moduleobject.h
    """
    _compilation_info_ = _ECI

    PyModuleDef_Base = rffi_platform.Struct(
        "PyModuleDef_Base",
        [
            ("m_init", lltype.Ptr(lltype.FuncType([], PyObject_P))),
            ("m_index", Py_ssize_t),
            ("m_copy", PyObject_P),
        ]
    )

    if _CPYTHON_VERSION_INFO >= (3, 5):
        PyModuelDef_Slot = rffi_platform.Struct(
            "PyModuleDef_Slot",
            [
                ("slot", rffi.INT),
                ("value", rffi.VOIDP),
            ]
        )


config = rffi_platform.configure(_CPyModuleObjectConfig)
PyModuleDef_Base = config["PyModuleDef_Base"]
if _CPYTHON_VERSION_INFO >= (3, 5):
    PyModuelDef_Slot = config["PyModuelDef_Slot"]


class _CPyModuleObjectConfig:
    """
    moduleobject.h
    """
    _compilation_info_ = _ECI

    PyModuleDef = rffi_platform.Struct(
        "PyModuleDef",
        [
            ("m_base", PyModuleDef_Base),
            ("m_name", rffi.CONST_CCHARP),
            ("m_doc", rffi.CONST_CCHARP),
            ("m_size", Py_ssize_t),
            ("m_methods", lltype.Ptr(PyMethodDef)),
            ("m_traverse", traverseproc),
            ("m_clear", inquiry),
            ("m_free", freefunc),
        ]
    )
    if _CPYTHON_VERSION_INFO >= (3, 5):
        PyModuleDef.interesting_fields.append(
            ("m_slots", lltype.Ptr(PyModuelDef_Slot))
        )


config = rffi_platform.configure(_CPyModuleObjectConfig)
PyModuleDef = config["PyModuleDef"]
PyModuleDef_P = lltype.Ptr(PyModuleDef)


class _CPyCodeObjectConfig:
    """
    cpython/code.h
    """
    _compilation_info_ = _ECI

    PyCodeObject = rffi_platform.Struct(
        "PyCodeObject",
        [
            ("co_consts", PyObject_P),
            ("co_names", PyObject_P),
            ("co_exceptiontable", PyObject_P),

            ("co_flags", rffi.INT),

            ("co_argcount", rffi.INT),
            ("co_posonlyargcount", rffi.INT),
            ("co_kwonlyargcount", rffi.INT),
            ("co_stacksize", rffi.INT),
            ("co_firstlineno", rffi.INT),

            ("co_nlocalsplus", rffi.INT),
            ("co_framesize", rffi.INT),
            ("co_nlocals", rffi.INT),
            ("co_ncellvars", rffi.INT),
            ("co_nfreevars", rffi.INT),
            ("co_version", rffi.INT),

            ("co_localsplusnames", PyObject_P),
            ("co_localspluskinds", PyObject_P),
            ("co_filename", PyObject_P),
            ("co_name", PyObject_P),
            ("co_qualname", PyObject_P),
            ("co_linetable", PyObject_P),
            ("co_weakreflist", PyObject_P),
        ]
    )


config = rffi_platform.configure(_CPyCodeObjectConfig)
PyCodeObject = config["PyCodeObject"]
PyCodeObject_P = lltype.Ptr(PyCodeObject)

_PyInterpreterFrame = lltype.ForwardReference()
_PyInterpreterFrame_P = lltype.Ptr(_PyInterpreterFrame)
PyFrameObject = lltype.ForwardReference()
PyFrameObject_P = lltype.Ptr(PyFrameObject)

_FRAME_ECI = ExternalCompilationInfo(
    pre_include_bits=_ECI.pre_include_bits,
    post_include_bits=[
        "#ifndef Py_BUILD_CORE",
        "#define Py_BUILD_CORE",
        "#endif",
        "#include <internal/pycore_frame.h>",
        "#undef Py_BUILD_CORE",
    ],
    includes=_ECI.includes,
    include_dirs=_ECI.include_dirs,
    libraries=_ECI.libraries,
    library_dirs=_ECI.library_dirs,
)


class _CPyFrameObjectConfig:
    """
    internal/pycore_frame.h
    """
    _compilation_info_ = _FRAME_ECI

    PyFrameObject = rffi_platform.Struct(
        "PyFrameObject",
        [
            ("f_back", PyFrameObject_P),
            ("f_frame", _PyInterpreterFrame_P),
            ("f_trace", PyObject_P),
            ("f_lineno", rffi.INT),
            ("f_trace_lines", rffi.CHAR),
            ("f_trace_opcodes", rffi.CHAR),
        ]
    )

    _PyInterpreterFrame = rffi_platform.Struct(
        "_PyInterpreterFrame",
        [
            ("previous", _PyInterpreterFrame_P),
            ("f_funcobj", PyObject_P),
            ("f_globals", PyObject_P),
            ("f_builtins", PyObject_P),
            ("f_locals", PyObject_P),
            ("frame_obj", PyFrameObject_P),
            ("stacktop", rffi.INT),
            ("return_offset", rffi.USHORT),
            ("owner", rffi.CHAR),
        ]
    )


config = rffi_platform.configure(_CPyFrameObjectConfig)
_PyInterpreterFrame.become(config["_PyInterpreterFrame"])
_PyInterpreterFrame_P = lltype.Ptr(_PyInterpreterFrame)
PyFrameObject.become(config["PyFrameObject"])
PyFrameObject_P = lltype.Ptr(PyFrameObject)


class _CPyThreadStateConfig:
    """
    cpython/pystate.h
    """
    _compilation_info_ = _ECI

    PyThreadState = rffi_platform.Struct(
        "PyThreadState",
        []
    )


config = rffi_platform.configure(_CPyThreadStateConfig)
PyThreadState = config["PyThreadState"]


# cpython/pystate.h
Py_tracefunc = lltype.Ptr(lltype.FuncType([PyObject_P, PyFrameObject_P, rffi.INT, PyObject_P], rffi.INT))


class _CPyThreadStateConfig:
    """
    cpython/pystate.h
    """
    _compilation_info_ = _ECI

    PyThreadState = rffi_platform.Struct(
        "PyThreadState",
        [
            ("prev", lltype.Ptr(PyThreadState)),
            ("next", lltype.Ptr(PyThreadState)),

            ("py_recursion_remaining", rffi.INT),
            ("py_recursion_limit", rffi.INT),

            ("c_recursion_remaining", rffi.INT),
            ("recursion_headroom", rffi.INT),

            ("tracing", rffi.INT),
            ("what_event", rffi.INT),

            ("c_profilefunc", Py_tracefunc),
            ("c_tracefunc", Py_tracefunc),

            ("c_profileobj", PyObject_P),
            ("c_traceobj", PyObject_P),

            ("current_exception", PyObject_P),
        ]
    )


config = rffi_platform.configure(_CPyThreadStateConfig)
PyThreadState = config["PyThreadState"]
PyThreadState_P = lltype.Ptr(PyThreadState)

# Functions in: pystate.h
PyState_AddModule = rffi.llexternal("PyState_AddModule", [PyObject_P, PyModuleDef_P], rffi.INT, **_llextkws)
PyState_RemoveModule = rffi.llexternal("PyState_RemoveModule", [PyModuleDef_P], rffi.INT, **_llextkws)
PyState_FindModule = rffi.llexternal("PyState_FindModule", [PyModuleDef_P], PyObject_P, **_llextkws)
PyThreadState_Clear = rffi.llexternal("PyThreadState_Clear", [PyThreadState_P], lltype.Void, **_llextkws)
PyThreadState_Delete = rffi.llexternal("PyThreadState_Delete", [PyThreadState_P], lltype.Void, **_llextkws)
PyThreadState_Get = rffi.llexternal("PyThreadState_Get", [], PyThreadState_P, **_llextkws)

_PyFrameEvalFunction = lltype.Ptr(lltype.FuncType([PyThreadState_P, _PyInterpreterFrame_P, rffi.INT], PyObject_P))

PyInterpreterState = lltype.Struct("PyInterpreterState", hints={"typedef": True, "external": "C", "c_name": "PyInterpreterState", "eci": _ECI})
PyInterpreterState_P = lltype.Ptr(PyInterpreterState)


PyInterpreterState_Get = rffi.llexternal("PyInterpreterState_Get", [], PyInterpreterState_P, **_llextkws)
_PyInterpreterState_SetEvalFrameFunc = rffi.llexternal("_PyInterpreterState_SetEvalFrameFunc", [PyInterpreterState_P, _PyFrameEvalFunction], lltype.Void, **_llextkws)
_PyInterpreterState_GetEvalFrameFunc = rffi.llexternal("_PyInterpreterState_GetEvalFrameFunc", [PyInterpreterState_P], _PyFrameEvalFunction, **_llextkws)

# Functions in: longobject.h
PyLong_FromLong = rffi.llexternal("PyLong_FromLong", [rffi.LONG], PyObject_P, **_llextkws)
PyLong_AsLong = rffi.llexternal("PyLong_AsLong", [PyObject_P], rffi.LONG, **_llextkws)

del config
 