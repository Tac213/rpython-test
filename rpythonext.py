#!/usr/bin/env pypy

"""RPython translation usage:

rpythond <translation options> target <targetoptions>

run with --help for more information
"""

from __future__ import print_function, absolute_import, division
import sys, os

# no implicit targets
if len(sys.argv) == 1:
    print(__doc__)
    sys.exit(1)

if sys.platform.startswith("win"):
    from rpython.translator import platform
    platform.Platform.externals = os.path.normpath(os.path.join(__file__, "..", "externals"))
    platform.set_platform("host", None)

if __name__ == "__main__":
    from rpython_ext.translator.goal.translate import cpython_extension_main
    cpython_extension_main()
