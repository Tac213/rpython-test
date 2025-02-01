#!/usr/bin/env pypy

"""RPython translation usage:

rpythond <translation options> target <targetoptions>

run with --help for more information
"""

from __future__ import print_function, absolute_import, division
import sys, os
from rpython.translator.goal.translate import main

# no implicit targets
if len(sys.argv) == 1:
    print(__doc__)
    sys.exit(1)

if sys.platform.startswith("win"):
    from rpython.translator import platform
    platform.Platform.externals = os.path.normpath(os.path.join(__file__, "..", "externals"))
    platform.set_platform("host", None)

try:
    import debugpy
except ImportError:
    pass
else:
    debugpy.listen(("localhost", 8142))
    print("Waiting for a debugging client to attach on the process, localhost:8142")
    debugpy.wait_for_client()

main()
