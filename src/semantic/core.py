"""Motor do analisador semântico: percurso da AST, tipos de expressões, unidades e rótulos."""
from symbol_table import SemanticError, SymbolTable


class SemanticCoreMixin:
    INTRINSICS = {
        "ABS": (1, None),
        "INT": (1, "INTEGER"),
        "REAL": (1, "REAL"),
        "MOD": (2, "INTEGER"),
        "SIN": (1, "REAL"),
        "COS": (1, "REAL"),
        "LEN": (1, "INTEGER"),
    }

    _BINARY_OPS = {
        "+",
        "-",
        "*",
        "/",
        "**",
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
    }

    def __init__(self):
        self.symbols = SymbolTable()
        self.common_blocks = {}
        self._common_pending_unit = None
        self._unit_labels = None
        self._call_args_allow_uninit = False
        self._parameter_values = {}

    def _register_label(self, label, lineno):
        if label in self._unit_labels:
            self.err(
                f"{label} definido mais de uma vez (já na linha {self._unit_labels[label]})",
                lineno,
            )
        self._unit_labels[label] = lineno

    def _walk_labels_in_node(self, node):
        if node is None:
            return
        if isinstance(node, list):
            for item in node:
                self._walk_labels_in_node(item)
            return
        if node[0] == "body":
            self._walk_labels_in_node(node[2])
        elif node[0] == "labeled":
            self._register_label(node[1], node[2][-1])
            self._walk_labels_in_node(node[2])
        elif node[0] == "if":
            _, _c, then_b, else_b, elseif_chain, _ln = node
            self._walk_labels_in_node(then_b)
            self._walk_labels_in_node(else_b)
            self._walk_labels_in_node(elseif_chain)
        elif node[0] == "elseif":
            _, _c, b, next_chain, _ln = node
            self._walk_labels_in_node(b)
            self._walk_labels_in_node(next_chain)
        elif node[0] == "else":
            self._walk_labels_in_node(node[1])
        elif node[0] == "do":
            self._walk_labels_in_node(node[6])

    def _body_defines_label(self, node, label):
        if node is None:
            return False
        if isinstance(node, list):
            return any(self._body_defines_label(s, label) for s in node)
        if node[0] == "labeled":
            return node[1] == label or self._body_defines_label(node[2], label)
        if node[0] == "if":
            _, _c, then_b, else_b, elseif_ch, _ln = node
            return (
                self._body_defines_label(then_b, label)
                or self._body_defines_label(else_b, label)
                or self._body_defines_label(elseif_ch, label)
            )
        if node[0] == "elseif":
            _, _c, b, next_ch, _ln = node
            return self._body_defines_label(b, label) or self._body_defines_label(next_ch, label)
        if node[0] == "else":
            return self._body_defines_label(node[1], label)
        if node[0] == "do":
            return self._body_defines_label(node[6], label)
        if node[0] == "body":
            return self._body_defines_label(node[2], label)
        return False

    def err(self, msg, lineno=None):
        raise SemanticError(f"Linha {lineno}: {msg}" if lineno else msg)

    def analyze(self, node):
        if isinstance(node, list):
            for item in node:
                self.analyze(item)
            return None
        if isinstance(node, str):
            upper = node.upper()
            if upper == node and node.replace("_", "").isalpha():
                try:
                    _, _, _, initialized = self.symbols.lookup_var(node)
                    if not initialized and not self._call_args_allow_uninit:
                        raise SemanticError(f"Variável '{node}' usada sem ser inicializada")
                except SemanticError as e:
                    if "não declarada" in str(e):
                        try:
                            self.symbols.lookup_fun(node)
                        except SemanticError:
                            raise SemanticError(f"Variável '{node}' não declarada")
                    else:
                        raise
            return None
        if isinstance(node, tuple):
            kind = node[0]
            if kind == "//":
                return self.visit_concat(node)
            return getattr(self, f"visit_{kind}")(node)
        return None

    def _normalize_type(self, tipo):
        if tipo is None or isinstance(tipo, list):
            return None
        if isinstance(tipo, tuple):
            if tipo[0] == "CHARACTER":
                return "CHARACTER"
            if tipo[0] == "array":
                return self._normalize_type(tipo[1]) if len(tipo) > 1 else None
        return tipo

    def _is_character_scalar(self, var_type):
        if var_type is None or (isinstance(var_type, tuple) and var_type[0] == "array"):
            return False
        return self._normalize_type(var_type) == "CHARACTER"

    def _types_compatible(self, target, source):
        t, s = self._normalize_type(target), self._normalize_type(source)
        return t == s or (t in {"INTEGER", "REAL"} and s in {"INTEGER", "REAL"})

    def _const_eval_literal(self, expr):
        if isinstance(expr, (bool, int, float)):
            return expr
        if isinstance(expr, tuple) and expr[0] == "str_lit":
            return expr[1]
        if isinstance(expr, tuple) and expr[0] == "neg":
            inner = self._const_eval_literal(expr[1])
            if isinstance(inner, (int, float)):
                return -inner
        return None

    def _resolve_parameter_int(self, dim, lineno, ctx="Dimensão"):
        if isinstance(dim, int):
            return dim
        if not isinstance(dim, str):
            self.err(f"{ctx} inválida: {dim!r}", lineno)

        if dim in self._parameter_values:
            v = self._parameter_values[dim]
            if isinstance(v, int):
                return v
            self.err(f"{ctx}: PARAMETER '{dim}' deve ser INTEGER", lineno)

        try:
            kind, _, _, _ = self.symbols.lookup_var(dim)
        except SemanticError:
            self.err(f"{ctx}: '{dim}' não é PARAMETER conhecida", lineno)
        if kind != "const":
            self.err(f"{ctx}: '{dim}' deve ser PARAMETER", lineno)

        v = self._parameter_values.get(dim)
        if isinstance(v, int):
            return v
        self.err(f"{ctx}: não foi possível resolver o valor inteiro de '{dim}'", lineno)

    def _resolve_dim_spec(self, array_dim, lineno):
        if array_dim is None:
            return None
        if isinstance(array_dim, list):
            return [self._resolve_parameter_int(d, lineno) for d in array_dim]
        return self._resolve_parameter_int(array_dim, lineno)

    def get_type(self, node):
        if node is None:
            return None
        if isinstance(node, bool):
            return "LOGICAL"
        if isinstance(node, int):
            return "INTEGER"
        if isinstance(node, float):
            return "REAL"
        if isinstance(node, str):
            try:
                _, type_, _, _ = self.symbols.lookup_var(node)
                return type_
            except SemanticError:
                try:
                    _, type_, _, _ = self.symbols.lookup_fun(node)
                    return type_
                except SemanticError:
                    return None
        if not isinstance(node, tuple):
            return None
        kind = node[0]
        if kind in (
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
            "OP_NOT",
        ):
            return "LOGICAL"
        if kind == "neg":
            return self.get_type(node[1])
        if kind in ("+", "-", "*", "/", "**"):
            left = self._normalize_type(self.get_type(node[1]))
            right = self._normalize_type(self.get_type(node[2]))
            if left == "REAL" or right == "REAL":
                return "REAL"
            if left == "INTEGER" and right == "INTEGER":
                return "INTEGER"
            return None
        if kind == "//":
            lt = self._normalize_type(self.get_type(node[1]))
            rt = self._normalize_type(self.get_type(node[2]))
            return "CHARACTER" if lt == "CHARACTER" and rt == "CHARACTER" else None
        if kind == "str_lit":
            return "CHARACTER"
        if kind == "call":
            name = node[1]
            if name in self.INTRINSICS:
                return self.INTRINSICS[name][1]
            try:
                _, type_, _, _ = self.symbols.lookup_fun(name)
                return type_
            except SemanticError:
                return None
        if kind == "index":
            try:
                _, type_, _, _ = self.symbols.lookup_var(node[1])
                return type_
            except SemanticError:
                return None
        if kind == "substring_ref":
            return "CHARACTER"
        return None

    def visit_str_lit(self, node):
        return None

    def visit_start(self, node):
        self._collect_subprograms(node)
        for child in node[1:]:
            self.analyze(child)

    def _enter_unit(self, args, body):
        self._parameter_values = {}
        self.symbols.push()
        for arg in args:
            self.symbols.declare_var(arg, None)
            self.symbols.initialize(arg)
        self._unit_labels = {}
        self._walk_labels_in_node(body[2])
        self._common_pending_unit = {}
        self.analyze(body)
        self._finalize_common_pending_unit()
        self._common_pending_unit = None
        self._unit_labels = None
        self.symbols.pop()

    def visit_program(self, node):
        self._enter_unit([], node[2])

    def _extract_param_types(self, args, body):
        tm = {}
        if isinstance(body, tuple) and body[0] == "body":
            for d in body[1]:
                if isinstance(d, tuple) and d[0] == "declaration":
                    for _, vname, _ in d[2]:
                        tm[vname] = d[1]
                elif isinstance(d, tuple) and d[0] == "dimension_list":
                    for name, dims in d[1]:
                        tm[name] = ("array", None, dims)
        return [tm.get(arg) for arg in args]

    def _collect_subprograms(self, node):
        if not isinstance(node, tuple):
            return
        if node[0] == "function":
            try:
                self.symbols.declare_fun(
                    node[2], node[1], self._extract_param_types(node[3], node[4])
                )
            except SemanticError:
                pass
        elif node[0] == "subroutine":
            try:
                self.symbols.declare_sub(node[1], self._extract_param_types(node[2], node[3]))
            except SemanticError:
                pass
        elif node[0] == "start":
            for child in node[1:]:
                if isinstance(child, list):
                    for item in child:
                        self._collect_subprograms(item)
                elif isinstance(child, tuple):
                    self._collect_subprograms(child)

    def visit_function(self, node):
        try:
            self.symbols.declare_fun(
                node[2], node[1], self._extract_param_types(node[3], node[4])
            )
        except SemanticError:
            pass
        self._enter_unit(node[3], node[4])

    def visit_subroutine(self, node):
        try:
            self.symbols.declare_sub(node[1], self._extract_param_types(node[2], node[3]))
        except SemanticError:
            pass
        self._enter_unit(node[2], node[3])

    def visit_body(self, node):
        self.analyze(node[1])
        self.analyze(node[2])

    def visit_labeled(self, node):
        self.analyze(node[2])

    def visit_return(self, node):
        pass

    def visit_continue(self, node):
        pass

    def visit_stop(self, node):
        pass

    def __getattr__(self, name):
        if name.startswith("visit_"):
            op = name[len("visit_") :]
            if len(op) >= 3 and op[0] == "." and op[-1] == ".":
                op = "." + op[1:-1].upper() + "."
            if op in self._BINARY_OPS:

                def _binop(node):
                    self.analyze(node[1])
                    self.analyze(node[2])

                return _binop
        raise AttributeError(name)
