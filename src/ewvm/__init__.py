"""Geração de código para a máquina virtual EWVM (layout de memória + emissor)."""
from .emit_core import EWVMEmitCoreMixin
from .emit_expr import EWVMExprMixin
from .emit_stmt import EWVMStmtMixin
from .layout import LayoutBuilder, ProgramLayout, VarLoc
from .types import (
    ASCII_TABLE_SIZE,
    STRUCT_IDX,
    Node,
    array_cells,
    array_dims,
    char_len_from_type,
    common_key,
    fortran_offset_1based,
    is_char_type,
    literal_val,
    merge_common_segments,
    norm_type,
)


class EWVMCodeGen(EWVMEmitCoreMixin, EWVMExprMixin, EWVMStmtMixin):
    """Emissor completo: heap/vars, expressões, statements e unidades."""

    pass


def generate_ewvm(ast: Node) -> str:
    return EWVMCodeGen(ast, LayoutBuilder(ast).build()).generate()


__all__ = [
    "ASCII_TABLE_SIZE",
    "EWVMCodeGen",
    "LayoutBuilder",
    "Node",
    "ProgramLayout",
    "STRUCT_IDX",
    "VarLoc",
    "array_cells",
    "array_dims",
    "char_len_from_type",
    "common_key",
    "fortran_offset_1based",
    "generate_ewvm",
    "is_char_type",
    "literal_val",
    "merge_common_segments",
    "norm_type",
]
