"""Operações de baixo nível: etiquetas, heap, células, variáveis e tabela ASCII."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .layout import ProgramLayout, VarLoc
from .types import ASCII_TABLE_SIZE, Node, STRUCT_IDX, norm_type


class EWVMEmitCoreMixin:
    def __init__(self, ast, layout: ProgramLayout):
        self.ast = ast
        self.layout = layout
        self.lines: List[str] = []
        self.lbl = 0
        self.sub_name: Optional[str] = None
        self.locals: Dict[str, VarLoc] = {}
        self.param_vals: Dict[str, Any] = {}
        self.entry_labels: Dict[str, str] = {}
        self.do_stack: List[int] = []
        self.deferred_after_do: Dict[int, List[Node]] = {}

    def fresh(self, h="L") -> str:
        self.lbl += 1
        return f"{h.upper()}{self.lbl}"

    def e(self, s: str):
        self.lines.append(s)

    @staticmethod
    def _safe_label(name: str) -> str:
        return re.sub(r"[^A-Za-z0-9]", "X", name.upper())

    def _esc(self, s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    def _push_heap_addr(self, cell: int):
        self.e(f"PUSHST {STRUCT_IDX}")
        self.e(f"PUSHI {cell}")
        self.e("PADD")

    def _load_cell(self, cell: int):
        self._push_heap_addr(cell)
        self.e("LOAD 0")

    def _store_cell(self, cell: int):
        self._push_heap_addr(cell)
        self.e("SWAP")
        self.e("STORE 0")

    def _init_ascii_table(self):
        # NUL, LF, CR, aspas: string vazia na tabela para não partir o literal EWVM.
        bad_idx = {0, 10, 13, 34}
        base = self.layout.ascii_table_base
        for i in range(ASCII_TABLE_SIZE):
            if i in bad_idx:
                self.e('PUSHS ""')
            else:
                ch = chr(i).replace("\\", "\\\\")
                self.e(f'PUSHS "{ch}"')
            self._store_cell(base + i)

    def _ascii_code_to_str(self):
        base = self.layout.ascii_table_base
        self.e(f"PUSHI {base}")
        self.e("ADD")
        self.e(f"PUSHST {STRUCT_IDX}")
        self.e("SWAP")
        self.e("PADD")
        self.e("LOAD 0")

    def _resolve(self, name: str) -> VarLoc:
        return self.locals[name] if self.sub_name and name in self.locals else self.layout.globals[name]

    def _load_var(self, loc: VarLoc, want_float=False):
        # REAL na célula: FTOI/ITOF conforme o contexto da expressão.
        if loc.kind == "heap":
            self._load_cell(loc.heap_off)
        elif loc.kind == "param":
            self.e(f"PUSHL {loc.fp_slot}")
            self.e("LOAD 0")
        else:
            self.e(f"PUSHL {loc.fp_slot}")

        nt = norm_type(loc.ftype)
        if nt == "REAL":
            if not want_float:
                self.e("FTOI")
        elif nt not in ("CHARACTER", None):
            if want_float:
                self.e("ITOF")

    def _store_var(self, loc: VarLoc):
        if loc.kind == "heap":
            self._store_cell(loc.heap_off)
        elif loc.kind == "param":
            self.e(f"PUSHL {loc.fp_slot}")
            self.e("SWAP")
            self.e("STORE 0")
        else:
            self.e(f"STOREL {loc.fp_slot}")
