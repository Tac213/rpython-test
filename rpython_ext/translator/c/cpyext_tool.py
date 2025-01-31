# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division
try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Optional
    from py._path.local import LocalPath
    from rpython.translator.driver import TranslationContext
    from rpython.translator.c.database import LowLevelDatabase
    from rpython.config.config import Config
    from rpython.memory.gc.hook import GcHooks
    from rpython.rtyper.lltypesystem.lltype import _ptr
    from rpython_ext.translator.driver import CPythonModuleDef

import py
from rpython.translator.c.genc import CBuilder
from rpython.rtyper.lltypesystem.lltype import getfunctionptr
from rpython_ext.tool.cpython_config import get_cpython_eci, get_cpython_site_packages_info


class CPythonExtensionBuilder(CBuilder):
    standalone = False
    split = True

    def __init__(self, translator, config, module_def, gchooks=None, name=None):
        # type: (TranslationContext, Config, CPythonModuleDef, Optional[GcHooks], Optional[str]) -> None
        super(CPythonExtensionBuilder, self).__init__(translator, None, config, gchooks=gchooks)
        self.ext_module_def = module_def
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
            func_ptrs.append(getfunctionptr(graph))
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

        # Methods define
        assert self.modulename
        methods_define_identifier = "{}_cpy_methods".format(self.modulename)
        print(file=fp)
        print("static PyMethodDef {}[] = {{".format(methods_define_identifier), file=fp)
        print("\t{NULL, NULL, 0, NULL}  /* Sentinel */", file=fp)
        print("};", file=fp)

        # Module table
        module_table_identifier = "{}_cpy_module".format(self.modulename)
        print(file=fp)
        print("static struct PyModuleDef {} = {{".format(module_table_identifier), file=fp)
        print("\tPyModuleDef_HEAD_INIT,", file=fp)
        print("\t\"{}\",  /* name of module */".format(self.modulename), file=fp)
        print("\t\"Built by RPython.\",  /* module documentation, may be NULL */".format(self.modulename), file=fp)
        print("\t-1,  /* size of per-interpreter state of the module, or -1 if the module keeps state in global variables. */".format(self.modulename), file=fp)
        print("\t{}  /* module documentation, may be NULL */".format(methods_define_identifier), file=fp)
        print("};", file=fp)

        # Module export function
        print(file=fp)
        print("PyMODINIT_FUNC", file=fp)
        print("PyInit_{}(void)".format(self.modulename), file=fp)
        print("{", file=fp)
        print("\tRPython_StartupCode();".format(module_table_identifier), file=fp)
        print("\treturn PyModule_Create(&{});".format(module_table_identifier), file=fp)
        print("}", file=fp)

        fp.close()
