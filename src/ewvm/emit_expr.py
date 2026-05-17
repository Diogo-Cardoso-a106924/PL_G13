"""Emissão de expressões: aritmética, lógica, arrays, strings, intrínsecos e chamadas."""
from __future__ import annotations

from .layout import VarLoc
from .types import (
    STRUCT_IDX,
    array_dims,
    char_len_from_type,
    is_char_type,
    literal_val,
    norm_type,
)


class EWVMExprMixin:
    def _push_ref(self, arg):
        if isinstance(arg, str):
            loc = self._resolve(arg)
            if loc.kind == "heap":
                self._push_heap_addr(loc.heap_off)
            else:
                self.e(f"PUSHL {loc.fp_slot}")
            return
        if isinstance(arg, tuple) and arg[0] == "index":
            loc = self._resolve(arg[1])
            self._array_elem_addr(loc, [arg[2]])
            return
        if isinstance(arg, tuple) and arg[0] == "call":
            name, idxs = arg[1], arg[2]
            try:
                loc = self._resolve(name)
                if isinstance(loc.ftype, tuple) and loc.ftype[0] == "array":
                    self._array_elem_addr(loc, idxs)
                    return
            except KeyError:
                pass
        self._expr(arg)

    def _array_elem_addr(self, loc: VarLoc, idxs):
        self._array_offset(loc, idxs)
        self.e(f"PUSHI {loc.heap_off}")
        self.e("ADD")
        self.e(f"PUSHST {STRUCT_IDX}")
        self.e("SWAP")
        self.e("PADD")

    def _is_real(self, ex) -> bool:
        if isinstance(ex, float):
            return True
        if isinstance(ex, (bool, int)):
            return False
        if isinstance(ex, str):
            if ex in self.param_vals:
                return isinstance(self.param_vals[ex], float)
            try:
                return norm_type(self._resolve(ex).ftype) == "REAL"
            except KeyError:
                return False
        if not isinstance(ex, tuple):
            return False
        k = ex[0]
        if k == "neg":
            return self._is_real(ex[1])
        if k in ("+", "-", "*", "/", "**"):
            return self._is_real(ex[1]) or self._is_real(ex[2])
        if k == "call":
            u, args = ex[1], ex[2]
            if u.upper() in ("REAL", "FLOAT", "SIN", "COS"):
                return True
            if u.upper() == "ABS" and len(args) == 1:
                return self._is_real(args[0])
            return norm_type(self.layout.sub_returns.get(u)) == "REAL"
        return False

    def _is_string(self, ex) -> bool:
        if isinstance(ex, tuple) and ex[0] in ("str_lit", "//", "substring_ref"):
            return True
        if isinstance(ex, str):
            try:
                return is_char_type(self._resolve(ex).ftype)
            except KeyError:
                return False
        return False

    def _is_logical(self, ex) -> bool:
        if isinstance(ex, bool):
            return True
        if isinstance(ex, tuple):
            return ex[0] in (
                "OP_NOT",
                ".EQ.",
                ".NE.",
                ".LT.",
                ".LE.",
                ".GT.",
                ".GE.",
                ".AND.",
                ".OR.",
                ".EQV.",
                ".NEQV.",
            )
        if isinstance(ex, str):
            try:
                return norm_type(self._resolve(ex).ftype) == "LOGICAL"
            except KeyError:
                return False
        return False

    def _expr(self, ex, want_float=False):
        if ex is None:
            self.e("PUSHI 0")
            return
        if isinstance(ex, bool):
            self.e(f"PUSHI {1 if ex else 0}")
            return
        if isinstance(ex, int):
            self.e(f"PUSHI {ex}")
            if want_float:
                self.e("ITOF")
            return
        if isinstance(ex, float):
            self.e(f"PUSHF {ex}")
            if not want_float:
                self.e("FTOI")
            return
        if isinstance(ex, str):
            if ex in self.param_vals:
                self._expr(self.param_vals[ex], want_float=want_float)
                return
            loc = self._resolve(ex)
            self._load_var(loc, want_float=(want_float and norm_type(loc.ftype) != "CHARACTER"))
            return
        if not isinstance(ex, tuple):
            self.e("PUSHI 0")
            return

        k = ex[0]
        if k == "str_lit":
            self.e(f'PUSHS "{self._esc(ex[1])}"')
            return
        if k == "neg":
            self._expr(ex[1], want_float=want_float)
            if want_float:
                self.e("PUSHF 0.0")
                self.e("SWAP")
                self.e("FSUB")
            else:
                self.e("PUSHI 0")
                self.e("SWAP")
                self.e("SUB")
            return
        if k == "OP_NOT":
            self._expr(ex[1], want_float=False)
            self.e("NOT")
            return
        if k == "//":
            self._concat(ex[1], ex[2])
            return
        if k == "call":
            self._call_fun(ex, want_float)
            return
        if k == "index":
            self._array_load(ex[1], [ex[2]], want_float)
            return
        if k == "substring_ref":
            self._substring_load(ex)
            return
        if k in ("+", "-", "*", "/", "**"):
            self._arith(k, ex[1], ex[2], want_float)
            return
        if k in (".EQ.", ".NE.", ".LT.", ".LE.", ".GT.", ".GE.", ".AND.", ".OR.", ".EQV.", ".NEQV."):
            self._logic(k, ex[1], ex[2])
            return
        self.e("PUSHI 0")

    def _arith(self, op, a, b, want_float):
        if op == "**":
            wf = want_float or self._is_real(a) or self._is_real(b)
            if wf:
                self._float_pow(a, b)
            else:
                self._int_pow(a, b)
            if wf and not want_float:
                self.e("FTOI")
            elif not wf and want_float:
                self.e("ITOF")
            return
        wf = want_float or self._is_real(a) or self._is_real(b)
        self._expr(a, want_float=wf)
        self._expr(b, want_float=wf)
        f_ops = {"+": "FADD", "-": "FSUB", "*": "FMUL", "/": "FDIV"}
        i_ops = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV"}
        self.e(f_ops[op] if wf else i_ops[op])
        if wf and not want_float:
            self.e("FTOI")
        elif not wf and want_float:
            self.e("ITOF")

    def _int_pow(self, a, b):
        t0, t1 = self.layout.pow_tmp0, self.layout.pow_tmp1
        self._expr(a, want_float=False)
        self._store_cell(t0)
        self._expr(b, want_float=False)
        self._store_cell(t1)
        self.e("PUSHI 1")
        lp, le = self.fresh("PW"), self.fresh("PWE")
        self.e(f"{lp}:")
        self._load_cell(t1)
        self.e(f"JZ {le}")
        self._load_cell(t0)
        self.e("MUL")
        self._load_cell(t1)
        self.e("PUSHI 1")
        self.e("SUB")
        self._store_cell(t1)
        self.e(f"JUMP {lp}")
        self.e(f"{le}:")

    def _float_pow(self, a, b):
        t0, t1 = self.layout.pow_tmp0, self.layout.pow_tmp1
        self._expr(a, want_float=True)
        self._store_cell(t0)
        self._expr(b, want_float=False)
        self._store_cell(t1)
        self.e("PUSHF 1.0")
        lp, le = self.fresh("PFW"), self.fresh("PFWE")
        self.e(f"{lp}:")
        self._load_cell(t1)
        self.e(f"JZ {le}")
        self._load_cell(t0)
        self.e("FMUL")
        self._load_cell(t1)
        self.e("PUSHI 1")
        self.e("SUB")
        self._store_cell(t1)
        self.e(f"JUMP {lp}")
        self.e(f"{le}:")

    def _logic(self, op, a, b):
        if op in (".AND.", ".OR.", ".EQV.", ".NEQV."):
            self._expr(a, want_float=False)
            self._expr(b, want_float=False)
            if op == ".AND.":
                self.e("AND")
            elif op == ".OR.":
                self.e("OR")
            elif op == ".EQV.":
                self.e("EQUAL")
            else:
                self.e("EQUAL")
                self.e("NOT")
            return
        rl = self._is_real(a) or self._is_real(b)
        self._expr(a, want_float=rl)
        self._expr(b, want_float=rl)
        cmp = {
            ".EQ.": ("EQUAL", None),
            ".NE.": ("EQUAL", "NOT"),
            ".LT.": ("FINF" if rl else "INF", None),
            ".LE.": ("FINFEQ" if rl else "INFEQ", None),
            ".GT.": ("FSUP" if rl else "SUP", None),
            ".GE.": ("FSUPEQ" if rl else "SUPEQ", None),
        }
        first, second = cmp[op]
        self.e(first)
        if second:
            self.e(second)

    def _array_offset(self, loc: VarLoc, idxs):
        dims = array_dims(loc.ftype)
        if isinstance(dims, int) or dims is None:
            self._expr(idxs[0], want_float=False)
            self.e("PUSHI 1")
            self.e("SUB")
        else:
            strides, s = [], 1
            for d in dims:
                strides.append(s)
                s *= int(d)
            for j, ix in enumerate(idxs):
                self._expr(ix, want_float=False)
                self.e("PUSHI 1")
                self.e("SUB")
                self.e(f"PUSHI {strides[j]}")
                self.e("MUL")
                if j > 0:
                    self.e("ADD")

    def _array_load(self, name, idxs, want_float):
        loc = self._resolve(name)
        self._array_offset(loc, idxs)
        if loc.kind == "param":
            self.e(f"PUSHL {loc.fp_slot}")
            self.e("SWAP")
            self.e("PADD")
        else:
            self.e(f"PUSHI {loc.heap_off}")
            self.e("ADD")
            self.e(f"PUSHST {STRUCT_IDX}")
            self.e("SWAP")
            self.e("PADD")
        self.e("LOAD 0")
        et = norm_type(loc.ftype[1]) if isinstance(loc.ftype, tuple) and len(loc.ftype) > 1 else None
        if et == "REAL":
            if not want_float:
                self.e("FTOI")
        elif want_float:
            self.e("ITOF")

    def _load_str_ptr(self, ex):
        if isinstance(ex, tuple) and ex[0] == "str_lit":
            self.e(f'PUSHS "{self._esc(ex[1])}"')
        elif isinstance(ex, str):
            self._load_var(self._resolve(ex), want_float=False)
        elif isinstance(ex, tuple) and ex[0] == "//":
            self._concat(ex[1], ex[2])
        elif isinstance(ex, tuple) and ex[0] == "substring_ref":
            self._substring_load(ex)
        else:
            self._expr(ex)

    def _concat(self, a, b):
        self._load_str_ptr(b)
        self._load_str_ptr(a)
        self.e("CONCAT")

    def _substring_load(self, ex):
        _, name, lo, hi, _ln = ex
        loc = self._resolve(name)
        t0, t1 = self.layout.pow_tmp0, self.layout.pow_tmp1
        self._expr(lo if lo is not None else 1, want_float=False)
        self._store_cell(t0)
        if hi is not None:
            self._expr(hi, want_float=False)
        else:
            self._load_var(loc, want_float=False)
            self.e("STRLEN")
        self._store_cell(t1)
        self._load_var(loc, want_float=False)
        self._store_cell(self.layout.str_tmp)
        self.e('PUSHS ""')
        lp, le = self.fresh("SSL"), self.fresh("SSE")
        self.e(f"{lp}:")
        self._load_cell(t0)
        self._load_cell(t1)
        self.e("INFEQ")
        self.e(f"JZ {le}")
        self._load_cell(self.layout.str_tmp)
        self._load_cell(t0)
        self.e("PUSHI 1")
        self.e("SUB")
        self.e("CHARAT")
        self._ascii_code_to_str()
        self.e("SWAP")
        self.e("CONCAT")
        self._load_cell(t0)
        self.e("PUSHI 1")
        self.e("ADD")
        self._store_cell(t0)
        self.e(f"JUMP {lp}")
        self.e(f"{le}:")

    def _call_fun(self, ex, want_float):
        _, name, args, *_ = ex
        try:
            loc = self._resolve(name)
            if isinstance(loc.ftype, tuple) and loc.ftype[0] == "array":
                self._array_load(name, args, want_float)
                return
        except KeyError:
            pass

        u = name.upper()

        if u == "MOD" and len(args) == 2:
            self._expr(args[0])
            self._expr(args[1])
            self.e("MOD")
            return

        if u == "ABS" and len(args) == 1:
            wf = want_float or self._is_real(args[0])
            self._expr(args[0], want_float=wf)
            self.e("DUP 1")
            ls = self.fresh("ABS")
            if wf:
                self.e("PUSHF 0.0")
                self.e("FINF")
                self.e(f"JZ {ls}")
                self.e("PUSHF 0.0")
                self.e("SWAP")
                self.e("FSUB")
            else:
                self.e("PUSHI 0")
                self.e("INF")
                self.e(f"JZ {ls}")
                self.e("PUSHI 0")
                self.e("SWAP")
                self.e("SUB")
            self.e(f"{ls}:")
            return

        if u == "INT" and len(args) == 1:
            self._expr(args[0], want_float=False)
            if want_float:
                self.e("ITOF")
            return

        if u == "REAL" and len(args) == 1:
            self._expr(args[0], want_float=True)
            if not want_float:
                self.e("FTOI")
            return

        if u == "SIN" and len(args) == 1:
            self._expr(args[0], want_float=True)
            self.e("FSIN")
            if not want_float:
                self.e("FTOI")
            return

        if u == "COS" and len(args) == 1:
            self._expr(args[0], want_float=True)
            self.e("FCOS")
            if not want_float:
                self.e("FTOI")
            return

        if u == "LEN" and len(args) == 1:
            self._load_str_ptr(args[0])
            self.e("STRLEN")
            return

        for arg in args:
            self._push_ref(arg)
        self.e(f"PUSHA {self.entry_labels.get(name, self._safe_label(name))}")
        self.e("CALL")

        rt = self.layout.sub_returns.get(name)
        if norm_type(rt) == "REAL":
            if not want_float:
                self.e("FTOI")
        else:
            if want_float:
                self.e("ITOF")
