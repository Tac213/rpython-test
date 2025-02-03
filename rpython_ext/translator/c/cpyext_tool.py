# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division
try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False
from collections import namedtuple
if TYPE_CHECKING:
    from typing import Optional, TextIO, Iterable
    import types
    from py._path.local import LocalPath
    from rpython.translator.driver import TranslationContext
    from rpython.translator.c.database import LowLevelDatabase
    from rpython.config.config import Config
    from rpython.memory.gc.hook import GcHooks
    from rpython.rtyper.lltypesystem.lltype import _ptr
    from rpython_ext.translator.driver import CPythonModuleDef

import py
from rpython.translator.c.genc import CBuilder, log
from rpython.rtyper.lltypesystem import lltype
from rpython_ext.tool.cpython_config import get_cpython_eci, get_cpython_site_packages_info


_METH_VARARGS = 0x0001
_METH_KEYWORDS = 0x0002
_METH_NOARGS = 0x0004
_METH_O = 0x0008

_METH_CLASS = 0x0010
_METH_STATIC = 0x0020

_MethodInfo = namedtuple(
    "_MethodInfo",
    [
        "method_name",
        "c_func_name",
        "py_func_c_name",
        "func_ptr_type_name",
        "interface",
        "interface_code",
        "doc",
    ],
)


class CPythonExtensionBuilder(CBuilder):
    standalone = False
    split = True

    def __init__(self, translator, config, module_def, eval_frame_func=None, gchooks=None, name=None):
        # type: (TranslationContext, Config, CPythonModuleDef, Optional[types.FunctionType], Optional[GcHooks], Optional[str]) -> None
        super(CPythonExtensionBuilder, self).__init__(translator, None, config, gchooks=gchooks)
        self.ext_module_def = module_def
        self.eval_frame_func = eval_frame_func
        self.name = name
        self.so_name = py.path.local("")  # type: LocalPath
        version_info, eci = get_cpython_eci()
        self.cpy_version_info = version_info
        self.cpy_eci = eci
        ext_suffixes, site_packages_dir = get_cpython_site_packages_info()
        self.ext_suffixes = ext_suffixes
        self.site_packages_dir = site_packages_dir

    def getentrypointptr(self):
        # type: () -> list[_ptr]
        func_ptrs = []  # type: list[_ptr]
        bk = self.translator.annotator.bookkeeper
        for func, _ in self.ext_module_def.values():
            graph = bk.getdesc(func).getuniquegraph()
            func_ptrs.append(lltype.getfunctionptr(graph))
        if self.eval_frame_func:
            graph = bk.getdesc(self.eval_frame_func).getuniquegraph()
            func_ptrs.append(lltype.getfunctionptr(graph))
        return func_ptrs

    def gen_makefile(self, targetdir, exe_name=None, headers_to_precompile=None):
        # type: (LocalPath, Optional[str], Optional[list[str]]) -> None
        pass

    def compile(self):
        # type: () -> None
        self.eci = self.eci.merge(self.cpy_eci)
        files = [self.c_source_filename] + self.extrafiles
        files += self.eventually_copy(self.eci.separate_module_files)
        self.eci.separate_module_files = ()
        oname = self.name
        so_ext = self.translator.platform.so_ext
        ext_suffix = self.ext_suffixes[0]
        if ext_suffix.startswith("."):
            ext_suffix = ext_suffix[1:]  # remove '.'
        self.translator.platform.so_ext = ext_suffix
        self.so_name = self.translator.platform.compile(
            files,
            self.eci,
            outputfilename=oname,
            standalone=False,
        )
        self.translator.platform.so_ext = so_ext

    def get_entry_point(self):
        # type: () -> LocalPath
        return self.so_name

    def generate_source(self, db, defines=None, exe_name=None):
        # type: (LowLevelDatabase, Optional[dict[str, int]], Optional[str]) -> LocalPath
        cfile = super(CPythonExtensionBuilder, self).generate_source(db, defines, exe_name)  # type: LocalPath
        self._generate_source_for_cpyext(cfile, db)
        return cfile

    def _generate_source_for_cpyext(self, cfile, db):
        # type: (LocalPath, LowLevelDatabase) -> None
        fp = cfile.open("a")
        print(file=fp)
        print('/***********************************************************/', file=fp)
        print('/***  Code for CPython Extension                         ***/', file=fp)

        # includes
        print(file=fp)
        for pre_include_bit in self.cpy_eci.pre_include_bits:
            print(pre_include_bit, file=fp)
        print("#include <Python.h>", file=fp)

        # Methods definition
        assert self.modulename
        methods_info = []  # type: list[_MethodInfo]
        for method_name in self.ext_module_def:
            methods_info.append(self._gen_cpython_method(fp, db, method_name))
        methods_info.extend(self._gen_eval_frame_func_methods(fp, db))
        methods_define_identifier = "{}_cpy_methods".format(self.modulename)
        print(file=fp)
        print("static PyMethodDef {}[] = {{".format(methods_define_identifier), file=fp)
        for mi in methods_info:
            print("\t{{\"{}\", ({}){}, {}, \"{}\"}},".format(mi.method_name, mi.func_ptr_type_name, mi.py_func_c_name, mi.interface_code, mi.doc), file=fp)
        print("\t{NULL, NULL, 0, NULL}  /* Sentinel */", file=fp)
        print("};", file=fp)

        # Module table
        module_table_identifier = "{}_cpy_module".format(self.modulename)
        print(file=fp)
        print("static struct PyModuleDef {} = {{".format(module_table_identifier), file=fp)
        print("\t.m_base = PyModuleDef_HEAD_INIT,", file=fp)
        print("\t.m_name = \"{}\",  /* name of module */".format(self.modulename), file=fp)
        print("\t.m_doc = \"Built by RPython.\",  /* module documentation, may be NULL */".format(self.modulename), file=fp)
        print("\t.m_size = -1,  /* size of per-interpreter state of the module, or -1 if the module keeps state in global variables. */".format(self.modulename), file=fp)
        print("\t.m_methods = {}".format(methods_define_identifier), file=fp)
        print("};", file=fp)

        # Module export function
        print(file=fp)
        print("PyMODINIT_FUNC", file=fp)
        print("PyInit_{}(void)".format(self.modulename), file=fp)
        print("{", file=fp)
        print("\tRPython_StartupCode();", file=fp)
        print("\tPyObject *m;", file=fp)
        print("\tm = PyModule_Create(&{});".format(module_table_identifier), file=fp)
        print("\tif (m == NULL)", file=fp)
        print("\t\treturn NULL;", file=fp)
        print("\treturn m;", file=fp)
        print("}", file=fp)

        fp.close()

    def _gen_cpython_method(self, fp, db, method_name):
        # type: (TextIO, LowLevelDatabase, str) -> _MethodInfo
        func, input_types = self.ext_module_def[method_name]

        bk = self.translator.annotator.bookkeeper
        graph = bk.getdesc(func).getuniquegraph()
        return_type = graph.returnblock.inputargs[0].concretetype
        c_func_name = db.get(lltype.getfunctionptr(graph))

        assert self.modulename
        py_func_c_name = "{}_{}".format(self.modulename, method_name)

        print(file=fp)
        print("static PyObject *", file=fp)
        args_code = ""
        func_code = func.__code__

        # Parse args
        if func_code.co_argcount == 0:
            interface = _METH_NOARGS
            interface_code = "METH_NOARGS"
            func_ptr_type_name = "PyCFunction"
            print("{}(PyObject *self, PyObject *Py_UNUSED(unused))".format(py_func_c_name), file=fp)
            print("{", file=fp)
        elif func_code.co_argcount == 1:
            interface = _METH_O
            interface_code = "METH_O"
            func_ptr_type_name = "PyCFunction"
            py_arg_name = func_code.co_varnames[0]
            print("{}(PyObject *self, PyObject *{})".format(py_func_c_name, py_arg_name), file=fp)
            print("{", file=fp)
            arg_name = "c_{}".format(py_arg_name)
            args_code = arg_name
            input_type = input_types[0]
            if input_type is bool:
                print("\tbool {} = PyObject_IsTrue({});".format(arg_name, py_arg_name), file=fp)
            elif input_type is int:
                print("\tlong {} = PyLong_AsLong({});".format(arg_name, py_arg_name), file=fp)
                print("\tif (PyErr_Occurred()) {", file=fp)
                print("\t\tPyErr_Print();", file=fp)
                print("\t\tNULL;", file=fp)
                print("\t}", file=fp)
            elif input_type is float:
                print("\tdouble {} = PyFloat_AsDouble({});".format(arg_name, py_arg_name), file=fp)
                print("\tif (PyErr_Occurred()) {", file=fp)
                print("\t\tPyErr_Print();", file=fp)
                print("\t\tNULL;", file=fp)
                print("\t}", file=fp)
            elif input_type is str:
                print("\tconst wchar_t *{} = PyUnicode_AsWideCharString({}, NULL);".format(arg_name, py_arg_name), file=fp)
                print("\tif (PyErr_Occurred()) {", file=fp)
                print("\t\tPyErr_Print();", file=fp)
                print("\t\tNULL;", file=fp)
                print("\t}", file=fp)
            else:
                log.WARNING("Unknown arg type {} of method {}".format(input_type, method_name))
                print("\tPyObject *{} = {};".format(arg_name, py_arg_name), file=fp)
        else:
            interface = _METH_VARARGS | _METH_KEYWORDS
            interface_code = "METH_VARARGS | METH_KEYWORDS"
            func_ptr_type_name = "PyCFunctionWithKeywords"
            print("{}(PyObject *self, PyObject *args, PyObject *kwargs)".format(py_func_c_name), file=fp)
            print("{", file=fp)
            args_format = ""
            arg_names = []  # type: list[str]
            py_arg_names = []  # type: list[str]
            for arg_index, input_type in enumerate(input_types):
                py_arg_name = func_code.co_varnames[arg_index]
                py_arg_names.append("\"{}\"".format(py_arg_name))
                arg_name = "c_{}".format(py_arg_name)
                arg_names.append(arg_name)
                if input_type is bool:
                    args_format += "p"
                    print("\tint {};".format(arg_name), file=fp)
                elif input_type is int:
                    args_format += "l"
                    print("\tlong {};".format(arg_name), file=fp)
                elif input_type is float:
                    args_format += "d"
                    print("\tdouble {};".format(arg_name), file=fp)
                elif input_type is str:
                    args_format += "s"
                    print("\tconst char *{};".format(arg_name), file=fp)
                else:
                    log.WARNING("Unknown arg type {} of method {}".format(input_type, method_name))
                    args_format += "O"
                    print("\tPyObject *{};".format(arg_name), file=fp)
            args_code = ", ".join(arg_names)
            print("\tstatic char* kwlist[] = {{{}, NULL}};".format(", ".join(py_arg_names)), file=fp)
            print(file=fp)
            print("\tif (!PyArg_ParseTupleAndKeywords(args, kwargs, \"{}\", kwlist, {}))".format(args_format, ", ".join("&{}".format(arg_name) for arg_name in arg_names)), file=fp)
            print("\t\treturn NULL;", file=fp)

        # Call c-function and return value
        if return_type is lltype.Void:
            print("\t{}({});".format(c_func_name, args_code), file=fp)
            print("\tPy_RETURN_NONE;", file=fp)
        elif return_type is lltype.Bool:
            print("\tbool ret = {}({});".format(c_func_name, args_code), file=fp)
            print("\tif (ret)", file=fp)
            print("\t\tPy_RETURN_TRUE;", file=fp)
            print("\tPy_RETURN_FALSE;", file=fp)
        elif return_type is lltype.Signed:
            print("\tlong ret = {}({});".format(c_func_name, args_code), file=fp)
            print("\treturn PyLong_FromLong(ret);", file=fp)
        elif return_type is lltype.Unsigned:
            print("\tunsigned long ret = {}({});".format(c_func_name, args_code), file=fp)
            print("\treturn PyLong_FromUnsignedLong(ret);", file=fp)
        elif return_type is lltype.Float:
            print("\tdouble ret = {}({});".format(c_func_name, args_code), file=fp)
            print("\treturn PyFloat_FromDouble(ret);", file=fp)
        else:
            log.WARNING("Unkown return type {} of method '{}', fall back to None.".format(return_type, method_name))
            print("\t{}({});".format(c_func_name, args_code), file=fp)
            print("\tPy_RETURN_NONE;", file=fp)
        print("}", file=fp)

        doc = func.__doc__ or ""
        doc = doc.replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
        return _MethodInfo(
            method_name,
            c_func_name,
            py_func_c_name,
            func_ptr_type_name,
            interface,
            interface_code,
            doc,
        )

    def _gen_eval_frame_func_methods(self, fp, db):
        # type: (TextIO, LowLevelDatabase) -> Iterable[_MethodInfo]
        if not self.eval_frame_func:
            return
        bk = self.translator.annotator.bookkeeper
        graph = bk.getdesc(self.eval_frame_func).getuniquegraph()
        ceval_frame_func_c_name = db.get(lltype.getfunctionptr(graph))

        # Same for each method
        c_func_name = ""
        func_ptr_type_name = "PyCFunction"
        interface = _METH_NOARGS
        interface_code = "METH_NOARGS"

        # Static variable
        print(file=fp)
        print("static _PyFrameEvalFunction s_default_frame_eval_func = NULL;", file=fp)

        assert self.modulename
        method_name = "enable"
        py_func_c_name = "{}_{}".format(self.modulename, method_name)
        print(file=fp)
        print("static PyObject *", file=fp)
        print("{}(PyObject *self, PyObject *Py_UNUSED(unused))".format(py_func_c_name), file=fp)
        print("{", file=fp)
        print("\tPyThreadState *ts = PyThreadState_Get();", file=fp)
        print("\tif (s_default_frame_eval_func == NULL)", file=fp)
        print("\t\ts_default_frame_eval_func = _PyInterpreterState_GetEvalFrameFunc(ts->interp);", file=fp)
        print("\t_PyFrameEvalFunction prev = _PyInterpreterState_GetEvalFrameFunc(ts->interp);", file=fp)
        print("\t_PyInterpreterState_SetEvalFrameFunc(ts->interp, {});".format(ceval_frame_func_c_name), file=fp)
        print("\tif (prev == {})".format(ceval_frame_func_c_name), file=fp)
        print("\t\tPy_RETURN_FALSE;", file=fp)
        print("\tPy_RETURN_TRUE;", file=fp)
        print("}", file=fp)

        doc = "Apply the frame eval function with the pypy JIT compiler."
        yield _MethodInfo(
            method_name,
            c_func_name,
            py_func_c_name,
            func_ptr_type_name,
            interface,
            interface_code,
            doc,
        )

        method_name = "disable"
        py_func_c_name = "{}_{}".format(self.modulename, method_name)
        print(file=fp)
        print("static PyObject *", file=fp)
        print("{}(PyObject *self, PyObject *Py_UNUSED(unused))".format(py_func_c_name), file=fp)
        print("{", file=fp)
        print("\tif (s_default_frame_eval_func == NULL)", file=fp)
        print("\t\tPy_RETURN_FALSE;", file=fp)
        print("\tPyThreadState *ts = PyThreadState_Get();", file=fp)
        print("\t_PyFrameEvalFunction prev = _PyInterpreterState_GetEvalFrameFunc(ts->interp);", file=fp)
        print("\t_PyInterpreterState_SetEvalFrameFunc(ts->interp, s_default_frame_eval_func);", file=fp)
        print("\tif (prev == {})".format(ceval_frame_func_c_name), file=fp)
        print("\t\tPy_RETURN_TRUE;", file=fp)
        print("\tPy_RETURN_FALSE;", file=fp)
        print("}", file=fp)

        doc = "Resume to the default CPython frame eval function."
        yield _MethodInfo(
            method_name,
            c_func_name,
            py_func_c_name,
            func_ptr_type_name,
            interface,
            interface_code,
            doc,
        )

        method_name = "status"
        py_func_c_name = "{}_{}".format(self.modulename, method_name)
        print(file=fp)
        print("static PyObject *", file=fp)
        print("{}(PyObject *self, PyObject *Py_UNUSED(unused))".format(py_func_c_name), file=fp)
        print("{", file=fp)
        print("\tPyThreadState *ts = PyThreadState_Get();", file=fp)
        print("\t_PyFrameEvalFunction prev = _PyInterpreterState_GetEvalFrameFunc(ts->interp);", file=fp)
        print("\tif (prev == {})".format(ceval_frame_func_c_name), file=fp)
        print("\t\tPy_RETURN_TRUE;", file=fp)
        print("\tPy_RETURN_FALSE;", file=fp)
        print("}", file=fp)

        doc = "Check whether the frame eval function with the pypy JIT compiler is applied."
        yield _MethodInfo(
            method_name,
            c_func_name,
            py_func_c_name,
            func_ptr_type_name,
            interface,
            interface_code,
            doc,
        )
