#!/usr/bin/env pypy

"""RPython translation usage:

rpythond <translation options> target <targetoptions>

run with --help for more information
"""

from __future__ import print_function, absolute_import, division
import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(__file__, "..", "pypy")))
from rpython_ext.translator.goal.translate import cpython_extension_main

# no implicit targets
if len(sys.argv) == 1:
    print(__doc__)
    sys.exit(1)

if sys.platform.startswith("win"):
    from rpython.translator.platform.windows import patch_os_env
    patch_os_env(os.path.normpath(os.path.join(__file__, "..", "externals")))


if __name__ == "__main__":
    cpython_extension_main()
