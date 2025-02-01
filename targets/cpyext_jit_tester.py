# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division
import sys
import os
import time

import cpyext_jit


def load_cpyext_jit_extension_module():
    import site
    from importlib import machinery, util
    targetpath = ""
    dirs = site.getsitepackages()
    name = "cpyext_jit"
    for candidate in dirs:
        if not candidate.endswith("site-packages"):
            continue
        for suffix in machinery.EXTENSION_SUFFIXES:
            file_name = "{}{}".format(name, suffix)
            file_path = os.path.join(candidate, file_name)
            if os.path.isfile(file_path):
                targetpath = file_path
                break
        if targetpath:
            break
    if not targetpath:
        raise EnvironmentError("No {} extension module can be found.".format(name))
    loader = machinery.ExtensionFileLoader(name, targetpath)
    spec = util.spec_from_file_location(name, targetpath, loader=loader)
    assert spec, "Failed to load module spec for target spec: {}".format(targetpath)
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    # type: () -> int
    global cpyext_jit
    if "--jit" in sys.argv:
        cpyext_jit = load_cpyext_jit_extension_module()
    t0 = time.time()
    cpyext_jit.entry_point(9999, 9999)
    print(time.time() - t0)
    print(cpyext_jit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
