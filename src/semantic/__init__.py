"""Análise semântica repartida por responsabilidade (ver submódulos ``core``, ``declarations``, etc.)."""
from .control_flow import SemanticControlFlowMixin
from .core import SemanticCoreMixin
from .declarations import SemanticDeclarationsMixin
from .statements import SemanticStatementsMixin


class SemanticAnalyzer(
    SemanticCoreMixin,
    SemanticDeclarationsMixin,
    SemanticStatementsMixin,
    SemanticControlFlowMixin,
):
    """Percurso da AST com verificação de tipos, âmbito e regras estáticas Fortran."""

    pass


__all__ = ["SemanticAnalyzer"]
