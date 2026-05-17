"""Emissão do programa completo, DATA inicial, statements e subprogramas."""
from __future__ import annotations

from typing import Any, Dict

from .layout import LayoutBuilder, VarLoc
from .types import (
    STRUCT_IDX,
    array_cells,
    array_dims,
    char_len_from_type,
    fortran_offset_1based,
    literal_val,
    norm_type,
)


class EWVMStmtMixin:
    def generate(self) -> str:
        self.lines = []
        prog, subs = LayoutBuilder._split(self.ast)
        self.entry_labels = {n: self._safe_label(n) for n in self.layout.sub_kind}

        self.e(f"PUSHI {self.layout.heap_cells}")
        self.e("ALLOCN")
        self.e(f"STOREG {STRUCT_IDX}")
        self.e("START")

        ascii_start = self.layout.ascii_table_base
        for cell in range(ascii_start):
            self.e("PUSHI 0")
            self._store_cell(cell)

        self._init_ascii_table()

        if prog:
            _, _, body, _ = prog
            self.sub_name = None
            self.locals = {}
            self.param_vals = self._params_from_body(body)
            self._emit_data_init(body)
            for st in body[2]:
                self._stmt(st)

        self.e("STOP")

        for u in subs:
            self._emit_unit(u)

        return "\n".join(self.lines) + "\n"

    def _params_from_body(self, body) -> Dict[str, Any]:
        _, decls, _ = body
        out = {}
        for d in decls:
            if isinstance(d, tuple) and d[0] == "parameter":
                _, pairs, _ = d
                for name, expr in pairs:
                    v = literal_val(expr)
                    if v is not None:
                        out[name] = v
        return out

    def _emit_data_init(self, body):
        _, decls, _ = body
        for d in decls:
            if isinstance(d, tuple) and d[0] == "data":
                self._data_stmt(d)

    def _data_stmt(self, d):
        _, groups, _ = d
        for objs, raw in groups:
            vals = self._expand_data(raw)
            vi = 0
            for o in objs:
                if o[0] == "whole":
                    loc = self.layout.globals[o[1]]
                    n = array_cells(loc.ftype) if isinstance(loc.ftype, tuple) and loc.ftype[0] == "array" else 1
                    for k in range(n):
                        if vi < len(vals):
                            self._store_lit_at(loc.heap_off + k, vals[vi])
                            vi += 1
                else:
                    nm, idxs = o[1], o[2]
                    loc = self.layout.globals[nm]
                    dims = array_dims(loc.ftype)
                    ii = [int(x) if isinstance(x, int) else int(self.param_vals.get(x, x)) for x in idxs]
                    off = fortran_offset_1based(dims, ii)
                    if vi < len(vals):
                        self._store_lit_at(loc.heap_off + off, vals[vi])
                        vi += 1

    @staticmethod
    def _expand_data(raw):
        out = []
        for x in raw:
            if isinstance(x, tuple) and x[0] == "rep":
                out.extend([x[2]] * int(x[1]))
            else:
                out.append(x)
        return out

    def _store_lit_at(self, cell: int, lit):
        if isinstance(lit, str):
            self.e(f'PUSHS "{self._esc(lit)}"')
        elif isinstance(lit, float):
            self.e(f"PUSHF {lit}")
        elif isinstance(lit, bool):
            self.e(f"PUSHI {1 if lit else 0}")
        else:
            self.e(f"PUSHI {int(lit)}")
        self._store_cell(cell)

    def _stmt(self, st):
        if st is None:
            return
        if isinstance(st, list):
            for x in st:
                self._stmt(x)
            return
        if not isinstance(st, tuple):
            return
        k = st[0]
        dispatch = {
            "labeled": lambda s: (self.e(f"{s[1]}:"), self._stmt(s[2])),
            "body": lambda s: [self._stmt(x) for x in s[2]],
            "assignment": self._stmt_assign,
            "assignment_array": self._stmt_assign_arr,
            "assignment_substring": self._stmt_assign_substr,
            "print": lambda s: self._print(s[2]),
            "write": lambda s: self._print(s[2]),
            "read": lambda s: self._read(s[2]),
            "if": self._if_stmt,
            "do": self._do_stmt,
            "goto": lambda s: self.e(f"JUMP {s[1]}"),
            "goto_computed": self._computed_goto,
            "call_stmt": self._stmt_call,
            "continue": lambda s: self.e("NOP"),
            "return": self._stmt_return,
            "stop": lambda s: self.e("STOP"),
        }
        dispatch.get(k, lambda s: None)(st)

    def _stmt_assign(self, st):
        _, name, expr, _ = st
        loc = self._resolve(name)
        nt = norm_type(loc.ftype)
        if nt == "CHARACTER":
            self._load_str_ptr(expr)
        elif nt == "REAL":
            self._expr(expr, want_float=True)
        else:
            self._expr(expr, want_float=False)
        self._store_var(loc)

    def _stmt_assign_arr(self, st):
        _, name, idxs, expr, _ = st
        loc = self._resolve(name)
        et = norm_type(loc.ftype[1]) if isinstance(loc.ftype, tuple) and len(loc.ftype) > 1 else None
        self._expr(expr, want_float=(et == "REAL"))
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
        self.e("SWAP")
        self.e("STORE 0")

    def _substring_splice(self, loc: VarLoc, lo, hi, emit_middle):
        t0, t1 = self.layout.pow_tmp0, self.layout.pow_tmp1
        str_tmp = self.layout.str_tmp
        self._load_var(loc, want_float=False)
        self._store_cell(str_tmp)
        self.e('PUSHS ""')
        lo_is_one = lo is None or (isinstance(lo, int) and lo == 1)
        if not lo_is_one:
            self.e("PUSHI 1")
            self._store_cell(t0)
            self._expr(lo if lo is not None else 1, want_float=False)
            self.e("PUSHI 1")
            self.e("SUB")
            self._store_cell(t1)
            lp, le = self.fresh("SPRE"), self.fresh("EPRE")
            self.e(f"{lp}:")
            self._load_cell(t0)
            self._load_cell(t1)
            self.e("INFEQ")
            self.e(f"JZ {le}")
            self._load_cell(str_tmp)
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
        emit_middle()
        if hi is not None:
            self._expr(hi, want_float=False)
            self.e("PUSHI 1")
            self.e("ADD")
            self._store_cell(t0)
            self._load_var(loc, want_float=False)
            self.e("STRLEN")
            self._store_cell(t1)
            lp, le = self.fresh("SSUF"), self.fresh("ESUF")
            self.e(f"{lp}:")
            self._load_cell(t0)
            self._load_cell(t1)
            self.e("INFEQ")
            self.e(f"JZ {le}")
            self._load_cell(str_tmp)
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
        self._store_var(loc)

    def _stmt_assign_substr(self, st):
        _, name, lo, hi, ex, _ = st
        loc = self._resolve(name)

        def emit_middle():
            self._load_str_ptr(ex)
            self.e("SWAP")
            self.e("CONCAT")

        self._substring_splice(loc, lo, hi, emit_middle)

    def _read_substring_item(self, it):
        _, name, lo, hi, _ln = it
        loc = self._resolve(name)
        lv = literal_val(lo) if lo is not None else 1
        hv = literal_val(hi) if hi is not None else char_len_from_type(loc.ftype)
        if not isinstance(lv, int) or not isinstance(hv, int) or hv - lv + 1 < 1:
            return

        def emit_middle():
            self.e('PUSHS ""')
            for _ in range(hv - lv + 1):
                self.e("READ")
                self.e("PUSHI 1")
                self.e("CHARAT")
                self._ascii_code_to_str()
                self.e("SWAP")
                self.e("CONCAT")
            self.e("SWAP")
            self.e("CONCAT")

        self._substring_splice(loc, lo, hi, emit_middle)

    def _print(self, items):
        first = True
        for it in items:
            if not first:
                self.e('PUSHS " "')
                self.e("WRITES")
            first = False
            if self._is_string(it):
                self._load_str_ptr(it)
                self.e("WRITES")
            elif self._is_logical(it):
                self._expr(it)
                lt, le = self.fresh("LTRUE"), self.fresh("LEND")
                self.e(f"JZ {lt}")
                self.e('PUSHS ".TRUE."')
                self.e("WRITES")
                self.e(f"JUMP {le}")
                self.e(f"{lt}:")
                self.e('PUSHS ".FALSE."')
                self.e("WRITES")
                self.e(f"{le}:")
            elif self._is_real(it):
                self._expr(it, want_float=True)
                self.e("WRITEF")
            else:
                self._expr(it, want_float=False)
                self.e("WRITEI")
        self.e("WRITELN")

    def _read(self, items):
        for it in items:
            if isinstance(it, str):
                self.e("READ")
                loc = self._resolve(it)
                nt = norm_type(loc.ftype)
                if nt == "REAL":
                    self.e("ATOF")
                elif nt != "CHARACTER":
                    self.e("ATOI")
                self._store_var(loc)
            elif isinstance(it, tuple) and it[0] == "index":
                self.e("READ")
                name, idx = it[1], it[2]
                loc = self._resolve(name)
                et = norm_type(loc.ftype[1]) if isinstance(loc.ftype, tuple) and len(loc.ftype) > 1 else None
                self.e("ATOF" if et == "REAL" else "ATOI")
                self._array_offset(loc, [idx])
                self.e(f"PUSHI {loc.heap_off}")
                self.e("ADD")
                self.e(f"PUSHST {STRUCT_IDX}")
                self.e("SWAP")
                self.e("PADD")
                self.e("SWAP")
                self.e("STORE 0")
            elif isinstance(it, tuple) and it[0] == "substring_ref":
                self._read_substring_item(it)

    def _if_stmt(self, st):
        _, cond, th, el, ech, _ = st
        if el is None and ech is None and not (isinstance(th, tuple) and th[0] == "body"):
            self._expr(cond)
            ls = self.fresh("IFSK")
            self.e(f"JZ {ls}")
            self._stmt(th)
            self.e(f"{ls}:")
            return
        end = self.fresh("ENDIF")
        self._expr(cond)
        lf = self.fresh("IFELS")
        self.e(f"JZ {lf}")
        self._stmt(th)
        self.e(f"JUMP {end}")
        self.e(f"{lf}:")
        if ech is not None:
            self._elif_chain(ech, end)
        elif el is not None:
            self._stmt(el)
        self.e(f"{end}:")

    def _elif_chain(self, node, end):
        if node is None:
            return
        if node[0] == "else":
            self._stmt(node[1])
            return
        _, cond, body, nxt, _ = node
        self._expr(cond)
        ln = self.fresh("ELIF")
        self.e(f"JZ {ln}")
        self._stmt(body)
        self.e(f"JUMP {end}")
        self.e(f"{ln}:")
        self._elif_chain(nxt, end)

    def _do_stmt(self, st):
        _, lab, var, start, end, step, body_stmts, _ = st
        lab_i = int(lab)
        stv = step if step is not None else 1
        loc = self._resolve(var)

        self._expr(start)
        self._store_var(loc)

        term_idx = self._find_do_terminal(body_stmts, lab_i)
        body_core = body_stmts[: term_idx + 1]
        post = body_stmts[term_idx + 1 :]

        own_post, defer_to_outer = [], None
        for s in post:
            if isinstance(s, tuple) and s[0] == "labeled" and int(s[1]) in self.do_stack:
                defer_to_outer = int(s[1])
                self.deferred_after_do.setdefault(defer_to_outer, []).append(s)
            elif defer_to_outer is not None:
                self.deferred_after_do.setdefault(defer_to_outer, []).append(s)
            else:
                own_post.append(s)

        l_top, l_after = self.fresh("DO"), self.fresh("DOAFT")
        self.do_stack.append(lab_i)
        self.e(f"{l_top}:")
        self._load_var(loc)
        self._expr(end)
        self.e("INFEQ" if self._const_step_pos(stv) else "SUPEQ")
        self.e(f"JZ {l_after}")
        for s in body_core:
            self._stmt(s)
        self._load_var(loc)
        self._expr(stv)
        self.e("ADD")
        self._store_var(loc)
        self.e(f"JUMP {l_top}")
        self.e(f"{l_after}:")
        extra = self.deferred_after_do.pop(lab_i, [])
        for s in own_post + extra:
            self._stmt(s)
        self.do_stack.pop()

    @staticmethod
    def _const_step_pos(stv):
        return not isinstance(stv, (int, float)) or stv > 0

    @staticmethod
    def _find_do_terminal(stmts, lab):
        for i, s in enumerate(stmts):
            if isinstance(s, tuple) and s[0] == "labeled" and int(s[1]) == lab:
                return i
        return len(stmts) - 1

    def _computed_goto(self, st):
        _, labels, var, _ = st
        loc = self._resolve(var)
        for j, lb in enumerate(labels):
            self._load_var(loc)
            self.e(f"PUSHI {j + 1}")
            self.e("EQUAL")
            ls = self.fresh("CG")
            self.e(f"JZ {ls}")
            self.e(f"JUMP {lb}")
            self.e(f"{ls}:")

    def _stmt_call(self, st):
        _, name, args, _ = st
        for arg in args:
            self._push_ref(arg)
        self.e(f"PUSHA {self.entry_labels.get(name, self._safe_label(name))}")
        self.e("CALL")

    def _stmt_return(self, st):
        if self.sub_name and self.layout.sub_kind.get(self.sub_name) == "fun":
            self._load_cell(self.layout.fn_result_heap[self.sub_name])
        self.e("RETURN")

    def _emit_unit(self, u):
        is_func = u[0] == "function"
        name = u[2] if is_func else u[1]
        body = u[4] if is_func else u[3]

        self.e(f"{self.entry_labels.get(name, self._safe_label(name))}:")
        self.sub_name = name
        self.locals = self.layout.sub_locals[name]
        self.param_vals = self._params_from_body(body)
        self._emit_data_init(body)

        for st in body[2]:
            self._stmt(st)

        if is_func:
            ho = self.layout.fn_result_heap[name]
            self._load_cell(ho)

        self.e("RETURN")
        self.sub_name = None
        self.locals = {}
