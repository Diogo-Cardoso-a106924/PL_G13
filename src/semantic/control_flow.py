"""Fluxo de controlo: IF, DO, GOTO e operadores unários especiais na AST."""
from symbol_table import SemanticError


class SemanticControlFlowMixin:
    def visit_if(self, node):
        _, cond, then_body, else_body, elseif_chain, lineno = node
        cond_type = self.get_type(cond)
        if cond_type is not None and cond_type != "LOGICAL":
            self.err(f"Condição do IF deve ser LOGICAL, é {cond_type}", lineno)
        self.analyze(cond)
        self.analyze(then_body)
        self.analyze(else_body)
        self.analyze(elseif_chain)

    def visit_elseif(self, node):
        _, cond, body, next_chain, lineno = node
        cond_type = self.get_type(cond)
        if cond_type is not None and cond_type != "LOGICAL":
            self.err(f"Condição do ELSEIF deve ser LOGICAL, é {cond_type}", lineno)
        self.analyze(cond)
        self.analyze(body)
        self.analyze(next_chain)

    def visit_else(self, node):
        self.analyze(node[1])

    def visit_do(self, node):
        _, do_label, var, start, end, step, body, lineno = node
        try:
            _, var_type, _, _ = self.symbols.lookup_var(var)
        except SemanticError:
            self.err(f"Variável de controlo do DO '{var}' não declarada", lineno)
        if var_type not in ("INTEGER", "REAL", None):
            self.err(
                f"Variável de controlo do DO '{var}' deve ser INTEGER ou REAL, é {var_type}",
                lineno,
            )
        if not self._body_defines_label(body, do_label):
            self.err(
                f"DO {do_label}: o corpo deve conter uma instrução com este rótulo "
                f"(terminador do laço, p.ex. CONTINUE)",
                lineno,
            )
        self.analyze(start)
        self.analyze(end)
        self.analyze(step)
        self.symbols.initialize(var)
        self.analyze(body)

    def visit_goto(self, node):
        if node[1] not in self._unit_labels:
            self.err(f"GOTO para {node[1]} não definido", node[2])

    def visit_goto_computed(self, node):
        _, labels, var, lineno = node
        try:
            _, var_type, _, initialized = self.symbols.lookup_var(var)
        except SemanticError:
            self.err(f"Variável '{var}' no GOTO não declarada", lineno)
        if not initialized:
            self.err(f"Variável '{var}' usada no GOTO sem ser inicializada", lineno)
        if var_type is not None and var_type != "INTEGER":
            self.err(f"Variável '{var}' no GOTO deve ser INTEGER (é {var_type})", lineno)
        for lab in labels:
            if lab not in self._unit_labels:
                self.err(f"GOTO computado: {lab} não definido", lineno)

    def visit_neg(self, node):
        self.analyze(node[1])

    def visit_OP_NOT(self, node):
        self.analyze(node[1])

    def visit_concat(self, node):
        _, left, right = node
        self.analyze(left)
        self.analyze(right)
        lt = self._normalize_type(self.get_type(left))
        rt = self._normalize_type(self.get_type(right))
        if lt != "CHARACTER" or rt != "CHARACTER":
            self.err(
                f"Operador '//' só aceita expressões CHARACTER "
                f"(esquerda: {lt!s}, direita: {rt!s})",
            )
