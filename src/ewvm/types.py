"""Tipos AST, constantes da VM e funções puras partilhadas pelo layout e emissor EWVM."""
from __future__ import annotations

from typing import Any

Node = Any
STRUCT_IDX = 0
ASCII_TABLE_SIZE = 128


def merge_common_segments(parts):
    if not parts:
        return []
    merged = []
    cur_name, cur_vl = parts[0][0], list(parts[0][1])
    for name, vl in parts[1:]:
        if name == cur_name:
            cur_vl.extend(vl)
        else:
            merged.append((cur_name, cur_vl))
            cur_name, cur_vl = name, list(vl)
    merged.append((cur_name, cur_vl))
    return merged


def common_key(name):
    return name if name else "__BLANK__"


def norm_type(t):
    if t is None:
        return None
    if isinstance(t, tuple):
        if t[0] == "CHARACTER":
            return "CHARACTER"
        if t[0] == "array":
            return norm_type(t[1])
    return t if isinstance(t, str) else None


def char_len_from_type(t):
    if isinstance(t, tuple) and t[0] == "CHARACTER":
        return int(t[1]) if t[1] else 1
    if t == "CHARACTER":
        return 1
    if isinstance(t, tuple) and t[0] == "array":
        return char_len_from_type(t[1])
    return None


def is_char_type(t):
    return norm_type(t) == "CHARACTER"


def array_dims(ftype):
    if isinstance(ftype, tuple) and ftype[0] == "array":
        d = ftype[2]
        return [int(x) for x in d] if isinstance(d, list) else int(d)
    return None


def array_cells(ftype):
    d = array_dims(ftype)
    if d is None:
        return 1
    if isinstance(d, int):
        return d
    n = 1
    for x in d:
        n *= int(x)
    return n


def fortran_offset_1based(dims, idxs):
    if isinstance(dims, int):
        return idxs[0] - 1
    off, stride = 0, 1
    for j in range(len(dims)):
        off += (idxs[j] - 1) * stride
        stride *= int(dims[j])
    return off


def literal_val(expr):
    if isinstance(expr, (bool, int, float)):
        return expr
    if isinstance(expr, tuple) and expr and expr[0] == "str_lit":
        return expr[1]
    if isinstance(expr, tuple) and expr[0] == "neg":
        v = literal_val(expr[1])
        if isinstance(v, (int, float)):
            return -v
    return None
