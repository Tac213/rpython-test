# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division

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

Py_INCREF = rffi.llexternal("Py_INCREF", [PyObject_P], lltype.Void, **_llextkws)
Py_DECREF = rffi.llexternal("Py_DECREF", [PyObject_P], lltype.Void, **_llextkws)
Py_XINCREF = rffi.llexternal("Py_XINCREF", [PyObject_P], lltype.Void, **_llextkws)
Py_XDECREF = rffi.llexternal("Py_XDECREF", [PyObject_P], lltype.Void, **_llextkws)

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

_FRAME_ECI = ExternalCompilationInfo(
    pre_include_bits=_ECI.pre_include_bits,
    post_include_bits=[
        "#ifndef Py_BUILD_CORE  // {}".format(__file__),
        "#define Py_BUILD_CORE  // {}".format(__file__),
        "#endif  // {}.{}".format(__file__, 0),
        "#include <internal/pycore_frame.h>  // {}".format(__file__),
        "#ifdef Py_BUILD_CORE  // {}".format(__file__),
        "#undef Py_BUILD_CORE  // {}".format(__file__),
        "#endif  // {}.{}".format(__file__, 1),
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

# Functions in: longobject.h
PyLong_FromLong = rffi.llexternal("PyLong_FromLong", [rffi.LONG], PyObject_P, **_llextkws)
PyLong_AsLong = rffi.llexternal("PyLong_AsLong", [PyObject_P], rffi.LONG, **_llextkws)

# Contants defined in object.h
Py_None = rffi.CConstant("Py_None", PyObject_P)
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

# pyerrors.h
PyExc_SystemError = rffi.CConstant("PyExc_SystemError", PyObject_P)

# traceback.h
PyTraceBack_Here = rffi.llexternal("PyTraceBack_Here", [PyFrameObject_P], rffi.INT, **_llextkws)
PyTraceBack_Print = rffi.llexternal("PyTraceBack_Print", [PyObject_P, PyObject_P], rffi.INT, **_llextkws)

del config
 