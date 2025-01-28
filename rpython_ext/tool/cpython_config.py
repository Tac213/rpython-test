# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division

import sys
import sysconfig
import os
from collections import namedtuple
try:
    from importlib import machinery, util
except ImportError:
    machinery = None
    util = None
try:
    import imp
except ImportError:
    imp = None
try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False
if TYPE_CHECKING:
    from rpython.translator.tool.cbuild import ExternalCompilationInfo


CPythonLibraryInfo = namedtuple("CPythonLibraryInfo", ["libdir", "lib"])
CPythonVersionInfo = namedtuple("CPythonVersionInfo", ["major", "minor", "micro", "releaselevel", "serial"])



def is_debug():
    # type: () -> bool
    """
    Check whether cpython is debug build
    Returns:
        bool
    """
    debug_suffix = "_d.pyd" if sys.platform == "win32" else "_d.so"
    if machinery:
        return any(s.endswith(debug_suffix) for s in machinery.EXTENSION_SUFFIXES)
    if imp:
        return any(s[0].endswith(debug_suffix) for s in imp.get_suffixes())
    raise RuntimeError("Neither 'importlib.machinery' nor 'imp' could be imported.")


def cpython_version():
    # type: () -> str
    """
    Get cpython version
    Returns:
        str
    """
    return "{}.{}".format(sys.version_info.major, sys.version_info.minor)


def get_cpython_include_path():
    # type: () -> str
    """
    Get cpython include path
    Returns:
        str
    """
    candidate = sysconfig.get_path("include")
    if not os.path.isdir(candidate):
        candidate = os.path.join(sys.base_exec_prefix, "include")
    assert os.path.isdir(candidate), "Can't find cpython include path of {}".format(sys.executable)
    return candidate


def cpython_lib_info(is_libpython3):
    # type: (bool) -> CPythonLibraryInfo
    """
    Get cpython library information
    Args:
        is_libpython3: whether to get libpython3
    Returns:
        CPythonLibraryInfo
    """
    libdir = sysconfig.get_config_var("LIBDIR")
    if libdir is None:
        libdir = os.path.abspath(os.path.join(sysconfig.get_config_var("LIBDEST"), "..", "libs"))
    if is_libpython3:
        assert sys.version_info.major == 3
        version = "3"
        version_no_dots = "3"
    else:
        version = cpython_version()
        version_no_dots = version.replace(".", "")

    lib = ""
    suffix = sysconfig.get_config_var("abi_thread") or ""
    if sys.platform == "win32":
        suffix = "{}_d".format(suffix) if is_debug() else suffix
        lib = "python{}{}".format(version_no_dots, suffix)

    elif sys.platform == "darwin":
        lib = "python{}{}".format(version, suffix)

    # Linux and anything else
    else:
        lib = "python{}{}".format(version, sys.abiflags)  # pylint: disable=no-member

    return CPythonLibraryInfo(libdir, lib)


def cpython_dll_path(is_libpython3):
    # type: (bool) -> str
    """
    Get cpython dll path
    Args:
        is_libpython3: whether to get libpython3
    Returns:
        str
    """
    if not sys.platform.startswith("win"):
        return ""
    if is_libpython3:
        assert sys.version_info.major == 3
        version_no_dots = "3"
    else:
        version = cpython_version()
        version_no_dots = version.replace(".", "")
    suffix = sysconfig.get_config_var("abi_thread") or ""
    suffix = "{}_d".format(suffix) if is_debug() else suffix
    file_name = "python{}{}.dll".format(version_no_dots, suffix)
    file_path = os.path.join(sys.base_exec_prefix, file_name)
    assert os.path.isfile(file_path), "Can't find cpython dll path of {}".format(sys.executable)
    return file_path


def get_cpython_executable():
    # type: () -> str
    """
    Get the path of the cpython executable.
    """
    env_py_exe = os.environ.get("PYTHON_EXECUTABLE", "")
    if os.path.isfile(env_py_exe):
        return env_py_exe
    return sys.executable


def get_cpython_eci():
    # type: () -> tuple[CPythonVersionInfo, ExternalCompilationInfo]
    """
    Get the `ExternalCompilationInfo` of the cpython.
    """
    from rpython.tool.runsubprocess import run_subprocess
    from rpython.translator.tool.cbuild import ExternalCompilationInfo

    cpython_exe = get_cpython_executable()
    file_path = os.path.abspath(__file__)
    if machinery:
        if file_path.endswith(machinery.BYTECODE_SUFFIXES):
            assert util is not None
            file_path = util.source_from_cache(file_path)
    elif imp:
        is_pyc = False
        for suffix, _, flag in imp.get_suffixes():
            if flag == imp.PY_COMPILED and file_path.endswith(suffix):
                is_pyc = True
                break
        if is_pyc:
            if hasattr(imp, "source_from_cache"):
                file_path = imp.source_from_cache(file_path)
            else:
                for suffix, _, flag in imp.get_suffixes():
                    if flag == imp.PY_SOURCE:
                        file_path = "{}{}".format(os.path.splitext(file_path)[0], suffix)
                        break
    status, stdout, stderr = run_subprocess(cpython_exe, [file_path])
    if status != 0:
        raise EnvironmentError(stderr)
    outputs = stdout.splitlines()
    version_info = CPythonVersionInfo(
        major=int(outputs[0]),
        minor=int(outputs[1]),
        micro=int(outputs[2]),
        releaselevel=outputs[3],
        serial=int(outputs[4]),
    )
    pre_include_bits = []
    if version_info < (3, 13):
        pre_include_bits.append("#define PY_SSIZE_T_CLEAN")
    eci = ExternalCompilationInfo(
        pre_include_bits=pre_include_bits,
        includes=["Python.h"],
        include_dirs=[outputs[5]],
        libraries=[outputs[6]],
        library_dirs=[outputs[7]],
    )
    return version_info, eci


def main():
    # type: () -> int
    print(sys.version_info.major, file=sys.stdout)
    print(sys.version_info.minor, file=sys.stdout)
    print(sys.version_info.micro, file=sys.stdout)
    print(sys.version_info.releaselevel, file=sys.stdout)
    print(sys.version_info.serial, file=sys.stdout)
    print(get_cpython_include_path(), file=sys.stdout)
    lib_info = cpython_lib_info(False)
    print(lib_info.lib, file=sys.stdout)
    print(lib_info.libdir, file=sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
