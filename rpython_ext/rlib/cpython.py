# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division
import inspect

from rpython.rlib.objectmodel import not_rpython
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.tool import rffi_platform
from rpython_ext.rlib import rdtoa  # Keep it to replace pypy's dtoa
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

    # unicodeobject.h
    Py_UCS4 = rffi_platform.SimpleType("Py_UCS4", rffi.UINT)
    Py_UCS2 = rffi_platform.SimpleType("Py_UCS4", rffi.USHORT)
    Py_UCS1 = rffi_platform.SimpleType("Py_UCS4", rffi.UCHAR)


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

Py_UCS4 = config["Py_UCS4"]
Py_UCS2 = config["Py_UCS2"]
Py_UCS1 = config["Py_UCS1"]

# pymacro.h
Py_UNREACHABLE = rffi.llexternal("Py_UNREACHABLE", [], lltype.Void, **_llextkws)


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

Py_REFCNT = rffi.llexternal("Py_REFCNT", [PyObject_P], rffi.INT, **_llextkws)
Py_INCREF = rffi.llexternal("Py_INCREF", [PyObject_P], lltype.Void, **_llextkws)
Py_DECREF = rffi.llexternal("Py_DECREF", [PyObject_P], lltype.Void, **_llextkws)
Py_XINCREF = rffi.llexternal("Py_XINCREF", [PyObject_P], lltype.Void, **_llextkws)
Py_XDECREF = rffi.llexternal("Py_XDECREF", [PyObject_P], lltype.Void, **_llextkws)


class _CPyLongObjectConfig:
    """
    pytypedefs.h
    """
    _compilation_info_ = _ECI

    PyLongObject = rffi_platform.Struct(
        "PyLongObject",
        [],
    )


config = rffi_platform.configure(_CPyLongObjectConfig)

PyLongObject = config["PyLongObject"]
PyLongObject_P = lltype.Ptr(PyLongObject)

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

Py_TYPE = rffi.llexternal("Py_TYPE", [PyObject_P], PyTypeObject_P, **_llextkws)

# abstract.h
PyObject_CallNoArgs = rffi.llexternal("PyObject_CallNoArgs", [PyObject_P], PyObject_P, **_llextkws)
PyObject_GetItem = rffi.llexternal("PyObject_GetItem", [PyObject_P, PyObject_P], PyObject_P, **_llextkws)
PyObject_SetItem = rffi.llexternal("PyObject_SetItem", [PyObject_P, PyObject_P, PyObject_P], rffi.INT, **_llextkws)


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


class _CPyFunctionObjectConfig:
    """
    cpython/funcobject.h
    """
    _compilation_info_ = _ECI

    PyFunctionObject = rffi_platform.Struct(
        "PyFunctionObject",
        [
            ("func_globals", PyObject_P),
            ("func_builtins", PyObject_P),
            ("func_name", PyObject_P),
            ("func_qualname", PyObject_P),
            ("func_code", PyObject_P),
            ("func_defaults", PyObject_P),
            ("func_kwdefaults", PyObject_P),
            ("func_closure", PyObject_P),
            ("func_doc", PyObject_P),
            ("func_dict", PyObject_P),
            ("func_weakreflist", PyObject_P),
            ("func_module", PyObject_P),
            ("func_version", rffi.UINT),
        ]
    )
    PyHeapTypeObject = rffi_platform.Struct(
        "PyHeapTypeObject",
        [
            ("ht_name", PyObject_P),
            ("ht_slots", PyObject_P),
            ("ht_qualname", PyObject_P),
            ("ht_module", PyObject_P),
        ]
    )


config = rffi_platform.configure(_CPyFunctionObjectConfig)
PyFunctionObject = config["PyFunctionObject"]
PyFunctionObject_P = lltype.Ptr(PyFunctionObject)
PyHeapTypeObject = config["PyHeapTypeObject"]
PyHeapTypeObject_P = lltype.Ptr(PyHeapTypeObject)

# objimpl.h
PyObject_Malloc = rffi.llexternal("PyObject_Malloc", [rffi.SIZE_T], rffi.VOIDP, **_llextkws)
PyObject_Realloc = rffi.llexternal("PyObject_Realloc", [rffi.VOIDP, rffi.SIZE_T], rffi.VOIDP, **_llextkws)
PyObject_Free = rffi.llexternal("PyObject_Free", [rffi.VOIDP], lltype.Void, **_llextkws)
PyObject_MALLOC = rffi.llexternal("PyObject_MALLOC", [rffi.SIZE_T], rffi.VOIDP, **_llextkws)
PyObject_REALLOC = rffi.llexternal("PyObject_REALLOC", [rffi.VOIDP, rffi.SIZE_T], rffi.VOIDP, **_llextkws)
PyObject_FREE = rffi.llexternal("PyObject_FREE", [rffi.VOIDP], lltype.Void, **_llextkws)
PyObject_Del = rffi.llexternal("PyObject_Del", [rffi.VOIDP], lltype.Void, **_llextkws)
PyObject_DEL = rffi.llexternal("PyObject_DEL", [rffi.VOIDP], lltype.Void, **_llextkws)

_Py_CODEUNIT__InnerStruct = rffi.CStruct("", ("code", rffi.UCHAR), ("arg", rffi.UCHAR), hints={"typedef": False, "external": "C", "c_name": "", "eci": _ECI, "size": 2})
if PY_MAJOR_VERSION == 3 and PY_MINOR_VERSION == 12:
    _Py_CODEUNIT = lltype.ForwardReference()


class _CPyCodeObjectConfig:
    """
    cpython/code.h
    """
    _compilation_info_ = _ECI

    if PY_MAJOR_VERSION == 3 and PY_MINOR_VERSION == 12:
        _Py_CODEUNIT = rffi_platform.Struct(
            "_Py_CODEUNIT",
            [
            ]
        )
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
if PY_MAJOR_VERSION == 3 and PY_MINOR_VERSION == 12:
    _Py_CODEUNIT.become(config["_Py_CODEUNIT"])
    _Py_CODEUNIT_P = lltype.Ptr(_Py_CODEUNIT)
else:
    _Py_CODEUNIT = lltype.ForwardReference()
    _Py_CODEUNIT_P = lltype.Ptr(_Py_CODEUNIT)

_PyInterpreterFrame = lltype.ForwardReference()
_PyInterpreterFrame_P = lltype.Ptr(_PyInterpreterFrame)
PyFrameObject = lltype.ForwardReference()
PyFrameObject_P = lltype.Ptr(PyFrameObject)


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


_CODE_ECI = ExternalCompilationInfo(
    pre_include_bits=_ECI.pre_include_bits,
    post_include_bits=[
        _unique_str("#ifndef Py_BUILD_CORE"),
        _unique_str("#define Py_BUILD_CORE"),
        _unique_str("#endif"),
        _unique_str("#include <internal/pycore_code.h>"),
        _unique_str("#ifdef Py_BUILD_CORE"),
        _unique_str("#undef Py_BUILD_CORE"),
        _unique_str("#endif"),
    ],
    includes=_ECI.includes,
    include_dirs=_ECI.include_dirs,
    libraries=_ECI.libraries,
    library_dirs=_ECI.library_dirs,
)


class _CPyCodeConfig:
    """
    internal/pycore_code.h
    """
    _compilation_info_ = _CODE_ECI

    ENABLE_SPECIALIZATION = rffi_platform.DefinedConstantInteger("ENABLE_SPECIALIZATION")


config = rffi_platform.configure(_CPyCodeConfig)
ENABLE_SPECIALIZATION = config["ENABLE_SPECIALIZATION"]


_FRAME_ECI = ExternalCompilationInfo(
    pre_include_bits=_ECI.pre_include_bits,
    post_include_bits=[
        _unique_str("#ifndef Py_BUILD_CORE"),
        _unique_str("#define Py_BUILD_CORE"),
        _unique_str("#endif"),
        _unique_str("#include <internal/pycore_frame.h>"),
        _unique_str("#ifdef Py_BUILD_CORE"),
        _unique_str("#undef Py_BUILD_CORE"),
        _unique_str("#endif"),
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

    if PY_MAJOR_VERSION == 3 and PY_MINOR_VERSION == 13:
        _PyInterpreterFrame = rffi_platform.Struct(
            "_PyInterpreterFrame",
            [
                ("f_executable", PyObject_P),  # Strong reference (code object or None)
                ("previous", _PyInterpreterFrame_P),
                ("f_funcobj", PyObject_P),  # Strong reference. Only valid if not on C stack
                ("f_globals", PyObject_P),  # Borrowed reference. Only valid if not on C stack
                ("f_builtins", PyObject_P),  # Borrowed reference. Only valid if not on C stack
                ("f_locals", PyObject_P),  # Strong reference, may be NULL. Only valid if not on C stack
                ("frame_obj", PyFrameObject_P),  # Strong reference, may be NULL. Only valid if not on C stack
                ("instr_ptr", _Py_CODEUNIT_P),  # Instruction currently executing (or about to begin)
                ("stacktop", rffi.INT),  # Offset of TOS from localsplus
                ("return_offset", rffi.USHORT),  # Only relevant during a function call
                ("owner", rffi.CHAR),
            ]
        )

        FRAME_OWNED_BY_THREAD = rffi_platform.ConstantInteger("FRAME_OWNED_BY_THREAD")
        FRAME_OWNED_BY_GENERATOR = rffi_platform.ConstantInteger("FRAME_OWNED_BY_GENERATOR")
        FRAME_OWNED_BY_FRAME_OBJECT = rffi_platform.ConstantInteger("FRAME_OWNED_BY_FRAME_OBJECT")
        FRAME_OWNED_BY_CSTACK = rffi_platform.ConstantInteger("FRAME_OWNED_BY_CSTACK")
        # internal/pycore_code.h
        _Py_CODEUNIT = rffi_platform.Struct(
            "_Py_CODEUNIT",
            [
                ("op", _Py_CODEUNIT__InnerStruct),
            ]
        )
    elif PY_MAJOR_VERSION == 3 and PY_MINOR_VERSION == 12:
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
if PY_MAJOR_VERSION == 3 and PY_MINOR_VERSION == 13:
    _Py_CODEUNIT.become(config["_Py_CODEUNIT"])
    _Py_CODEUNIT._hints["union"] = True
    _Py_CODEUNIT_P = lltype.Ptr(_Py_CODEUNIT)
    FRAME_OWNED_BY_THREAD = config["FRAME_OWNED_BY_THREAD"]
    FRAME_OWNED_BY_GENERATOR = config["FRAME_OWNED_BY_GENERATOR"]
    FRAME_OWNED_BY_FRAME_OBJECT = config["FRAME_OWNED_BY_FRAME_OBJECT"]
    FRAME_OWNED_BY_CSTACK = config["FRAME_OWNED_BY_CSTACK"]


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

PyInterpreterState = rffi.CStruct("PyInterpreterState", hints={"typedef": True, "external": "C", "c_name": "PyInterpreterState", "eci": _ECI})
PyInterpreterState_P = lltype.Ptr(PyInterpreterState)


class _CPyThreadStateConfig:
    """
    cpython/pystate.h
    """
    _compilation_info_ = _ECI

    if PY_MAJOR_VERSION == 3 and PY_MINOR_VERSION == 13:
        PyThreadState = rffi_platform.Struct(
            "PyThreadState",
            [
                ("prev", lltype.Ptr(PyThreadState)),
                ("next", lltype.Ptr(PyThreadState)),
                ("interp", PyInterpreterState_P),

                ("state", rffi.INT),

                ("py_recursion_remaining", rffi.INT),
                ("py_recursion_limit", rffi.INT),

                ("c_recursion_remaining", rffi.INT),
                ("recursion_headroom", rffi.INT),

                ("tracing", rffi.INT),
                ("what_event", rffi.INT),

                ("c_profilefunc", Py_tracefunc),
                ("c_tracefunc", Py_tracefunc),

                ("current_frame", _PyInterpreterFrame_P),

                ("c_profileobj", PyObject_P),
                ("c_traceobj", PyObject_P),

                ("current_exception", PyObject_P),
            ]
        )
    elif PY_MAJOR_VERSION == 3 and PY_MINOR_VERSION == 12:
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
_PyThreadState_PopFrame = rffi.llexternal("_PyThreadState_PopFrame", [PyThreadState_P, _PyInterpreterFrame_P], lltype.Void, **_llextkws)

_PyFrameEvalFunction = lltype.Ptr(lltype.FuncType([PyThreadState_P, _PyInterpreterFrame_P, rffi.INT], PyObject_P))


PyInterpreterState_Get = rffi.llexternal("PyInterpreterState_Get", [], PyInterpreterState_P, **_llextkws)
_PyInterpreterState_SetEvalFrameFunc = rffi.llexternal("_PyInterpreterState_SetEvalFrameFunc", [PyInterpreterState_P, _PyFrameEvalFunction], lltype.Void, **_llextkws)
_PyInterpreterState_GetEvalFrameFunc = rffi.llexternal("_PyInterpreterState_GetEvalFrameFunc", [PyInterpreterState_P], _PyFrameEvalFunction, **_llextkws)

# Functions in: object.h
PyType_HasFeature = rffi.llexternal("PyType_HasFeature", [PyTypeObject_P, rffi.ULONG], lltype.Bool, **_llextkws)

# Functions in: longobject.h
PyLong_Check = rffi.llexternal("PyLong_Check", [PyObject_P], lltype.Bool, **_llextkws)
PyLong_CheckExact = rffi.llexternal("PyLong_CheckExact", [PyObject_P], lltype.Bool, **_llextkws)
PyLong_FromLong = rffi.llexternal("PyLong_FromLong", [rffi.LONG], PyObject_P, **_llextkws)
PyLong_AsLong = rffi.llexternal("PyLong_AsLong", [PyObject_P], rffi.LONG, **_llextkws)

# Functions in floatobject.h
PyFloat_Check = rffi.llexternal("PyFloat_Check", [PyObject_P], lltype.Bool, **_llextkws)
PyFloat_CheckExact = rffi.llexternal("PyFloat_CheckExact", [PyObject_P], lltype.Bool, **_llextkws)
PyFloat_FromDouble = rffi.llexternal("PyFloat_FromDouble", [lltype.Float], PyObject_P, **_llextkws)

# Functions in unicodeobject.h
PyUnicode_Check = rffi.llexternal("PyUnicode_Check", [PyObject_P], lltype.Bool, **_llextkws)
PyUnicode_CheckExact = rffi.llexternal("PyUnicode_CheckExact", [PyObject_P], lltype.Bool, **_llextkws)
PyUnicode_FromStringAndSize = rffi.llexternal("PyUnicode_FromStringAndSize", [rffi.CONST_CCHARP, Py_ssize_t], PyObject_P, **_llextkws)
PyUnicode_FromString = rffi.llexternal("PyUnicode_FromString", [rffi.CONST_CCHARP], PyObject_P, **_llextkws)
PyUnicode_Resize = rffi.llexternal("PyUnicode_Resize", [PyObject_P, Py_ssize_t], rffi.INT, **_llextkws)
PyUnicode_FromEncodedObject = rffi.llexternal("PyUnicode_FromEncodedObject", [PyObject_P, rffi.CONST_CCHARP, rffi.CONST_CCHARP], PyObject_P, **_llextkws)
PyUnicode_FromObject = rffi.llexternal("PyUnicode_FromObject", [PyObject_P], PyObject_P, **_llextkws)
PyUnicode_Concat = rffi.llexternal("PyUnicode_Concat", [PyObject_P, PyObject_P], PyObject_P, **_llextkws)
PyUnicode_Append = rffi.llexternal("PyUnicode_Append", [rffi.CArrayPtr(PyObject_P), PyObject_P], lltype.Void, **_llextkws)
PyUnicode_AppendAndDel = rffi.llexternal("PyUnicode_AppendAndDel", [rffi.CArrayPtr(PyObject_P), PyObject_P], lltype.Void, **_llextkws)
PyUnicode_Split = rffi.llexternal("PyUnicode_Split", [PyObject_P, PyObject_P, Py_ssize_t], PyObject_P, **_llextkws)
PyUnicode_Splitlines = rffi.llexternal("PyUnicode_Splitlines", [PyObject_P, rffi.INT], PyObject_P, **_llextkws)
PyUnicode_Partition = rffi.llexternal("PyUnicode_Partition", [PyObject_P, PyObject_P], PyObject_P, **_llextkws)
PyUnicode_RPartition = rffi.llexternal("PyUnicode_RPartition", [PyObject_P, PyObject_P], PyObject_P, **_llextkws)
PyUnicode_RSplit = rffi.llexternal("PyUnicode_RSplit", [PyObject_P, PyObject_P, Py_ssize_t], PyObject_P, **_llextkws)
PyUnicode_Translate = rffi.llexternal("PyUnicode_Translate", [PyObject_P, PyObject_P, rffi.CONST_CCHARP], PyObject_P, **_llextkws)
PyUnicode_Join = rffi.llexternal("PyUnicode_Join", [PyObject_P, PyObject_P], PyObject_P, **_llextkws)
PyUnicode_Tailmatch = rffi.llexternal("PyUnicode_Tailmatch", [PyObject_P, PyObject_P, Py_ssize_t, Py_ssize_t, rffi.INT], Py_ssize_t, **_llextkws)
PyUnicode_Find = rffi.llexternal("PyUnicode_Find", [PyObject_P, PyObject_P, Py_ssize_t, Py_ssize_t, rffi.INT], Py_ssize_t, **_llextkws)
PyUnicode_Count = rffi.llexternal("PyUnicode_Count", [PyObject_P, PyObject_P, Py_ssize_t, Py_ssize_t], Py_ssize_t, **_llextkws)
PyUnicode_Replace = rffi.llexternal("PyUnicode_Replace", [PyObject_P, PyObject_P, PyObject_P, Py_ssize_t], PyObject_P, **_llextkws)
PyUnicode_Compare = rffi.llexternal("PyUnicode_Compare", [PyObject_P, PyObject_P], rffi.INT, **_llextkws)
PyUnicode_CompareWithASCIIString = rffi.llexternal("PyUnicode_CompareWithASCIIString", [PyObject_P, rffi.CONST_CCHARP], rffi.INT, **_llextkws)
PyUnicode_RichCompare = rffi.llexternal("PyUnicode_RichCompare", [PyObject_P, PyObject_P, rffi.INT], PyObject_P, **_llextkws)
PyUnicode_Format = rffi.llexternal("PyUnicode_Format", [PyObject_P, PyObject_P], PyObject_P, **_llextkws)
PyUnicode_Contains = rffi.llexternal("PyUnicode_Contains", [PyObject_P, PyObject_P], rffi.INT, **_llextkws)
PyUnicode_IsIdentifier = rffi.llexternal("PyUnicode_IsIdentifier", [PyObject_P], rffi.INT, **_llextkws)
# Functions in cpython/unicodeobject.h
PyUnicode_GET_LENGTH = rffi.llexternal("PyUnicode_GET_LENGTH", [PyObject_P], Py_ssize_t, **_llextkws)
PyUnicode_READ_CHAR = rffi.llexternal("PyUnicode_READ_CHAR", [PyObject_P, Py_ssize_t], Py_UCS4, **_llextkws)

# Functions in listobject.h
PyList_Check = rffi.llexternal("PyList_Check", [PyObject_P], lltype.Bool, **_llextkws)
PyList_CheckExact = rffi.llexternal("PyList_CheckExact", [PyObject_P], lltype.Bool, **_llextkws)
PyList_New = rffi.llexternal("PyList_New", [Py_ssize_t], PyObject_P, **_llextkws)
PyList_Size = rffi.llexternal("PyList_Size", [PyObject_P], Py_ssize_t, **_llextkws)
PyList_GetItem = rffi.llexternal("PyList_GetItem", [PyObject_P, Py_ssize_t], PyObject_P, **_llextkws)
PyList_SetItem = rffi.llexternal("PyList_SetItem", [PyObject_P, Py_ssize_t, PyObject_P], rffi.INT, **_llextkws)
PyList_Insert = rffi.llexternal("PyList_Insert", [PyObject_P, Py_ssize_t, PyObject_P], rffi.INT, **_llextkws)
PyList_Append = rffi.llexternal("PyList_Append", [PyObject_P, PyObject_P], rffi.INT, **_llextkws)
PyList_GetSlice = rffi.llexternal("PyList_GetSlice", [PyObject_P, Py_ssize_t, Py_ssize_t], PyObject_P, **_llextkws)
PyList_SetSlice = rffi.llexternal("PyList_SetSlice", [PyObject_P, Py_ssize_t, Py_ssize_t, PyObject_P], rffi.INT, **_llextkws)
PyList_Sort = rffi.llexternal("PyList_Sort", [PyObject_P], rffi.INT, **_llextkws)
PyList_Reverse = rffi.llexternal("PyList_Reverse", [PyObject_P], rffi.INT, **_llextkws)
PyList_AsTuple = rffi.llexternal("PyList_AsTuple", [PyObject_P], PyObject_P, **_llextkws)
# Functions in cpython/listobject.h
PyList_GET_SIZE = rffi.llexternal("PyList_GET_SIZE", [PyObject_P], Py_ssize_t, **_llextkws)
PyList_GET_ITEM = rffi.llexternal("PyList_GET_ITEM", [PyObject_P, Py_ssize_t], PyObject_P, **_llextkws)
PyList_SET_ITEM = rffi.llexternal("PyList_SET_ITEM", [PyObject_P, Py_ssize_t, PyObject_P], lltype.Void, **_llextkws)
PyList_Extend = rffi.llexternal("PyList_Extend", [PyObject_P, PyObject_P], rffi.INT, **_llextkws)
PyList_Clear = rffi.llexternal("PyList_Clear", [PyObject_P], rffi.INT, **_llextkws)

# Functions in dictobject.h
PyDict_Check = rffi.llexternal("PyDict_Check", [PyObject_P], lltype.Bool, **_llextkws)
PyDict_CheckExact = rffi.llexternal("PyDict_CheckExact", [PyObject_P], lltype.Bool, **_llextkws)
PyDict_New = rffi.llexternal("PyDict_New", [], PyObject_P, **_llextkws)
PyDict_GetItem = rffi.llexternal("PyDict_GetItem", [PyObject_P, PyObject_P], PyObject_P, **_llextkws)
PyDict_GetItemWithError = rffi.llexternal("PyDict_GetItemWithError", [PyObject_P, PyObject_P], PyObject_P, **_llextkws)
PyDict_SetItem = rffi.llexternal("PyDict_SetItem", [PyObject_P, PyObject_P, PyObject_P], rffi.INT, **_llextkws)
PyDict_DelItem = rffi.llexternal("PyDict_DelItem", [PyObject_P, PyObject_P], rffi.INT, **_llextkws)
PyDict_Clear = rffi.llexternal("PyDict_Clear", [PyObject_P], lltype.Void, **_llextkws)
PyDict_GetItemRef = rffi.llexternal("PyDict_GetItemRef", [PyObject_P, PyObject_P, rffi.CArrayPtr(PyObject_P)], rffi.INT, **_llextkws)

# Functions in tupleobject.h
PyTuple_Check = rffi.llexternal("PyTuple_Check", [PyObject_P], lltype.Bool, **_llextkws)
PyTuple_CheckExact = rffi.llexternal("PyTuple_CheckExact", [PyObject_P], lltype.Bool, **_llextkws)
PyTuple_New = rffi.llexternal("PyTuple_New", [], PyObject_P, **_llextkws)
PyTuple_Size = rffi.llexternal("PyTuple_Size", [PyObject_P], Py_ssize_t, **_llextkws)
PyTuple_GetItem = rffi.llexternal("PyTuple_GetItem", [PyObject_P, Py_ssize_t], PyObject_P, **_llextkws)
PyTuple_SetItem = rffi.llexternal("PyTuple_SetItem", [PyObject_P, Py_ssize_t, PyObject_P], rffi.INT, **_llextkws)
PyTuple_GetSlice = rffi.llexternal("PyTuple_GetSlice", [PyObject_P, Py_ssize_t, Py_ssize_t], PyObject_P, **_llextkws)
# Functions in cpython/tupleobject.h
PyTuple_GET_SIZE = rffi.llexternal("PyTuple_GET_SIZE", [PyObject_P], Py_ssize_t, **_llextkws)
PyTuple_GET_ITEM = rffi.llexternal("PyTuple_GET_ITEM", [PyObject_P, Py_ssize_t], PyObject_P, **_llextkws)
PyTuple_SET_ITEM = rffi.llexternal("PyTuple_SET_ITEM", [PyObject_P, Py_ssize_t, PyObject_P], lltype.Void, **_llextkws)

# Functions in setobject.h
PySet_Check = rffi.llexternal("PySet_Check", [PyObject_P], lltype.Bool, **_llextkws)
PySet_CheckExact = rffi.llexternal("PySet_CheckExact", [PyObject_P], lltype.Bool, **_llextkws)
PyAnySet_Check = rffi.llexternal("PyAnySet_Check", [PyObject_P], lltype.Bool, **_llextkws)
PyAnySet_CheckExact = rffi.llexternal("PyAnySet_CheckExact", [PyObject_P], lltype.Bool, **_llextkws)
PyFrozenSet_Check = rffi.llexternal("PyFrozenSet_Check", [PyObject_P], lltype.Bool, **_llextkws)
PyFrozenSet_CheckExact = rffi.llexternal("PyFrozenSet_CheckExact", [PyObject_P], lltype.Bool, **_llextkws)
PySet_New = rffi.llexternal("PySet_New", [PyObject_P], PyObject_P, **_llextkws)
PyFrozenSet_New = rffi.llexternal("PyFrozenSet_New", [PyObject_P], PyObject_P, **_llextkws)
PySet_Add = rffi.llexternal("PySet_Add", [PyObject_P, PyObject_P], rffi.INT, **_llextkws)
PySet_Clear = rffi.llexternal("PySet_Clear", [PyObject_P], rffi.INT, **_llextkws)
PySet_Contains = rffi.llexternal("PySet_Contains", [PyObject_P, PyObject_P], rffi.INT, **_llextkws)
PySet_Discard = rffi.llexternal("PySet_Discard", [PyObject_P, PyObject_P], rffi.INT, **_llextkws)
PySet_Pop = rffi.llexternal("PySet_Pop", [PyObject_P], PyObject_P, **_llextkws)
PySet_Size = rffi.llexternal("PySet_Size", [PyObject_P], Py_ssize_t, **_llextkws)
# Functions in cpython/setobject.h
PySet_GET_SIZE = rffi.llexternal("PySet_GET_SIZE", [PyObject_P], Py_ssize_t, **_llextkws)

# Functions in sliceobject.h
PySlice_New = rffi.llexternal("PySlice_New", [PyObject_P, PyObject_P, PyObject_P], PyObject_P, **_llextkws)

# Contants defined in object.h
Py_None = rffi.CConstant("Py_None", PyObject_P)
Py_TPFLAGS_HEAPTYPE = rffi.CConstant("Py_TPFLAGS_HEAPTYPE", rffi.ULONG)
# Contants defined in boolobject.h
Py_True = rffi.CConstant("Py_True", PyObject_P)
Py_False = rffi.CConstant("Py_False", PyObject_P)

_OPCODE_ECI = ExternalCompilationInfo(
    pre_include_bits=_ECI.pre_include_bits,
    includes=[_ for _ in _ECI.includes] + ["opcode.h"],
    include_dirs=_ECI.include_dirs,
    libraries=_ECI.libraries,
    library_dirs=_ECI.library_dirs,
)


class _CPyOpcodeConfig:
    """
    opcode.h
    opcode_ids.h
    """
    _compilation_info_ = _OPCODE_ECI

    # opcode_ids.h
    BEFORE_ASYNC_WITH = rffi_platform.DefinedConstantInteger("BEFORE_ASYNC_WITH")
    BEFORE_WITH = rffi_platform.DefinedConstantInteger("BEFORE_WITH")
    BINARY_OP_INPLACE_ADD_UNICODE = rffi_platform.DefinedConstantInteger("BINARY_OP_INPLACE_ADD_UNICODE")
    BINARY_SLICE = rffi_platform.DefinedConstantInteger("BINARY_SLICE")
    BINARY_SUBSCR = rffi_platform.DefinedConstantInteger("BINARY_SUBSCR")
    CHECK_EG_MATCH = rffi_platform.DefinedConstantInteger("CHECK_EG_MATCH")
    CHECK_EXC_MATCH = rffi_platform.DefinedConstantInteger("CHECK_EXC_MATCH")
    CLEANUP_THROW = rffi_platform.DefinedConstantInteger("CLEANUP_THROW")
    DELETE_SUBSCR = rffi_platform.DefinedConstantInteger("DELETE_SUBSCR")
    END_ASYNC_FOR = rffi_platform.DefinedConstantInteger("END_ASYNC_FOR")
    END_FOR = rffi_platform.DefinedConstantInteger("END_FOR")
    END_SEND = rffi_platform.DefinedConstantInteger("END_SEND")
    EXIT_INIT_CHECK = rffi_platform.DefinedConstantInteger("EXIT_INIT_CHECK")
    FORMAT_SIMPLE = rffi_platform.DefinedConstantInteger("FORMAT_SIMPLE")
    FORMAT_WITH_SPEC = rffi_platform.DefinedConstantInteger("FORMAT_WITH_SPEC")
    GET_AITER = rffi_platform.DefinedConstantInteger("GET_AITER")
    RESERVED = rffi_platform.DefinedConstantInteger("RESERVED")
    GET_ANEXT = rffi_platform.DefinedConstantInteger("GET_ANEXT")
    GET_ITER = rffi_platform.DefinedConstantInteger("GET_ITER")
    GET_LEN = rffi_platform.DefinedConstantInteger("GET_LEN")
    GET_YIELD_FROM_ITER = rffi_platform.DefinedConstantInteger("GET_YIELD_FROM_ITER")
    INTERPRETER_EXIT = rffi_platform.DefinedConstantInteger("INTERPRETER_EXIT")
    LOAD_ASSERTION_ERROR = rffi_platform.DefinedConstantInteger("LOAD_ASSERTION_ERROR")
    LOAD_BUILD_CLASS = rffi_platform.DefinedConstantInteger("LOAD_BUILD_CLASS")
    LOAD_LOCALS = rffi_platform.DefinedConstantInteger("LOAD_LOCALS")
    MAKE_FUNCTION = rffi_platform.DefinedConstantInteger("MAKE_FUNCTION")
    MATCH_KEYS = rffi_platform.DefinedConstantInteger("MATCH_KEYS")
    MATCH_MAPPING = rffi_platform.DefinedConstantInteger("MATCH_MAPPING")
    MATCH_SEQUENCE = rffi_platform.DefinedConstantInteger("MATCH_SEQUENCE")
    NOP = rffi_platform.DefinedConstantInteger("NOP")
    POP_EXCEPT = rffi_platform.DefinedConstantInteger("POP_EXCEPT")
    POP_TOP = rffi_platform.DefinedConstantInteger("POP_TOP")
    PUSH_EXC_INFO = rffi_platform.DefinedConstantInteger("PUSH_EXC_INFO")
    PUSH_NULL = rffi_platform.DefinedConstantInteger("PUSH_NULL")
    RETURN_GENERATOR = rffi_platform.DefinedConstantInteger("RETURN_GENERATOR")
    RETURN_VALUE = rffi_platform.DefinedConstantInteger("RETURN_VALUE")
    SETUP_ANNOTATIONS = rffi_platform.DefinedConstantInteger("SETUP_ANNOTATIONS")
    STORE_SLICE = rffi_platform.DefinedConstantInteger("STORE_SLICE")
    STORE_SUBSCR = rffi_platform.DefinedConstantInteger("STORE_SUBSCR")
    TO_BOOL = rffi_platform.DefinedConstantInteger("TO_BOOL")
    UNARY_INVERT = rffi_platform.DefinedConstantInteger("UNARY_INVERT")
    UNARY_NEGATIVE = rffi_platform.DefinedConstantInteger("UNARY_NEGATIVE")
    UNARY_NOT = rffi_platform.DefinedConstantInteger("UNARY_NOT")
    WITH_EXCEPT_START = rffi_platform.DefinedConstantInteger("WITH_EXCEPT_START")
    BINARY_OP = rffi_platform.DefinedConstantInteger("BINARY_OP")
    BUILD_CONST_KEY_MAP = rffi_platform.DefinedConstantInteger("BUILD_CONST_KEY_MAP")
    BUILD_LIST = rffi_platform.DefinedConstantInteger("BUILD_LIST")
    BUILD_MAP = rffi_platform.DefinedConstantInteger("BUILD_MAP")
    BUILD_SET = rffi_platform.DefinedConstantInteger("BUILD_SET")
    BUILD_SLICE = rffi_platform.DefinedConstantInteger("BUILD_SLICE")
    BUILD_STRING = rffi_platform.DefinedConstantInteger("BUILD_STRING")
    BUILD_TUPLE = rffi_platform.DefinedConstantInteger("BUILD_TUPLE")
    CALL = rffi_platform.DefinedConstantInteger("CALL")
    CALL_FUNCTION_EX = rffi_platform.DefinedConstantInteger("CALL_FUNCTION_EX")
    CALL_INTRINSIC_1 = rffi_platform.DefinedConstantInteger("CALL_INTRINSIC_1")
    CALL_INTRINSIC_2 = rffi_platform.DefinedConstantInteger("CALL_INTRINSIC_2")
    CALL_KW = rffi_platform.DefinedConstantInteger("CALL_KW")
    COMPARE_OP = rffi_platform.DefinedConstantInteger("COMPARE_OP")
    CONTAINS_OP = rffi_platform.DefinedConstantInteger("CONTAINS_OP")
    CONVERT_VALUE = rffi_platform.DefinedConstantInteger("CONVERT_VALUE")
    COPY = rffi_platform.DefinedConstantInteger("COPY")
    COPY_FREE_VARS = rffi_platform.DefinedConstantInteger("COPY_FREE_VARS")
    DELETE_ATTR = rffi_platform.DefinedConstantInteger("DELETE_ATTR")
    DELETE_DEREF = rffi_platform.DefinedConstantInteger("DELETE_DEREF")
    DELETE_FAST = rffi_platform.DefinedConstantInteger("DELETE_FAST")
    DELETE_GLOBAL = rffi_platform.DefinedConstantInteger("DELETE_GLOBAL")
    DELETE_NAME = rffi_platform.DefinedConstantInteger("DELETE_NAME")
    DICT_MERGE = rffi_platform.DefinedConstantInteger("DICT_MERGE")
    DICT_UPDATE = rffi_platform.DefinedConstantInteger("DICT_UPDATE")
    ENTER_EXECUTOR = rffi_platform.DefinedConstantInteger("ENTER_EXECUTOR")
    EXTENDED_ARG = rffi_platform.DefinedConstantInteger("EXTENDED_ARG")
    FOR_ITER = rffi_platform.DefinedConstantInteger("FOR_ITER")
    GET_AWAITABLE = rffi_platform.DefinedConstantInteger("GET_AWAITABLE")
    IMPORT_FROM = rffi_platform.DefinedConstantInteger("IMPORT_FROM")
    IMPORT_NAME = rffi_platform.DefinedConstantInteger("IMPORT_NAME")
    IS_OP = rffi_platform.DefinedConstantInteger("IS_OP")
    JUMP_BACKWARD = rffi_platform.DefinedConstantInteger("JUMP_BACKWARD")
    JUMP_BACKWARD_NO_INTERRUPT = rffi_platform.DefinedConstantInteger("JUMP_BACKWARD_NO_INTERRUPT")
    JUMP_FORWARD = rffi_platform.DefinedConstantInteger("JUMP_FORWARD")
    LIST_APPEND = rffi_platform.DefinedConstantInteger("LIST_APPEND")
    LIST_EXTEND = rffi_platform.DefinedConstantInteger("LIST_EXTEND")
    LOAD_ATTR = rffi_platform.DefinedConstantInteger("LOAD_ATTR")
    LOAD_CONST = rffi_platform.DefinedConstantInteger("LOAD_CONST")
    LOAD_DEREF = rffi_platform.DefinedConstantInteger("LOAD_DEREF")
    LOAD_FAST = rffi_platform.DefinedConstantInteger("LOAD_FAST")
    LOAD_FAST_AND_CLEAR = rffi_platform.DefinedConstantInteger("LOAD_FAST_AND_CLEAR")
    LOAD_FAST_CHECK = rffi_platform.DefinedConstantInteger("LOAD_FAST_CHECK")
    LOAD_FAST_LOAD_FAST = rffi_platform.DefinedConstantInteger("LOAD_FAST_LOAD_FAST")
    LOAD_FROM_DICT_OR_DEREF = rffi_platform.DefinedConstantInteger("LOAD_FROM_DICT_OR_DEREF")
    LOAD_FROM_DICT_OR_GLOBALS = rffi_platform.DefinedConstantInteger("LOAD_FROM_DICT_OR_GLOBALS")
    LOAD_GLOBAL = rffi_platform.DefinedConstantInteger("LOAD_GLOBAL")
    LOAD_NAME = rffi_platform.DefinedConstantInteger("LOAD_NAME")
    LOAD_SUPER_ATTR = rffi_platform.DefinedConstantInteger("LOAD_SUPER_ATTR")
    MAKE_CELL = rffi_platform.DefinedConstantInteger("MAKE_CELL")
    MAP_ADD = rffi_platform.DefinedConstantInteger("MAP_ADD")
    MATCH_CLASS = rffi_platform.DefinedConstantInteger("MATCH_CLASS")
    POP_JUMP_IF_FALSE = rffi_platform.DefinedConstantInteger("POP_JUMP_IF_FALSE")
    POP_JUMP_IF_NONE = rffi_platform.DefinedConstantInteger("POP_JUMP_IF_NONE")
    POP_JUMP_IF_NOT_NONE = rffi_platform.DefinedConstantInteger("POP_JUMP_IF_NOT_NONE")
    POP_JUMP_IF_TRUE = rffi_platform.DefinedConstantInteger("POP_JUMP_IF_TRUE")
    RAISE_VARARGS = rffi_platform.DefinedConstantInteger("RAISE_VARARGS")
    RERAISE = rffi_platform.DefinedConstantInteger("RERAISE")
    RETURN_CONST = rffi_platform.DefinedConstantInteger("RETURN_CONST")
    SEND = rffi_platform.DefinedConstantInteger("SEND")
    SET_ADD = rffi_platform.DefinedConstantInteger("SET_ADD")
    SET_FUNCTION_ATTRIBUTE = rffi_platform.DefinedConstantInteger("SET_FUNCTION_ATTRIBUTE")
    SET_UPDATE = rffi_platform.DefinedConstantInteger("SET_UPDATE")
    STORE_ATTR = rffi_platform.DefinedConstantInteger("STORE_ATTR")
    STORE_DEREF = rffi_platform.DefinedConstantInteger("STORE_DEREF")
    STORE_FAST = rffi_platform.DefinedConstantInteger("STORE_FAST")
    STORE_FAST_LOAD_FAST = rffi_platform.DefinedConstantInteger("STORE_FAST_LOAD_FAST")
    STORE_FAST_STORE_FAST = rffi_platform.DefinedConstantInteger("STORE_FAST_STORE_FAST")
    STORE_GLOBAL = rffi_platform.DefinedConstantInteger("STORE_GLOBAL")
    STORE_NAME = rffi_platform.DefinedConstantInteger("STORE_NAME")
    SWAP = rffi_platform.DefinedConstantInteger("SWAP")
    UNPACK_EX = rffi_platform.DefinedConstantInteger("UNPACK_EX")
    UNPACK_SEQUENCE = rffi_platform.DefinedConstantInteger("UNPACK_SEQUENCE")
    YIELD_VALUE = rffi_platform.DefinedConstantInteger("YIELD_VALUE")
    RESUME = rffi_platform.DefinedConstantInteger("RESUME")
    BINARY_OP_ADD_FLOAT = rffi_platform.DefinedConstantInteger("BINARY_OP_ADD_FLOAT")
    BINARY_OP_ADD_INT = rffi_platform.DefinedConstantInteger("BINARY_OP_ADD_INT")
    BINARY_OP_ADD_UNICODE = rffi_platform.DefinedConstantInteger("BINARY_OP_ADD_UNICODE")
    BINARY_OP_MULTIPLY_FLOAT = rffi_platform.DefinedConstantInteger("BINARY_OP_MULTIPLY_FLOAT")
    BINARY_OP_MULTIPLY_INT = rffi_platform.DefinedConstantInteger("BINARY_OP_MULTIPLY_INT")
    BINARY_OP_SUBTRACT_FLOAT = rffi_platform.DefinedConstantInteger("BINARY_OP_SUBTRACT_FLOAT")
    BINARY_OP_SUBTRACT_INT = rffi_platform.DefinedConstantInteger("BINARY_OP_SUBTRACT_INT")
    BINARY_SUBSCR_DICT = rffi_platform.DefinedConstantInteger("BINARY_SUBSCR_DICT")
    BINARY_SUBSCR_GETITEM = rffi_platform.DefinedConstantInteger("BINARY_SUBSCR_GETITEM")
    BINARY_SUBSCR_LIST_INT = rffi_platform.DefinedConstantInteger("BINARY_SUBSCR_LIST_INT")
    BINARY_SUBSCR_STR_INT = rffi_platform.DefinedConstantInteger("BINARY_SUBSCR_STR_INT")
    BINARY_SUBSCR_TUPLE_INT = rffi_platform.DefinedConstantInteger("BINARY_SUBSCR_TUPLE_INT")
    CALL_ALLOC_AND_ENTER_INIT = rffi_platform.DefinedConstantInteger("CALL_ALLOC_AND_ENTER_INIT")
    CALL_BOUND_METHOD_EXACT_ARGS = rffi_platform.DefinedConstantInteger("CALL_BOUND_METHOD_EXACT_ARGS")
    CALL_BOUND_METHOD_GENERAL = rffi_platform.DefinedConstantInteger("CALL_BOUND_METHOD_GENERAL")
    CALL_BUILTIN_CLASS = rffi_platform.DefinedConstantInteger("CALL_BUILTIN_CLASS")
    CALL_BUILTIN_FAST = rffi_platform.DefinedConstantInteger("CALL_BUILTIN_FAST")
    CALL_BUILTIN_FAST_WITH_KEYWORDS = rffi_platform.DefinedConstantInteger("CALL_BUILTIN_FAST_WITH_KEYWORDS")
    CALL_BUILTIN_O = rffi_platform.DefinedConstantInteger("CALL_BUILTIN_O")
    CALL_ISINSTANCE = rffi_platform.DefinedConstantInteger("CALL_ISINSTANCE")
    CALL_LEN = rffi_platform.DefinedConstantInteger("CALL_LEN")
    CALL_LIST_APPEND = rffi_platform.DefinedConstantInteger("CALL_LIST_APPEND")
    CALL_METHOD_DESCRIPTOR_FAST = rffi_platform.DefinedConstantInteger("CALL_METHOD_DESCRIPTOR_FAST")
    CALL_METHOD_DESCRIPTOR_FAST_WITH_KEYWORDS = rffi_platform.DefinedConstantInteger("CALL_METHOD_DESCRIPTOR_FAST_WITH_KEYWORDS")
    CALL_METHOD_DESCRIPTOR_NOARGS = rffi_platform.DefinedConstantInteger("CALL_METHOD_DESCRIPTOR_NOARGS")
    CALL_METHOD_DESCRIPTOR_O = rffi_platform.DefinedConstantInteger("CALL_METHOD_DESCRIPTOR_O")
    CALL_NON_PY_GENERAL = rffi_platform.DefinedConstantInteger("CALL_NON_PY_GENERAL")
    CALL_PY_EXACT_ARGS = rffi_platform.DefinedConstantInteger("CALL_PY_EXACT_ARGS")
    CALL_PY_GENERAL = rffi_platform.DefinedConstantInteger("CALL_PY_GENERAL")
    CALL_STR_1 = rffi_platform.DefinedConstantInteger("CALL_STR_1")
    CALL_TUPLE_1 = rffi_platform.DefinedConstantInteger("CALL_TUPLE_1")
    CALL_TYPE_1 = rffi_platform.DefinedConstantInteger("CALL_TYPE_1")
    COMPARE_OP_FLOAT = rffi_platform.DefinedConstantInteger("COMPARE_OP_FLOAT")
    COMPARE_OP_INT = rffi_platform.DefinedConstantInteger("COMPARE_OP_INT")
    COMPARE_OP_STR = rffi_platform.DefinedConstantInteger("COMPARE_OP_STR")
    CONTAINS_OP_DICT = rffi_platform.DefinedConstantInteger("CONTAINS_OP_DICT")
    CONTAINS_OP_SET = rffi_platform.DefinedConstantInteger("CONTAINS_OP_SET")
    FOR_ITER_GEN = rffi_platform.DefinedConstantInteger("FOR_ITER_GEN")
    FOR_ITER_LIST = rffi_platform.DefinedConstantInteger("FOR_ITER_LIST")
    FOR_ITER_RANGE = rffi_platform.DefinedConstantInteger("FOR_ITER_RANGE")
    FOR_ITER_TUPLE = rffi_platform.DefinedConstantInteger("FOR_ITER_TUPLE")
    LOAD_ATTR_CLASS = rffi_platform.DefinedConstantInteger("LOAD_ATTR_CLASS")
    LOAD_ATTR_GETATTRIBUTE_OVERRIDDEN = rffi_platform.DefinedConstantInteger("LOAD_ATTR_GETATTRIBUTE_OVERRIDDEN")
    LOAD_ATTR_INSTANCE_VALUE = rffi_platform.DefinedConstantInteger("LOAD_ATTR_INSTANCE_VALUE")
    LOAD_ATTR_METHOD_LAZY_DICT = rffi_platform.DefinedConstantInteger("LOAD_ATTR_METHOD_LAZY_DICT")
    LOAD_ATTR_METHOD_NO_DICT = rffi_platform.DefinedConstantInteger("LOAD_ATTR_METHOD_NO_DICT")
    LOAD_ATTR_METHOD_WITH_VALUES = rffi_platform.DefinedConstantInteger("LOAD_ATTR_METHOD_WITH_VALUES")
    LOAD_ATTR_MODULE = rffi_platform.DefinedConstantInteger("LOAD_ATTR_MODULE")
    LOAD_ATTR_NONDESCRIPTOR_NO_DICT = rffi_platform.DefinedConstantInteger("LOAD_ATTR_NONDESCRIPTOR_NO_DICT")
    LOAD_ATTR_NONDESCRIPTOR_WITH_VALUES = rffi_platform.DefinedConstantInteger("LOAD_ATTR_NONDESCRIPTOR_WITH_VALUES")
    LOAD_ATTR_PROPERTY = rffi_platform.DefinedConstantInteger("LOAD_ATTR_PROPERTY")
    LOAD_ATTR_SLOT = rffi_platform.DefinedConstantInteger("LOAD_ATTR_SLOT")
    LOAD_ATTR_WITH_HINT = rffi_platform.DefinedConstantInteger("LOAD_ATTR_WITH_HINT")
    LOAD_GLOBAL_BUILTIN = rffi_platform.DefinedConstantInteger("LOAD_GLOBAL_BUILTIN")
    LOAD_GLOBAL_MODULE = rffi_platform.DefinedConstantInteger("LOAD_GLOBAL_MODULE")
    LOAD_SUPER_ATTR_ATTR = rffi_platform.DefinedConstantInteger("LOAD_SUPER_ATTR_ATTR")
    LOAD_SUPER_ATTR_METHOD = rffi_platform.DefinedConstantInteger("LOAD_SUPER_ATTR_METHOD")
    RESUME_CHECK = rffi_platform.DefinedConstantInteger("RESUME_CHECK")
    SEND_GEN = rffi_platform.DefinedConstantInteger("SEND_GEN")
    STORE_ATTR_INSTANCE_VALUE = rffi_platform.DefinedConstantInteger("STORE_ATTR_INSTANCE_VALUE")
    STORE_ATTR_SLOT = rffi_platform.DefinedConstantInteger("STORE_ATTR_SLOT")
    STORE_ATTR_WITH_HINT = rffi_platform.DefinedConstantInteger("STORE_ATTR_WITH_HINT")
    STORE_SUBSCR_DICT = rffi_platform.DefinedConstantInteger("STORE_SUBSCR_DICT")
    STORE_SUBSCR_LIST_INT = rffi_platform.DefinedConstantInteger("STORE_SUBSCR_LIST_INT")
    TO_BOOL_ALWAYS_TRUE = rffi_platform.DefinedConstantInteger("TO_BOOL_ALWAYS_TRUE")
    TO_BOOL_BOOL = rffi_platform.DefinedConstantInteger("TO_BOOL_BOOL")
    TO_BOOL_INT = rffi_platform.DefinedConstantInteger("TO_BOOL_INT")
    TO_BOOL_LIST = rffi_platform.DefinedConstantInteger("TO_BOOL_LIST")
    TO_BOOL_NONE = rffi_platform.DefinedConstantInteger("TO_BOOL_NONE")
    TO_BOOL_STR = rffi_platform.DefinedConstantInteger("TO_BOOL_STR")
    UNPACK_SEQUENCE_LIST = rffi_platform.DefinedConstantInteger("UNPACK_SEQUENCE_LIST")
    UNPACK_SEQUENCE_TUPLE = rffi_platform.DefinedConstantInteger("UNPACK_SEQUENCE_TUPLE")
    UNPACK_SEQUENCE_TWO_TUPLE = rffi_platform.DefinedConstantInteger("UNPACK_SEQUENCE_TWO_TUPLE")
    INSTRUMENTED_RESUME = rffi_platform.DefinedConstantInteger("INSTRUMENTED_RESUME")
    INSTRUMENTED_END_FOR = rffi_platform.DefinedConstantInteger("INSTRUMENTED_END_FOR")
    INSTRUMENTED_END_SEND = rffi_platform.DefinedConstantInteger("INSTRUMENTED_END_SEND")
    INSTRUMENTED_RETURN_VALUE = rffi_platform.DefinedConstantInteger("INSTRUMENTED_RETURN_VALUE")
    INSTRUMENTED_RETURN_CONST = rffi_platform.DefinedConstantInteger("INSTRUMENTED_RETURN_CONST")
    INSTRUMENTED_YIELD_VALUE = rffi_platform.DefinedConstantInteger("INSTRUMENTED_YIELD_VALUE")
    INSTRUMENTED_LOAD_SUPER_ATTR = rffi_platform.DefinedConstantInteger("INSTRUMENTED_LOAD_SUPER_ATTR")
    INSTRUMENTED_FOR_ITER = rffi_platform.DefinedConstantInteger("INSTRUMENTED_FOR_ITER")
    INSTRUMENTED_CALL = rffi_platform.DefinedConstantInteger("INSTRUMENTED_CALL")
    INSTRUMENTED_CALL_KW = rffi_platform.DefinedConstantInteger("INSTRUMENTED_CALL_KW")
    INSTRUMENTED_CALL_FUNCTION_EX = rffi_platform.DefinedConstantInteger("INSTRUMENTED_CALL_FUNCTION_EX")
    INSTRUMENTED_INSTRUCTION = rffi_platform.DefinedConstantInteger("INSTRUMENTED_INSTRUCTION")
    INSTRUMENTED_JUMP_FORWARD = rffi_platform.DefinedConstantInteger("INSTRUMENTED_JUMP_FORWARD")
    INSTRUMENTED_JUMP_BACKWARD = rffi_platform.DefinedConstantInteger("INSTRUMENTED_JUMP_BACKWARD")
    INSTRUMENTED_POP_JUMP_IF_TRUE = rffi_platform.DefinedConstantInteger("INSTRUMENTED_POP_JUMP_IF_TRUE")
    INSTRUMENTED_POP_JUMP_IF_FALSE = rffi_platform.DefinedConstantInteger("INSTRUMENTED_POP_JUMP_IF_FALSE")
    INSTRUMENTED_POP_JUMP_IF_NONE = rffi_platform.DefinedConstantInteger("INSTRUMENTED_POP_JUMP_IF_NONE")
    INSTRUMENTED_POP_JUMP_IF_NOT_NONE = rffi_platform.DefinedConstantInteger("INSTRUMENTED_POP_JUMP_IF_NOT_NONE")
    INSTRUMENTED_LINE = rffi_platform.DefinedConstantInteger("INSTRUMENTED_LINE")
    JUMP = rffi_platform.DefinedConstantInteger("JUMP")
    JUMP_NO_INTERRUPT = rffi_platform.DefinedConstantInteger("JUMP_NO_INTERRUPT")
    LOAD_CLOSURE = rffi_platform.DefinedConstantInteger("LOAD_CLOSURE")
    LOAD_METHOD = rffi_platform.DefinedConstantInteger("LOAD_METHOD")
    LOAD_SUPER_METHOD = rffi_platform.DefinedConstantInteger("LOAD_SUPER_METHOD")
    LOAD_ZERO_SUPER_ATTR = rffi_platform.DefinedConstantInteger("LOAD_ZERO_SUPER_ATTR")
    LOAD_ZERO_SUPER_METHOD = rffi_platform.DefinedConstantInteger("LOAD_ZERO_SUPER_METHOD")
    POP_BLOCK = rffi_platform.DefinedConstantInteger("POP_BLOCK")
    SETUP_CLEANUP = rffi_platform.DefinedConstantInteger("SETUP_CLEANUP")
    SETUP_FINALLY = rffi_platform.DefinedConstantInteger("SETUP_FINALLY")
    SETUP_WITH = rffi_platform.DefinedConstantInteger("SETUP_WITH")
    STORE_FAST_MAYBE_NULL = rffi_platform.DefinedConstantInteger("STORE_FAST_MAYBE_NULL")
    HAVE_ARGUMENT = rffi_platform.DefinedConstantInteger("HAVE_ARGUMENT")
    MIN_INSTRUMENTED_OPCODE = rffi_platform.DefinedConstantInteger("MIN_INSTRUMENTED_OPCODE")
    # opcode.h
    NB_ADD = rffi_platform.DefinedConstantInteger("NB_ADD")
    NB_AND = rffi_platform.DefinedConstantInteger("NB_AND")
    NB_FLOOR_DIVIDE = rffi_platform.DefinedConstantInteger("NB_FLOOR_DIVIDE")
    NB_LSHIFT = rffi_platform.DefinedConstantInteger("NB_LSHIFT")
    NB_MATRIX_MULTIPLY = rffi_platform.DefinedConstantInteger("NB_MATRIX_MULTIPLY")
    NB_MULTIPLY = rffi_platform.DefinedConstantInteger("NB_MULTIPLY")
    NB_REMAINDER = rffi_platform.DefinedConstantInteger("NB_REMAINDER")
    NB_OR = rffi_platform.DefinedConstantInteger("NB_OR")
    NB_POWER = rffi_platform.DefinedConstantInteger("NB_POWER")
    NB_RSHIFT = rffi_platform.DefinedConstantInteger("NB_RSHIFT")
    NB_SUBTRACT = rffi_platform.DefinedConstantInteger("NB_SUBTRACT")
    NB_TRUE_DIVIDE = rffi_platform.DefinedConstantInteger("NB_TRUE_DIVIDE")
    NB_XOR = rffi_platform.DefinedConstantInteger("NB_XOR")
    NB_INPLACE_ADD = rffi_platform.DefinedConstantInteger("NB_INPLACE_ADD")
    NB_INPLACE_AND = rffi_platform.DefinedConstantInteger("NB_INPLACE_AND")
    NB_INPLACE_FLOOR_DIVIDE = rffi_platform.DefinedConstantInteger("NB_INPLACE_FLOOR_DIVIDE")
    NB_INPLACE_LSHIFT = rffi_platform.DefinedConstantInteger("NB_INPLACE_LSHIFT")
    NB_INPLACE_MATRIX_MULTIPLY = rffi_platform.DefinedConstantInteger("NB_INPLACE_MATRIX_MULTIPLY")
    NB_INPLACE_MULTIPLY = rffi_platform.DefinedConstantInteger("NB_INPLACE_MULTIPLY")
    NB_INPLACE_REMAINDER = rffi_platform.DefinedConstantInteger("NB_INPLACE_REMAINDER")
    NB_INPLACE_OR = rffi_platform.DefinedConstantInteger("NB_INPLACE_OR")
    NB_INPLACE_POWER = rffi_platform.DefinedConstantInteger("NB_INPLACE_POWER")
    NB_INPLACE_RSHIFT = rffi_platform.DefinedConstantInteger("NB_INPLACE_RSHIFT")
    NB_INPLACE_SUBTRACT = rffi_platform.DefinedConstantInteger("NB_INPLACE_SUBTRACT")
    NB_INPLACE_TRUE_DIVIDE = rffi_platform.DefinedConstantInteger("NB_INPLACE_TRUE_DIVIDE")
    NB_INPLACE_XOR = rffi_platform.DefinedConstantInteger("NB_INPLACE_XOR")
    NB_OPARG_LAST = rffi_platform.DefinedConstantInteger("NB_OPARG_LAST")


config = rffi_platform.configure(_CPyOpcodeConfig)
BEFORE_ASYNC_WITH = config["BEFORE_ASYNC_WITH"]
BEFORE_WITH = config["BEFORE_WITH"]
BINARY_OP_INPLACE_ADD_UNICODE = config["BINARY_OP_INPLACE_ADD_UNICODE"]
BINARY_SLICE = config["BINARY_SLICE"]
BINARY_SUBSCR = config["BINARY_SUBSCR"]
CHECK_EG_MATCH = config["CHECK_EG_MATCH"]
CHECK_EXC_MATCH = config["CHECK_EXC_MATCH"]
CLEANUP_THROW = config["CLEANUP_THROW"]
DELETE_SUBSCR = config["DELETE_SUBSCR"]
END_ASYNC_FOR = config["END_ASYNC_FOR"]
END_FOR = config["END_FOR"]
END_SEND = config["END_SEND"]
EXIT_INIT_CHECK = config["EXIT_INIT_CHECK"]
FORMAT_SIMPLE = config["FORMAT_SIMPLE"]
FORMAT_WITH_SPEC = config["FORMAT_WITH_SPEC"]
GET_AITER = config["GET_AITER"]
RESERVED = config["RESERVED"]
GET_ANEXT = config["GET_ANEXT"]
GET_ITER = config["GET_ITER"]
GET_LEN = config["GET_LEN"]
GET_YIELD_FROM_ITER = config["GET_YIELD_FROM_ITER"]
INTERPRETER_EXIT = config["INTERPRETER_EXIT"]
LOAD_ASSERTION_ERROR = config["LOAD_ASSERTION_ERROR"]
LOAD_BUILD_CLASS = config["LOAD_BUILD_CLASS"]
LOAD_LOCALS = config["LOAD_LOCALS"]
MAKE_FUNCTION = config["MAKE_FUNCTION"]
MATCH_KEYS = config["MATCH_KEYS"]
MATCH_MAPPING = config["MATCH_MAPPING"]
MATCH_SEQUENCE = config["MATCH_SEQUENCE"]
NOP = config["NOP"]
POP_EXCEPT = config["POP_EXCEPT"]
POP_TOP = config["POP_TOP"]
PUSH_EXC_INFO = config["PUSH_EXC_INFO"]
PUSH_NULL = config["PUSH_NULL"]
RETURN_GENERATOR = config["RETURN_GENERATOR"]
RETURN_VALUE = config["RETURN_VALUE"]
SETUP_ANNOTATIONS = config["SETUP_ANNOTATIONS"]
STORE_SLICE = config["STORE_SLICE"]
STORE_SUBSCR = config["STORE_SUBSCR"]
TO_BOOL = config["TO_BOOL"]
UNARY_INVERT = config["UNARY_INVERT"]
UNARY_NEGATIVE = config["UNARY_NEGATIVE"]
UNARY_NOT = config["UNARY_NOT"]
WITH_EXCEPT_START = config["WITH_EXCEPT_START"]
BINARY_OP = config["BINARY_OP"]
BUILD_CONST_KEY_MAP = config["BUILD_CONST_KEY_MAP"]
BUILD_LIST = config["BUILD_LIST"]
BUILD_MAP = config["BUILD_MAP"]
BUILD_SET = config["BUILD_SET"]
BUILD_SLICE = config["BUILD_SLICE"]
BUILD_STRING = config["BUILD_STRING"]
BUILD_TUPLE = config["BUILD_TUPLE"]
CALL = config["CALL"]
CALL_FUNCTION_EX = config["CALL_FUNCTION_EX"]
CALL_INTRINSIC_1 = config["CALL_INTRINSIC_1"]
CALL_INTRINSIC_2 = config["CALL_INTRINSIC_2"]
CALL_KW = config["CALL_KW"]
COMPARE_OP = config["COMPARE_OP"]
CONTAINS_OP = config["CONTAINS_OP"]
CONVERT_VALUE = config["CONVERT_VALUE"]
COPY = config["COPY"]
COPY_FREE_VARS = config["COPY_FREE_VARS"]
DELETE_ATTR = config["DELETE_ATTR"]
DELETE_DEREF = config["DELETE_DEREF"]
DELETE_FAST = config["DELETE_FAST"]
DELETE_GLOBAL = config["DELETE_GLOBAL"]
DELETE_NAME = config["DELETE_NAME"]
DICT_MERGE = config["DICT_MERGE"]
DICT_UPDATE = config["DICT_UPDATE"]
ENTER_EXECUTOR = config["ENTER_EXECUTOR"]
EXTENDED_ARG = config["EXTENDED_ARG"]
FOR_ITER = config["FOR_ITER"]
GET_AWAITABLE = config["GET_AWAITABLE"]
IMPORT_FROM = config["IMPORT_FROM"]
IMPORT_NAME = config["IMPORT_NAME"]
IS_OP = config["IS_OP"]
JUMP_BACKWARD = config["JUMP_BACKWARD"]
JUMP_BACKWARD_NO_INTERRUPT = config["JUMP_BACKWARD_NO_INTERRUPT"]
JUMP_FORWARD = config["JUMP_FORWARD"]
LIST_APPEND = config["LIST_APPEND"]
LIST_EXTEND = config["LIST_EXTEND"]
LOAD_ATTR = config["LOAD_ATTR"]
LOAD_CONST = config["LOAD_CONST"]
LOAD_DEREF = config["LOAD_DEREF"]
LOAD_FAST = config["LOAD_FAST"]
LOAD_FAST_AND_CLEAR = config["LOAD_FAST_AND_CLEAR"]
LOAD_FAST_CHECK = config["LOAD_FAST_CHECK"]
LOAD_FAST_LOAD_FAST = config["LOAD_FAST_LOAD_FAST"]
LOAD_FROM_DICT_OR_DEREF = config["LOAD_FROM_DICT_OR_DEREF"]
LOAD_FROM_DICT_OR_GLOBALS = config["LOAD_FROM_DICT_OR_GLOBALS"]
LOAD_GLOBAL = config["LOAD_GLOBAL"]
LOAD_NAME = config["LOAD_NAME"]
LOAD_SUPER_ATTR = config["LOAD_SUPER_ATTR"]
MAKE_CELL = config["MAKE_CELL"]
MAP_ADD = config["MAP_ADD"]
MATCH_CLASS = config["MATCH_CLASS"]
POP_JUMP_IF_FALSE = config["POP_JUMP_IF_FALSE"]
POP_JUMP_IF_NONE = config["POP_JUMP_IF_NONE"]
POP_JUMP_IF_NOT_NONE = config["POP_JUMP_IF_NOT_NONE"]
POP_JUMP_IF_TRUE = config["POP_JUMP_IF_TRUE"]
RAISE_VARARGS = config["RAISE_VARARGS"]
RERAISE = config["RERAISE"]
RETURN_CONST = config["RETURN_CONST"]
SEND = config["SEND"]
SET_ADD = config["SET_ADD"]
SET_FUNCTION_ATTRIBUTE = config["SET_FUNCTION_ATTRIBUTE"]
SET_UPDATE = config["SET_UPDATE"]
STORE_ATTR = config["STORE_ATTR"]
STORE_DEREF = config["STORE_DEREF"]
STORE_FAST = config["STORE_FAST"]
STORE_FAST_LOAD_FAST = config["STORE_FAST_LOAD_FAST"]
STORE_FAST_STORE_FAST = config["STORE_FAST_STORE_FAST"]
STORE_GLOBAL = config["STORE_GLOBAL"]
STORE_NAME = config["STORE_NAME"]
SWAP = config["SWAP"]
UNPACK_EX = config["UNPACK_EX"]
UNPACK_SEQUENCE = config["UNPACK_SEQUENCE"]
YIELD_VALUE = config["YIELD_VALUE"]
RESUME = config["RESUME"]
BINARY_OP_ADD_FLOAT = config["BINARY_OP_ADD_FLOAT"]
BINARY_OP_ADD_INT = config["BINARY_OP_ADD_INT"]
BINARY_OP_ADD_UNICODE = config["BINARY_OP_ADD_UNICODE"]
BINARY_OP_MULTIPLY_FLOAT = config["BINARY_OP_MULTIPLY_FLOAT"]
BINARY_OP_MULTIPLY_INT = config["BINARY_OP_MULTIPLY_INT"]
BINARY_OP_SUBTRACT_FLOAT = config["BINARY_OP_SUBTRACT_FLOAT"]
BINARY_OP_SUBTRACT_INT = config["BINARY_OP_SUBTRACT_INT"]
BINARY_SUBSCR_DICT = config["BINARY_SUBSCR_DICT"]
BINARY_SUBSCR_GETITEM = config["BINARY_SUBSCR_GETITEM"]
BINARY_SUBSCR_LIST_INT = config["BINARY_SUBSCR_LIST_INT"]
BINARY_SUBSCR_STR_INT = config["BINARY_SUBSCR_STR_INT"]
BINARY_SUBSCR_TUPLE_INT = config["BINARY_SUBSCR_TUPLE_INT"]
CALL_ALLOC_AND_ENTER_INIT = config["CALL_ALLOC_AND_ENTER_INIT"]
CALL_BOUND_METHOD_EXACT_ARGS = config["CALL_BOUND_METHOD_EXACT_ARGS"]
CALL_BOUND_METHOD_GENERAL = config["CALL_BOUND_METHOD_GENERAL"]
CALL_BUILTIN_CLASS = config["CALL_BUILTIN_CLASS"]
CALL_BUILTIN_FAST = config["CALL_BUILTIN_FAST"]
CALL_BUILTIN_FAST_WITH_KEYWORDS = config["CALL_BUILTIN_FAST_WITH_KEYWORDS"]
CALL_BUILTIN_O = config["CALL_BUILTIN_O"]
CALL_ISINSTANCE = config["CALL_ISINSTANCE"]
CALL_LEN = config["CALL_LEN"]
CALL_LIST_APPEND = config["CALL_LIST_APPEND"]
CALL_METHOD_DESCRIPTOR_FAST = config["CALL_METHOD_DESCRIPTOR_FAST"]
CALL_METHOD_DESCRIPTOR_FAST_WITH_KEYWORDS = config["CALL_METHOD_DESCRIPTOR_FAST_WITH_KEYWORDS"]
CALL_METHOD_DESCRIPTOR_NOARGS = config["CALL_METHOD_DESCRIPTOR_NOARGS"]
CALL_METHOD_DESCRIPTOR_O = config["CALL_METHOD_DESCRIPTOR_O"]
CALL_NON_PY_GENERAL = config["CALL_NON_PY_GENERAL"]
CALL_PY_EXACT_ARGS = config["CALL_PY_EXACT_ARGS"]
CALL_PY_GENERAL = config["CALL_PY_GENERAL"]
CALL_STR_1 = config["CALL_STR_1"]
CALL_TUPLE_1 = config["CALL_TUPLE_1"]
CALL_TYPE_1 = config["CALL_TYPE_1"]
COMPARE_OP_FLOAT = config["COMPARE_OP_FLOAT"]
COMPARE_OP_INT = config["COMPARE_OP_INT"]
COMPARE_OP_STR = config["COMPARE_OP_STR"]
CONTAINS_OP_DICT = config["CONTAINS_OP_DICT"]
CONTAINS_OP_SET = config["CONTAINS_OP_SET"]
FOR_ITER_GEN = config["FOR_ITER_GEN"]
FOR_ITER_LIST = config["FOR_ITER_LIST"]
FOR_ITER_RANGE = config["FOR_ITER_RANGE"]
FOR_ITER_TUPLE = config["FOR_ITER_TUPLE"]
LOAD_ATTR_CLASS = config["LOAD_ATTR_CLASS"]
LOAD_ATTR_GETATTRIBUTE_OVERRIDDEN = config["LOAD_ATTR_GETATTRIBUTE_OVERRIDDEN"]
LOAD_ATTR_INSTANCE_VALUE = config["LOAD_ATTR_INSTANCE_VALUE"]
LOAD_ATTR_METHOD_LAZY_DICT = config["LOAD_ATTR_METHOD_LAZY_DICT"]
LOAD_ATTR_METHOD_NO_DICT = config["LOAD_ATTR_METHOD_NO_DICT"]
LOAD_ATTR_METHOD_WITH_VALUES = config["LOAD_ATTR_METHOD_WITH_VALUES"]
LOAD_ATTR_MODULE = config["LOAD_ATTR_MODULE"]
LOAD_ATTR_NONDESCRIPTOR_NO_DICT = config["LOAD_ATTR_NONDESCRIPTOR_NO_DICT"]
LOAD_ATTR_NONDESCRIPTOR_WITH_VALUES = config["LOAD_ATTR_NONDESCRIPTOR_WITH_VALUES"]
LOAD_ATTR_PROPERTY = config["LOAD_ATTR_PROPERTY"]
LOAD_ATTR_SLOT = config["LOAD_ATTR_SLOT"]
LOAD_ATTR_WITH_HINT = config["LOAD_ATTR_WITH_HINT"]
LOAD_GLOBAL_BUILTIN = config["LOAD_GLOBAL_BUILTIN"]
LOAD_GLOBAL_MODULE = config["LOAD_GLOBAL_MODULE"]
LOAD_SUPER_ATTR_ATTR = config["LOAD_SUPER_ATTR_ATTR"]
LOAD_SUPER_ATTR_METHOD = config["LOAD_SUPER_ATTR_METHOD"]
RESUME_CHECK = config["RESUME_CHECK"]
SEND_GEN = config["SEND_GEN"]
STORE_ATTR_INSTANCE_VALUE = config["STORE_ATTR_INSTANCE_VALUE"]
STORE_ATTR_SLOT = config["STORE_ATTR_SLOT"]
STORE_ATTR_WITH_HINT = config["STORE_ATTR_WITH_HINT"]
STORE_SUBSCR_DICT = config["STORE_SUBSCR_DICT"]
STORE_SUBSCR_LIST_INT = config["STORE_SUBSCR_LIST_INT"]
TO_BOOL_ALWAYS_TRUE = config["TO_BOOL_ALWAYS_TRUE"]
TO_BOOL_BOOL = config["TO_BOOL_BOOL"]
TO_BOOL_INT = config["TO_BOOL_INT"]
TO_BOOL_LIST = config["TO_BOOL_LIST"]
TO_BOOL_NONE = config["TO_BOOL_NONE"]
TO_BOOL_STR = config["TO_BOOL_STR"]
UNPACK_SEQUENCE_LIST = config["UNPACK_SEQUENCE_LIST"]
UNPACK_SEQUENCE_TUPLE = config["UNPACK_SEQUENCE_TUPLE"]
UNPACK_SEQUENCE_TWO_TUPLE = config["UNPACK_SEQUENCE_TWO_TUPLE"]
INSTRUMENTED_RESUME = config["INSTRUMENTED_RESUME"]
INSTRUMENTED_END_FOR = config["INSTRUMENTED_END_FOR"]
INSTRUMENTED_END_SEND = config["INSTRUMENTED_END_SEND"]
INSTRUMENTED_RETURN_VALUE = config["INSTRUMENTED_RETURN_VALUE"]
INSTRUMENTED_RETURN_CONST = config["INSTRUMENTED_RETURN_CONST"]
INSTRUMENTED_YIELD_VALUE = config["INSTRUMENTED_YIELD_VALUE"]
INSTRUMENTED_LOAD_SUPER_ATTR = config["INSTRUMENTED_LOAD_SUPER_ATTR"]
INSTRUMENTED_FOR_ITER = config["INSTRUMENTED_FOR_ITER"]
INSTRUMENTED_CALL = config["INSTRUMENTED_CALL"]
INSTRUMENTED_CALL_KW = config["INSTRUMENTED_CALL_KW"]
INSTRUMENTED_CALL_FUNCTION_EX = config["INSTRUMENTED_CALL_FUNCTION_EX"]
INSTRUMENTED_INSTRUCTION = config["INSTRUMENTED_INSTRUCTION"]
INSTRUMENTED_JUMP_FORWARD = config["INSTRUMENTED_JUMP_FORWARD"]
INSTRUMENTED_JUMP_BACKWARD = config["INSTRUMENTED_JUMP_BACKWARD"]
INSTRUMENTED_POP_JUMP_IF_TRUE = config["INSTRUMENTED_POP_JUMP_IF_TRUE"]
INSTRUMENTED_POP_JUMP_IF_FALSE = config["INSTRUMENTED_POP_JUMP_IF_FALSE"]
INSTRUMENTED_POP_JUMP_IF_NONE = config["INSTRUMENTED_POP_JUMP_IF_NONE"]
INSTRUMENTED_POP_JUMP_IF_NOT_NONE = config["INSTRUMENTED_POP_JUMP_IF_NOT_NONE"]
INSTRUMENTED_LINE = config["INSTRUMENTED_LINE"]
JUMP = config["JUMP"]
JUMP_NO_INTERRUPT = config["JUMP_NO_INTERRUPT"]
LOAD_CLOSURE = config["LOAD_CLOSURE"]
LOAD_METHOD = config["LOAD_METHOD"]
LOAD_SUPER_METHOD = config["LOAD_SUPER_METHOD"]
LOAD_ZERO_SUPER_ATTR = config["LOAD_ZERO_SUPER_ATTR"]
LOAD_ZERO_SUPER_METHOD = config["LOAD_ZERO_SUPER_METHOD"]
POP_BLOCK = config["POP_BLOCK"]
SETUP_CLEANUP = config["SETUP_CLEANUP"]
SETUP_FINALLY = config["SETUP_FINALLY"]
SETUP_WITH = config["SETUP_WITH"]
STORE_FAST_MAYBE_NULL = config["STORE_FAST_MAYBE_NULL"]
HAVE_ARGUMENT = config["HAVE_ARGUMENT"]
MIN_INSTRUMENTED_OPCODE = config["MIN_INSTRUMENTED_OPCODE"]

NB_ADD = config["NB_ADD"]
NB_AND = config["NB_AND"]
NB_FLOOR_DIVIDE = config["NB_FLOOR_DIVIDE"]
NB_LSHIFT = config["NB_LSHIFT"]
NB_MATRIX_MULTIPLY = config["NB_MATRIX_MULTIPLY"]
NB_MULTIPLY = config["NB_MULTIPLY"]
NB_REMAINDER = config["NB_REMAINDER"]
NB_OR = config["NB_OR"]
NB_POWER = config["NB_POWER"]
NB_RSHIFT = config["NB_RSHIFT"]
NB_SUBTRACT = config["NB_SUBTRACT"]
NB_TRUE_DIVIDE = config["NB_TRUE_DIVIDE"]
NB_XOR = config["NB_XOR"]
NB_INPLACE_ADD = config["NB_INPLACE_ADD"]
NB_INPLACE_AND = config["NB_INPLACE_AND"]
NB_INPLACE_FLOOR_DIVIDE = config["NB_INPLACE_FLOOR_DIVIDE"]
NB_INPLACE_LSHIFT = config["NB_INPLACE_LSHIFT"]
NB_INPLACE_MATRIX_MULTIPLY = config["NB_INPLACE_MATRIX_MULTIPLY"]
NB_INPLACE_MULTIPLY = config["NB_INPLACE_MULTIPLY"]
NB_INPLACE_REMAINDER = config["NB_INPLACE_REMAINDER"]
NB_INPLACE_OR = config["NB_INPLACE_OR"]
NB_INPLACE_POWER = config["NB_INPLACE_POWER"]
NB_INPLACE_RSHIFT = config["NB_INPLACE_RSHIFT"]
NB_INPLACE_SUBTRACT = config["NB_INPLACE_SUBTRACT"]
NB_INPLACE_TRUE_DIVIDE = config["NB_INPLACE_TRUE_DIVIDE"]
NB_INPLACE_XOR = config["NB_INPLACE_XOR"]
NB_OPARG_LAST = config["NB_OPARG_LAST"]


class opcode_ids:
    """
    opcode_ids.h
    """

    CACHE = rffi.CConstant("CACHE", rffi.UCHAR)
    BEFORE_ASYNC_WITH = rffi.CConstant("BEFORE_ASYNC_WITH", rffi.UCHAR)
    BEFORE_WITH = rffi.CConstant("BEFORE_WITH", rffi.UCHAR)
    BINARY_OP_INPLACE_ADD_UNICODE = rffi.CConstant("BINARY_OP_INPLACE_ADD_UNICODE", rffi.UCHAR)
    BINARY_SLICE = rffi.CConstant("BINARY_SLICE", rffi.UCHAR)
    BINARY_SUBSCR = rffi.CConstant("BINARY_SUBSCR", rffi.UCHAR)
    CHECK_EG_MATCH = rffi.CConstant("CHECK_EG_MATCH", rffi.UCHAR)
    CHECK_EXC_MATCH = rffi.CConstant("CHECK_EXC_MATCH", rffi.UCHAR)
    CLEANUP_THROW = rffi.CConstant("CLEANUP_THROW", rffi.UCHAR)
    DELETE_SUBSCR = rffi.CConstant("DELETE_SUBSCR", rffi.UCHAR)
    END_ASYNC_FOR = rffi.CConstant("END_ASYNC_FOR", rffi.UCHAR)
    END_FOR = rffi.CConstant("END_FOR", rffi.UCHAR)
    END_SEND = rffi.CConstant("END_SEND", rffi.UCHAR)
    EXIT_INIT_CHECK = rffi.CConstant("EXIT_INIT_CHECK", rffi.UCHAR)
    FORMAT_SIMPLE = rffi.CConstant("FORMAT_SIMPLE", rffi.UCHAR)
    FORMAT_WITH_SPEC = rffi.CConstant("FORMAT_WITH_SPEC", rffi.UCHAR)
    GET_AITER = rffi.CConstant("GET_AITER", rffi.UCHAR)
    RESERVED = rffi.CConstant("RESERVED", rffi.UCHAR)
    GET_ANEXT = rffi.CConstant("GET_ANEXT", rffi.UCHAR)
    GET_ITER = rffi.CConstant("GET_ITER", rffi.UCHAR)
    GET_LEN = rffi.CConstant("GET_LEN", rffi.UCHAR)
    GET_YIELD_FROM_ITER = rffi.CConstant("GET_YIELD_FROM_ITER", rffi.UCHAR)
    INTERPRETER_EXIT = rffi.CConstant("INTERPRETER_EXIT", rffi.UCHAR)
    LOAD_ASSERTION_ERROR = rffi.CConstant("LOAD_ASSERTION_ERROR", rffi.UCHAR)
    LOAD_BUILD_CLASS = rffi.CConstant("LOAD_BUILD_CLASS", rffi.UCHAR)
    LOAD_LOCALS = rffi.CConstant("LOAD_LOCALS", rffi.UCHAR)
    MAKE_FUNCTION = rffi.CConstant("MAKE_FUNCTION", rffi.UCHAR)
    MATCH_KEYS = rffi.CConstant("MATCH_KEYS", rffi.UCHAR)
    MATCH_MAPPING = rffi.CConstant("MATCH_MAPPING", rffi.UCHAR)
    MATCH_SEQUENCE = rffi.CConstant("MATCH_SEQUENCE", rffi.UCHAR)
    NOP = rffi.CConstant("NOP", rffi.UCHAR)
    POP_EXCEPT = rffi.CConstant("POP_EXCEPT", rffi.UCHAR)
    POP_TOP = rffi.CConstant("POP_TOP", rffi.UCHAR)
    PUSH_EXC_INFO = rffi.CConstant("PUSH_EXC_INFO", rffi.UCHAR)
    PUSH_NULL = rffi.CConstant("PUSH_NULL", rffi.UCHAR)
    RETURN_GENERATOR = rffi.CConstant("RETURN_GENERATOR", rffi.UCHAR)
    RETURN_VALUE = rffi.CConstant("RETURN_VALUE", rffi.UCHAR)
    SETUP_ANNOTATIONS = rffi.CConstant("SETUP_ANNOTATIONS", rffi.UCHAR)
    STORE_SLICE = rffi.CConstant("STORE_SLICE", rffi.UCHAR)
    STORE_SUBSCR = rffi.CConstant("STORE_SUBSCR", rffi.UCHAR)
    TO_BOOL = rffi.CConstant("TO_BOOL", rffi.UCHAR)
    UNARY_INVERT = rffi.CConstant("UNARY_INVERT", rffi.UCHAR)
    UNARY_NEGATIVE = rffi.CConstant("UNARY_NEGATIVE", rffi.UCHAR)
    UNARY_NOT = rffi.CConstant("UNARY_NOT", rffi.UCHAR)
    WITH_EXCEPT_START = rffi.CConstant("WITH_EXCEPT_START", rffi.UCHAR)
    BINARY_OP = rffi.CConstant("BINARY_OP", rffi.UCHAR)
    BUILD_CONST_KEY_MAP = rffi.CConstant("BUILD_CONST_KEY_MAP", rffi.UCHAR)
    BUILD_LIST = rffi.CConstant("BUILD_LIST", rffi.UCHAR)
    BUILD_MAP = rffi.CConstant("BUILD_MAP", rffi.UCHAR)
    BUILD_SET = rffi.CConstant("BUILD_SET", rffi.UCHAR)
    BUILD_SLICE = rffi.CConstant("BUILD_SLICE", rffi.UCHAR)
    BUILD_STRING = rffi.CConstant("BUILD_STRING", rffi.UCHAR)
    BUILD_TUPLE = rffi.CConstant("BUILD_TUPLE", rffi.UCHAR)
    CALL = rffi.CConstant("CALL", rffi.UCHAR)
    CALL_FUNCTION_EX = rffi.CConstant("CALL_FUNCTION_EX", rffi.UCHAR)
    CALL_INTRINSIC_1 = rffi.CConstant("CALL_INTRINSIC_1", rffi.UCHAR)
    CALL_INTRINSIC_2 = rffi.CConstant("CALL_INTRINSIC_2", rffi.UCHAR)
    CALL_KW = rffi.CConstant("CALL_KW", rffi.UCHAR)
    COMPARE_OP = rffi.CConstant("COMPARE_OP", rffi.UCHAR)
    CONTAINS_OP = rffi.CConstant("CONTAINS_OP", rffi.UCHAR)
    CONVERT_VALUE = rffi.CConstant("CONVERT_VALUE", rffi.UCHAR)
    COPY = rffi.CConstant("COPY", rffi.UCHAR)
    COPY_FREE_VARS = rffi.CConstant("COPY_FREE_VARS", rffi.UCHAR)
    DELETE_ATTR = rffi.CConstant("DELETE_ATTR", rffi.UCHAR)
    DELETE_DEREF = rffi.CConstant("DELETE_DEREF", rffi.UCHAR)
    DELETE_FAST = rffi.CConstant("DELETE_FAST", rffi.UCHAR)
    DELETE_GLOBAL = rffi.CConstant("DELETE_GLOBAL", rffi.UCHAR)
    DELETE_NAME = rffi.CConstant("DELETE_NAME", rffi.UCHAR)
    DICT_MERGE = rffi.CConstant("DICT_MERGE", rffi.UCHAR)
    DICT_UPDATE = rffi.CConstant("DICT_UPDATE", rffi.UCHAR)
    ENTER_EXECUTOR = rffi.CConstant("ENTER_EXECUTOR", rffi.UCHAR)
    EXTENDED_ARG = rffi.CConstant("EXTENDED_ARG", rffi.UCHAR)
    FOR_ITER = rffi.CConstant("FOR_ITER", rffi.UCHAR)
    GET_AWAITABLE = rffi.CConstant("GET_AWAITABLE", rffi.UCHAR)
    IMPORT_FROM = rffi.CConstant("IMPORT_FROM", rffi.UCHAR)
    IMPORT_NAME = rffi.CConstant("IMPORT_NAME", rffi.UCHAR)
    IS_OP = rffi.CConstant("IS_OP", rffi.UCHAR)
    JUMP_BACKWARD = rffi.CConstant("JUMP_BACKWARD", rffi.UCHAR)
    JUMP_BACKWARD_NO_INTERRUPT = rffi.CConstant("JUMP_BACKWARD_NO_INTERRUPT", rffi.UCHAR)
    JUMP_FORWARD = rffi.CConstant("JUMP_FORWARD", rffi.UCHAR)
    LIST_APPEND = rffi.CConstant("LIST_APPEND", rffi.UCHAR)
    LIST_EXTEND = rffi.CConstant("LIST_EXTEND", rffi.UCHAR)
    LOAD_ATTR = rffi.CConstant("LOAD_ATTR", rffi.UCHAR)
    LOAD_CONST = rffi.CConstant("LOAD_CONST", rffi.UCHAR)
    LOAD_DEREF = rffi.CConstant("LOAD_DEREF", rffi.UCHAR)
    LOAD_FAST = rffi.CConstant("LOAD_FAST", rffi.UCHAR)
    LOAD_FAST_AND_CLEAR = rffi.CConstant("LOAD_FAST_AND_CLEAR", rffi.UCHAR)
    LOAD_FAST_CHECK = rffi.CConstant("LOAD_FAST_CHECK", rffi.UCHAR)
    LOAD_FAST_LOAD_FAST = rffi.CConstant("LOAD_FAST_LOAD_FAST", rffi.UCHAR)
    LOAD_FROM_DICT_OR_DEREF = rffi.CConstant("LOAD_FROM_DICT_OR_DEREF", rffi.UCHAR)
    LOAD_FROM_DICT_OR_GLOBALS = rffi.CConstant("LOAD_FROM_DICT_OR_GLOBALS", rffi.UCHAR)
    LOAD_GLOBAL = rffi.CConstant("LOAD_GLOBAL", rffi.UCHAR)
    LOAD_NAME = rffi.CConstant("LOAD_NAME", rffi.UCHAR)
    LOAD_SUPER_ATTR = rffi.CConstant("LOAD_SUPER_ATTR", rffi.UCHAR)
    MAKE_CELL = rffi.CConstant("MAKE_CELL", rffi.UCHAR)
    MAP_ADD = rffi.CConstant("MAP_ADD", rffi.UCHAR)
    MATCH_CLASS = rffi.CConstant("MATCH_CLASS", rffi.UCHAR)
    POP_JUMP_IF_FALSE = rffi.CConstant("POP_JUMP_IF_FALSE", rffi.UCHAR)
    POP_JUMP_IF_NONE = rffi.CConstant("POP_JUMP_IF_NONE", rffi.UCHAR)
    POP_JUMP_IF_NOT_NONE = rffi.CConstant("POP_JUMP_IF_NOT_NONE", rffi.UCHAR)
    POP_JUMP_IF_TRUE = rffi.CConstant("POP_JUMP_IF_TRUE", rffi.UCHAR)
    RAISE_VARARGS = rffi.CConstant("RAISE_VARARGS", rffi.UCHAR)
    RERAISE = rffi.CConstant("RERAISE", rffi.UCHAR)
    RETURN_CONST = rffi.CConstant("RETURN_CONST", rffi.UCHAR)
    SEND = rffi.CConstant("SEND", rffi.UCHAR)
    SET_ADD = rffi.CConstant("SET_ADD", rffi.UCHAR)
    SET_FUNCTION_ATTRIBUTE = rffi.CConstant("SET_FUNCTION_ATTRIBUTE", rffi.UCHAR)
    SET_UPDATE = rffi.CConstant("SET_UPDATE", rffi.UCHAR)
    STORE_ATTR = rffi.CConstant("STORE_ATTR", rffi.UCHAR)
    STORE_DEREF = rffi.CConstant("STORE_DEREF", rffi.UCHAR)
    STORE_FAST = rffi.CConstant("STORE_FAST", rffi.UCHAR)
    STORE_FAST_LOAD_FAST = rffi.CConstant("STORE_FAST_LOAD_FAST", rffi.UCHAR)
    STORE_FAST_STORE_FAST = rffi.CConstant("STORE_FAST_STORE_FAST", rffi.UCHAR)
    STORE_GLOBAL = rffi.CConstant("STORE_GLOBAL", rffi.UCHAR)
    STORE_NAME = rffi.CConstant("STORE_NAME", rffi.UCHAR)
    SWAP = rffi.CConstant("SWAP", rffi.UCHAR)
    UNPACK_EX = rffi.CConstant("UNPACK_EX", rffi.UCHAR)
    UNPACK_SEQUENCE = rffi.CConstant("UNPACK_SEQUENCE", rffi.UCHAR)
    YIELD_VALUE = rffi.CConstant("YIELD_VALUE", rffi.UCHAR)
    RESUME = rffi.CConstant("RESUME", rffi.UCHAR)
    BINARY_OP_ADD_FLOAT = rffi.CConstant("BINARY_OP_ADD_FLOAT", rffi.UCHAR)
    BINARY_OP_ADD_INT = rffi.CConstant("BINARY_OP_ADD_INT", rffi.UCHAR)
    BINARY_OP_ADD_UNICODE = rffi.CConstant("BINARY_OP_ADD_UNICODE", rffi.UCHAR)
    BINARY_OP_MULTIPLY_FLOAT = rffi.CConstant("BINARY_OP_MULTIPLY_FLOAT", rffi.UCHAR)
    BINARY_OP_MULTIPLY_INT = rffi.CConstant("BINARY_OP_MULTIPLY_INT", rffi.UCHAR)
    BINARY_OP_SUBTRACT_FLOAT = rffi.CConstant("BINARY_OP_SUBTRACT_FLOAT", rffi.UCHAR)
    BINARY_OP_SUBTRACT_INT = rffi.CConstant("BINARY_OP_SUBTRACT_INT", rffi.UCHAR)
    BINARY_SUBSCR_DICT = rffi.CConstant("BINARY_SUBSCR_DICT", rffi.UCHAR)
    BINARY_SUBSCR_GETITEM = rffi.CConstant("BINARY_SUBSCR_GETITEM", rffi.UCHAR)
    BINARY_SUBSCR_LIST_INT = rffi.CConstant("BINARY_SUBSCR_LIST_INT", rffi.UCHAR)
    BINARY_SUBSCR_STR_INT = rffi.CConstant("BINARY_SUBSCR_STR_INT", rffi.UCHAR)
    BINARY_SUBSCR_TUPLE_INT = rffi.CConstant("BINARY_SUBSCR_TUPLE_INT", rffi.UCHAR)
    CALL_ALLOC_AND_ENTER_INIT = rffi.CConstant("CALL_ALLOC_AND_ENTER_INIT", rffi.UCHAR)
    CALL_BOUND_METHOD_EXACT_ARGS = rffi.CConstant("CALL_BOUND_METHOD_EXACT_ARGS", rffi.UCHAR)
    CALL_BOUND_METHOD_GENERAL = rffi.CConstant("CALL_BOUND_METHOD_GENERAL", rffi.UCHAR)
    CALL_BUILTIN_CLASS = rffi.CConstant("CALL_BUILTIN_CLASS", rffi.UCHAR)
    CALL_BUILTIN_FAST = rffi.CConstant("CALL_BUILTIN_FAST", rffi.UCHAR)
    CALL_BUILTIN_FAST_WITH_KEYWORDS = rffi.CConstant("CALL_BUILTIN_FAST_WITH_KEYWORDS", rffi.UCHAR)
    CALL_BUILTIN_O = rffi.CConstant("CALL_BUILTIN_O", rffi.UCHAR)
    CALL_ISINSTANCE = rffi.CConstant("CALL_ISINSTANCE", rffi.UCHAR)
    CALL_LEN = rffi.CConstant("CALL_LEN", rffi.UCHAR)
    CALL_LIST_APPEND = rffi.CConstant("CALL_LIST_APPEND", rffi.UCHAR)
    CALL_METHOD_DESCRIPTOR_FAST = rffi.CConstant("CALL_METHOD_DESCRIPTOR_FAST", rffi.UCHAR)
    CALL_METHOD_DESCRIPTOR_FAST_WITH_KEYWORDS = rffi.CConstant("CALL_METHOD_DESCRIPTOR_FAST_WITH_KEYWORDS", rffi.UCHAR)
    CALL_METHOD_DESCRIPTOR_NOARGS = rffi.CConstant("CALL_METHOD_DESCRIPTOR_NOARGS", rffi.UCHAR)
    CALL_METHOD_DESCRIPTOR_O = rffi.CConstant("CALL_METHOD_DESCRIPTOR_O", rffi.UCHAR)
    CALL_NON_PY_GENERAL = rffi.CConstant("CALL_NON_PY_GENERAL", rffi.UCHAR)
    CALL_PY_EXACT_ARGS = rffi.CConstant("CALL_PY_EXACT_ARGS", rffi.UCHAR)
    CALL_PY_GENERAL = rffi.CConstant("CALL_PY_GENERAL", rffi.UCHAR)
    CALL_STR_1 = rffi.CConstant("CALL_STR_1", rffi.UCHAR)
    CALL_TUPLE_1 = rffi.CConstant("CALL_TUPLE_1", rffi.UCHAR)
    CALL_TYPE_1 = rffi.CConstant("CALL_TYPE_1", rffi.UCHAR)
    COMPARE_OP_FLOAT = rffi.CConstant("COMPARE_OP_FLOAT", rffi.UCHAR)
    COMPARE_OP_INT = rffi.CConstant("COMPARE_OP_INT", rffi.UCHAR)
    COMPARE_OP_STR = rffi.CConstant("COMPARE_OP_STR", rffi.UCHAR)
    CONTAINS_OP_DICT = rffi.CConstant("CONTAINS_OP_DICT", rffi.UCHAR)
    CONTAINS_OP_SET = rffi.CConstant("CONTAINS_OP_SET", rffi.UCHAR)
    FOR_ITER_GEN = rffi.CConstant("FOR_ITER_GEN", rffi.UCHAR)
    FOR_ITER_LIST = rffi.CConstant("FOR_ITER_LIST", rffi.UCHAR)
    FOR_ITER_RANGE = rffi.CConstant("FOR_ITER_RANGE", rffi.UCHAR)
    FOR_ITER_TUPLE = rffi.CConstant("FOR_ITER_TUPLE", rffi.UCHAR)
    LOAD_ATTR_CLASS = rffi.CConstant("LOAD_ATTR_CLASS", rffi.UCHAR)
    LOAD_ATTR_GETATTRIBUTE_OVERRIDDEN = rffi.CConstant("LOAD_ATTR_GETATTRIBUTE_OVERRIDDEN", rffi.UCHAR)
    LOAD_ATTR_INSTANCE_VALUE = rffi.CConstant("LOAD_ATTR_INSTANCE_VALUE", rffi.UCHAR)
    LOAD_ATTR_METHOD_LAZY_DICT = rffi.CConstant("LOAD_ATTR_METHOD_LAZY_DICT", rffi.UCHAR)
    LOAD_ATTR_METHOD_NO_DICT = rffi.CConstant("LOAD_ATTR_METHOD_NO_DICT", rffi.UCHAR)
    LOAD_ATTR_METHOD_WITH_VALUES = rffi.CConstant("LOAD_ATTR_METHOD_WITH_VALUES", rffi.UCHAR)
    LOAD_ATTR_MODULE = rffi.CConstant("LOAD_ATTR_MODULE", rffi.UCHAR)
    LOAD_ATTR_NONDESCRIPTOR_NO_DICT = rffi.CConstant("LOAD_ATTR_NONDESCRIPTOR_NO_DICT", rffi.UCHAR)
    LOAD_ATTR_NONDESCRIPTOR_WITH_VALUES = rffi.CConstant("LOAD_ATTR_NONDESCRIPTOR_WITH_VALUES", rffi.UCHAR)
    LOAD_ATTR_PROPERTY = rffi.CConstant("LOAD_ATTR_PROPERTY", rffi.UCHAR)
    LOAD_ATTR_SLOT = rffi.CConstant("LOAD_ATTR_SLOT", rffi.UCHAR)
    LOAD_ATTR_WITH_HINT = rffi.CConstant("LOAD_ATTR_WITH_HINT", rffi.UCHAR)
    LOAD_GLOBAL_BUILTIN = rffi.CConstant("LOAD_GLOBAL_BUILTIN", rffi.UCHAR)
    LOAD_GLOBAL_MODULE = rffi.CConstant("LOAD_GLOBAL_MODULE", rffi.UCHAR)
    LOAD_SUPER_ATTR_ATTR = rffi.CConstant("LOAD_SUPER_ATTR_ATTR", rffi.UCHAR)
    LOAD_SUPER_ATTR_METHOD = rffi.CConstant("LOAD_SUPER_ATTR_METHOD", rffi.UCHAR)
    RESUME_CHECK = rffi.CConstant("RESUME_CHECK", rffi.UCHAR)
    SEND_GEN = rffi.CConstant("SEND_GEN", rffi.UCHAR)
    STORE_ATTR_INSTANCE_VALUE = rffi.CConstant("STORE_ATTR_INSTANCE_VALUE", rffi.UCHAR)
    STORE_ATTR_SLOT = rffi.CConstant("STORE_ATTR_SLOT", rffi.UCHAR)
    STORE_ATTR_WITH_HINT = rffi.CConstant("STORE_ATTR_WITH_HINT", rffi.UCHAR)
    STORE_SUBSCR_DICT = rffi.CConstant("STORE_SUBSCR_DICT", rffi.UCHAR)
    STORE_SUBSCR_LIST_INT = rffi.CConstant("STORE_SUBSCR_LIST_INT", rffi.UCHAR)
    TO_BOOL_ALWAYS_TRUE = rffi.CConstant("TO_BOOL_ALWAYS_TRUE", rffi.UCHAR)
    TO_BOOL_BOOL = rffi.CConstant("TO_BOOL_BOOL", rffi.UCHAR)
    TO_BOOL_INT = rffi.CConstant("TO_BOOL_INT", rffi.UCHAR)
    TO_BOOL_LIST = rffi.CConstant("TO_BOOL_LIST", rffi.UCHAR)
    TO_BOOL_NONE = rffi.CConstant("TO_BOOL_NONE", rffi.UCHAR)
    TO_BOOL_STR = rffi.CConstant("TO_BOOL_STR", rffi.UCHAR)
    UNPACK_SEQUENCE_LIST = rffi.CConstant("UNPACK_SEQUENCE_LIST", rffi.UCHAR)
    UNPACK_SEQUENCE_TUPLE = rffi.CConstant("UNPACK_SEQUENCE_TUPLE", rffi.UCHAR)
    UNPACK_SEQUENCE_TWO_TUPLE = rffi.CConstant("UNPACK_SEQUENCE_TWO_TUPLE", rffi.UCHAR)
    INSTRUMENTED_RESUME = rffi.CConstant("INSTRUMENTED_RESUME", rffi.UCHAR)
    INSTRUMENTED_END_FOR = rffi.CConstant("INSTRUMENTED_END_FOR", rffi.UCHAR)
    INSTRUMENTED_END_SEND = rffi.CConstant("INSTRUMENTED_END_SEND", rffi.UCHAR)
    INSTRUMENTED_RETURN_VALUE = rffi.CConstant("INSTRUMENTED_RETURN_VALUE", rffi.UCHAR)
    INSTRUMENTED_RETURN_CONST = rffi.CConstant("INSTRUMENTED_RETURN_CONST", rffi.UCHAR)
    INSTRUMENTED_YIELD_VALUE = rffi.CConstant("INSTRUMENTED_YIELD_VALUE", rffi.UCHAR)
    INSTRUMENTED_LOAD_SUPER_ATTR = rffi.CConstant("INSTRUMENTED_LOAD_SUPER_ATTR", rffi.UCHAR)
    INSTRUMENTED_FOR_ITER = rffi.CConstant("INSTRUMENTED_FOR_ITER", rffi.UCHAR)
    INSTRUMENTED_CALL = rffi.CConstant("INSTRUMENTED_CALL", rffi.UCHAR)
    INSTRUMENTED_CALL_KW = rffi.CConstant("INSTRUMENTED_CALL_KW", rffi.UCHAR)
    INSTRUMENTED_CALL_FUNCTION_EX = rffi.CConstant("INSTRUMENTED_CALL_FUNCTION_EX", rffi.UCHAR)
    INSTRUMENTED_INSTRUCTION = rffi.CConstant("INSTRUMENTED_INSTRUCTION", rffi.UCHAR)
    INSTRUMENTED_JUMP_FORWARD = rffi.CConstant("INSTRUMENTED_JUMP_FORWARD", rffi.UCHAR)
    INSTRUMENTED_JUMP_BACKWARD = rffi.CConstant("INSTRUMENTED_JUMP_BACKWARD", rffi.UCHAR)
    INSTRUMENTED_POP_JUMP_IF_TRUE = rffi.CConstant("INSTRUMENTED_POP_JUMP_IF_TRUE", rffi.UCHAR)
    INSTRUMENTED_POP_JUMP_IF_FALSE = rffi.CConstant("INSTRUMENTED_POP_JUMP_IF_FALSE", rffi.UCHAR)
    INSTRUMENTED_POP_JUMP_IF_NONE = rffi.CConstant("INSTRUMENTED_POP_JUMP_IF_NONE", rffi.UCHAR)
    INSTRUMENTED_POP_JUMP_IF_NOT_NONE = rffi.CConstant("INSTRUMENTED_POP_JUMP_IF_NOT_NONE", rffi.UCHAR)
    INSTRUMENTED_LINE = rffi.CConstant("INSTRUMENTED_LINE", rffi.UCHAR)
    JUMP = rffi.CConstant("JUMP", rffi.UCHAR)
    JUMP_NO_INTERRUPT = rffi.CConstant("JUMP_NO_INTERRUPT", rffi.UCHAR)
    LOAD_CLOSURE = rffi.CConstant("LOAD_CLOSURE", rffi.UCHAR)
    LOAD_METHOD = rffi.CConstant("LOAD_METHOD", rffi.UCHAR)
    LOAD_SUPER_METHOD = rffi.CConstant("LOAD_SUPER_METHOD", rffi.UCHAR)
    LOAD_ZERO_SUPER_ATTR = rffi.CConstant("LOAD_ZERO_SUPER_ATTR", rffi.UCHAR)
    LOAD_ZERO_SUPER_METHOD = rffi.CConstant("LOAD_ZERO_SUPER_METHOD", rffi.UCHAR)
    POP_BLOCK = rffi.CConstant("POP_BLOCK", rffi.UCHAR)
    SETUP_CLEANUP = rffi.CConstant("SETUP_CLEANUP", rffi.UCHAR)
    SETUP_FINALLY = rffi.CConstant("SETUP_FINALLY", rffi.UCHAR)
    SETUP_WITH = rffi.CConstant("SETUP_WITH", rffi.UCHAR)
    STORE_FAST_MAYBE_NULL = rffi.CConstant("STORE_FAST_MAYBE_NULL", rffi.UCHAR)
    HAVE_ARGUMENT = rffi.CConstant("HAVE_ARGUMENT", rffi.UCHAR)
    MIN_INSTRUMENTED_OPCODE = rffi.CConstant("MIN_INSTRUMENTED_OPCODE", rffi.UCHAR)


# pyerrors.h
PyExc_SystemError = rffi.CConstant("PyExc_SystemError", PyObject_P)
PyExc_TypeError = rffi.CConstant("PyExc_TypeError", PyObject_P)

# traceback.h
PyTraceBack_Here = rffi.llexternal("PyTraceBack_Here", [PyFrameObject_P], rffi.INT, **_llextkws)
PyTraceBack_Print = rffi.llexternal("PyTraceBack_Print", [PyObject_P, PyObject_P], rffi.INT, **_llextkws)

del config
 