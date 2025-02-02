# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division
import os
try:
    from importlib import machinery, util
except ImportError:
    machinery = None
    util = None
try:
    import imp  # type: ignore
except ImportError:
    imp = None
try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from rpython_ext.translator.driver import CPythonExtensionTranslationDriver, CPythonModuleDef

# We need to import cpybooster manually since the current file and the implementaion module have duplicate names.
_CPYBOOSTER_FILE = os.path.normpath(os.path.join(__file__, "..", "..", "cpybooster", "__init__.py"))
if machinery and util:
    loader = machinery.SourceFileLoader("cpybooster", _CPYBOOSTER_FILE)
    spec = util.spec_from_file_location("cpybooster", _CPYBOOSTER_FILE, loader=loader)
    assert spec
    cpybooster = util.module_from_spec(spec)
    spec.loader.exec_module(cpybooster)
    del loader, spec
else:
    fp, pathname, description = imp.find_module("cpybooster", [os.path.dirname(os.path.dirname(_CPYBOOSTER_FILE))])
    try:
        cpybooster = imp.load_module("cpybooster", fp, pathname, description)
    finally:
        if fp:
            fp.close()
        del fp, pathname, description
del _CPYBOOSTER_FILE


def target(driver, args):
    # type: (CPythonExtensionTranslationDriver, list[str]) -> CPythonModuleDef
    return {
        cpybooster.boost.__name__: (cpybooster.boost, []),
        cpybooster.unboost.__name__: (cpybooster.unboost, []),
    }


jit_entry_point = cpybooster.boost.__name__
