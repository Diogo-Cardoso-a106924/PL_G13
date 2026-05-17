"""Cálculo de layout de memória (heap, frame, COMMON) antes da geração de código."""
from __future__ import annotations

from typing import Any, Dict, List

from .types import (
    ASCII_TABLE_SIZE,
    array_cells,
    char_len_from_type,
    common_key,
    merge_common_segments,
    norm_type,
)


class VarLoc:
    __slots__ = ("kind", "heap_off", "fp_slot", "param_i", "ftype", "char_len")

    def __init__(self, kind, *, heap_off=0, fp_slot=0, param_i=0, ftype=None, char_len=None):
        self.kind = kind
        self.heap_off = heap_off
        self.fp_slot = fp_slot
        self.param_i = param_i
        self.ftype = ftype
        self.char_len = char_len


class ProgramLayout:
    def __init__(self):
        self.heap_cells = 0
        self.globals = {}
        self.fn_result_heap = {}
        self.sub_locals = {}
        self.sub_args = {}
        self.sub_kind = {}
        self.sub_returns = {}
        self.pow_tmp0 = 0
        self.pow_tmp1 = 0
        self.str_tmp = 0
        self.ascii_table_base = 0


class LayoutBuilder:
    def __init__(self, start):
        self.start = start
        self.heap_ptr = 0
        self.common_order = {}
        self.common_block_order = []
        self.globals = {}

    def build(self) -> ProgramLayout:
        prog, subs = self._split(self.start)
        units = ([prog] if prog else []) + subs
        self._scan_common_all(units)

        types_main: Dict[str, Any] = {}
        if prog:
            self._collect_types(prog[2], types_main)

        for key in self.common_block_order:
            for name in self.common_order[key]:
                if name not in self.globals:
                    self._alloc_global(name, types_main.get(name))

        if prog:
            _, _, body, _ = prog
            _, decls, _ = body
            for d in decls:
                self._alloc_decl_globals(d, types_main)

        pl = ProgramLayout()

        for u in subs:
            if u[0] == "function":
                _, ret, fname, _args, _fbody, _ = u
                if fname not in self.globals:
                    self._alloc_global(fname, ret)

        pl.pow_tmp0 = self.heap_ptr
        pl.pow_tmp1 = self.heap_ptr + 1
        pl.str_tmp = self.heap_ptr + 2
        self.heap_ptr += 3

        pl.ascii_table_base = self.heap_ptr
        self.heap_ptr += ASCII_TABLE_SIZE

        pl.heap_cells = max(1, self.heap_ptr)
        pl.globals = dict(self.globals)

        for u in subs:
            if u[0] == "function":
                _, _r, fname, _, _, _ = u
                if fname in self.globals:
                    pl.fn_result_heap[fname] = self.globals[fname].heap_off

        for u in subs:
            if u[0] == "function":
                _, ret, name, args, fbody, _ = u
                pl.sub_kind[name] = "fun"
                pl.sub_returns[name] = ret
                pl.sub_args[name] = list(args)
                pl.sub_locals[name] = self._layout_sub(fbody, args, fname=name)
            else:
                _, name, args, sbody, _ = u
                pl.sub_kind[name] = "sub"
                pl.sub_args[name] = list(args)
                pl.sub_locals[name] = self._layout_sub(sbody, args)

        return pl

    @staticmethod
    def _split(node):
        if len(node) == 2:
            a = node[1]
            return (None, a) if isinstance(a, list) else (a, [])
        return node[1], node[2]

    @staticmethod
    def _unit_body(u):
        k = u[0]
        if k == "program":
            return u[2]
        if k == "function":
            return u[4]
        if k == "subroutine":
            return u[3]
        raise ValueError(f"unidade inválida: {k!r}")

    def _scan_common_all(self, units):
        for u in units:
            self._register_common_body(self._unit_body(u))

    def _register_common_body(self, body):
        _, decls, _ = body
        local: Dict[str, List[str]] = {}
        for d in decls:
            if not isinstance(d, tuple) or d[0] != "common":
                continue
            _, parts, _ = d
            for bname, vl in merge_common_segments(parts):
                key = common_key(bname)
                local.setdefault(key, []).extend(v[1] for v in vl)
        for key, names in local.items():
            if key not in self.common_order:
                self.common_order[key] = names
                self.common_block_order.append(key)

    def _collect_types(self, body, types):
        _, decls, _ = body
        for d in decls:
            self._decl_types(d, types)

    def _decl_types(self, d, types):
        if not isinstance(d, tuple):
            return
        if d[0] == "declaration":
            _, tipo, var_list, _ = d
            for _a, name, adim in var_list:
                if adim is not None:
                    types[name] = ("array", norm_type(tipo) or tipo, self._dims(adim))
                elif isinstance(tipo, tuple) and tipo[0] == "CHARACTER":
                    types[name] = tipo
                else:
                    types[name] = tipo
        elif d[0] == "dimension_list":
            _, pairs, _ = d
            for name, dims in pairs:
                types[name] = ("array", types.get(name), self._dims(dims))
        elif d[0] == "parameter":
            _, pairs, _ = d
            for name, expr in pairs:
                if name not in types:
                    types[name] = self._infer_t(expr)

    @staticmethod
    def _infer_t(expr):
        if isinstance(expr, bool):
            return "LOGICAL"
        if isinstance(expr, int):
            return "INTEGER"
        if isinstance(expr, float):
            return "REAL"
        if isinstance(expr, tuple) and expr[0] == "str_lit":
            return "CHARACTER"
        return None

    @staticmethod
    def _dims(d):
        return [int(x) for x in d] if isinstance(d, list) else int(d)

    def _cells_for_type(self, t):
        return array_cells(t) if isinstance(t, tuple) and t[0] == "array" else 1

    def _alloc_global(self, name, t):
        off = self.heap_ptr
        self.heap_ptr += self._cells_for_type(t)
        self.globals[name] = VarLoc(
            "heap",
            heap_off=off,
            ftype=t,
            char_len=char_len_from_type(t),
        )

    def _alloc_decl_globals(self, d, types):
        if not isinstance(d, tuple):
            return
        names = []
        if d[0] == "declaration":
            _, _tipo, var_list, _ = d
            names = [name for _a, name, _adim in var_list]
        elif d[0] == "dimension_list":
            _, pairs, _ = d
            names = [name for name, _ in pairs]
        elif d[0] == "parameter":
            _, pairs, _ = d
            names = [name for name, _ in pairs]
        for name in names:
            if name not in self.globals and not self._name_in_common(name):
                self._alloc_global(name, types.get(name))

    def _name_in_common(self, name):
        return any(name in ns for ns in self.common_order.values())

    def _resolve_common_loc(self, body, vn):
        _, decls, _ = body
        for d in decls:
            if not isinstance(d, tuple) or d[0] != "common":
                continue
            _, parts, _ = d
            for bname, vl in merge_common_segments(parts):
                key = common_key(bname)
                names = [v[1] for v in vl]
                if vn in names and key in self.common_order:
                    peer = self.common_order[key][names.index(vn)]
                    if peer in self.globals:
                        g = self.globals[peer]
                        return VarLoc(
                            "heap",
                            heap_off=g.heap_off,
                            ftype=g.ftype,
                            char_len=g.char_len,
                        )
        return None

    def _layout_sub(self, body, args, fname=None) -> Dict[str, VarLoc]:
        types: Dict[str, Any] = {}
        self._collect_types(body, types)
        locs: Dict[str, VarLoc] = {}

        n = len(args)
        for i, p in enumerate(args):
            locs[p] = VarLoc(
                "param",
                fp_slot=-(n - i),
                param_i=i,
                ftype=types.get(p),
                char_len=char_len_from_type(types.get(p)),
            )

        frame_i = 0
        _, decls, _ = body

        for d in decls:
            if not isinstance(d, tuple):
                continue

            if d[0] == "common":
                _, parts, _ = d
                for _bn, vl in merge_common_segments(parts):
                    for _x, vn, _y in vl:
                        if vn not in locs:
                            loc = self._resolve_common_loc(body, vn)
                            if loc:
                                locs[vn] = loc

            elif d[0] == "declaration":
                _, tipo, var_list, _ = d
                for _a, vn, adim in var_list:
                    if vn in locs:
                        continue
                    loc = self._resolve_common_loc(body, vn)
                    if loc:
                        locs[vn] = loc
                        continue
                    frame_i += 1
                    tt = ("array", norm_type(tipo) or tipo, self._dims(adim)) if adim else tipo
                    locs[vn] = VarLoc(
                        "frame",
                        fp_slot=-(n + frame_i),
                        ftype=tt,
                        char_len=char_len_from_type(tt),
                    )

            elif d[0] == "dimension_list":
                _, pairs, _ = d
                for vn, dims in pairs:
                    if vn in locs:
                        continue
                    loc = self._resolve_common_loc(body, vn)
                    if loc:
                        locs[vn] = loc
                        continue
                    frame_i += 1
                    tt = ("array", types.get(vn), self._dims(dims))
                    locs[vn] = VarLoc("frame", fp_slot=-(n + frame_i), ftype=tt)

        if fname and fname in self.globals:
            g = self.globals[fname]
            locs[fname] = VarLoc(
                "heap",
                heap_off=g.heap_off,
                ftype=g.ftype,
                char_len=g.char_len,
            )
        return locs
