# -*- coding: utf-8 -*-
# author: Tac
# contact: cookiezhx@163.com

from __future__ import print_function, absolute_import, division

from rpython.rlib.rarithmetic import build_int

r_int8 = build_int("r_int8", True, 8)
r_uint8 = build_int("r_uint8", False, 8)

r_int16 = build_int("r_int16", True, 16)
r_uint16 = build_int("r_uint16", False, 16)
