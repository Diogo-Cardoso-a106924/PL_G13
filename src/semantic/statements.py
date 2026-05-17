"""Instruções executáveis: I/O, atribuições, chamadas e acesso a arrays/substrings."""
from symbol_table import SemanticError


class SemanticStatementsMixin:
    def visit_assignment(self, node):
        _, name, expr, lineno = node
        var_type = None
        try:
            kind, var_type, _idx, _init = self.symbols.lookup_var(name)
            if kind == "const":
                self.err(f"Não é possível alterar uma constante: '{name}'", lineno)
        except SemanticError as e:
            if "não é variável" in str(e):
                try:
                    _, var_type, _, _ = self.symbols.lookup_fun(name)
                except SemanticError:
                    self.err(f"Identificador '{name}' não declarado", lineno)
            elif "não declarada" in str(e):
                self.err(f"Variável não declarada: {name}", lineno)
            else:
                raise
        self.analyze(expr)
        expr_type = self.get_type(expr)
        if var_type is not None and expr_type is not None:
            if not self._types_compatible(var_type, expr_type):
                self.err(
                    f"Tipo incompatível na atribuição a '{name}': "
                    f"variável é {var_type} mas expressão é {expr_type}",
                    lineno,
                )
        self.symbols.initialize(name)

    def visit_assignment_array(self, node):
        _, name, indices, value_expr, lineno = node
        try:
            kind, var_type, _, _ = self.symbols.lookup_var(name)
            if kind == "const":
                self.err(f"Não é possível alterar uma constante: '{name}'", lineno)
            if not isinstance(var_type, tuple) or var_type[0] != "array":
                self.err(f"'{name}' não é um array", lineno)
            array_dims = var_type[2]
            expected = len(array_dims) if isinstance(array_dims, list) else 1
            if len(indices) != expected:
                self.err(
                    f"Array '{name}' espera {expected} índice(s), mas recebeu {len(indices)}",
                    lineno,
                )
        except SemanticError as e:
            if "não declarada" in str(e):
                self.err(f"Array '{name}' não declarado", lineno)
            else:
                raise
        for idx_expr in indices:
            self.analyze(idx_expr)
        self.analyze(value_expr)
        expr_type = self.get_type(value_expr)
        base_type = self._normalize_type(var_type)
        if base_type is not None and expr_type is not None:
            if not self._types_compatible(base_type, expr_type):
                self.err(
                    f"Tipo incompatível na atribuição a '{name}': "
                    f"array é {base_type} mas expressão é {expr_type}",
                    lineno,
                )
        self.symbols.initialize(name)

    def visit_print(self, node):
        for expr in node[2]:
            self.analyze(expr)

    def visit_write(self, node):
        for expr in node[2]:
            self.analyze(expr)

    def visit_read(self, node):
        _, _, read_list, lineno = node
        for item in read_list:
            if isinstance(item, str):
                kind, _type, _idx, _init = self.symbols.lookup_var(item)
                if kind == "const":
                    self.err(f"Não é possível ler para uma constante: '{item}'", lineno)
                self.symbols.initialize(item)
            elif isinstance(item, tuple) and item[0] == "substring_ref":
                _, sn, lo, hi, iln = item
                self._validate_substring_target(sn, lo, hi, iln)
                self.symbols.initialize(sn)
            else:
                self.analyze(item)

    def _validate_substring_target(self, name, lo, hi, lineno):
        try:
            kind, var_type, _, _ = self.symbols.lookup_var(name)
        except SemanticError as e:
            if "não declarada" in str(e):
                self.err(f"Variável '{name}' não declarada", lineno)
            raise
        if kind == "const":
            self.err(f"Substring não aplicável a constante '{name}'", lineno)
        if not self._is_character_scalar(var_type):
            self.err(
                f"Substring requer variável CHARACTER escalar (não array): '{name}'",
                lineno,
            )
        for b in (lo, hi):
            if b is None:
                continue
            self.analyze(b)
            bt = self._normalize_type(self.get_type(b))
            if bt is not None and bt not in ("INTEGER", "REAL"):
                self.err(
                    f"Limites de substring de '{name}' devem ser numéricos, é {bt}",
                    lineno,
                )

    def visit_substring_ref(self, node):
        _, name, lo, hi, lineno = node
        self._validate_substring_target(name, lo, hi, lineno)
        _, _, _, initialized = self.symbols.lookup_var(name)
        if not initialized:
            self.err(f"Variável '{name}' usada na substring sem ser inicializada", lineno)

    def visit_assignment_substring(self, node):
        _, name, lo, hi, value_expr, lineno = node
        self._validate_substring_target(name, lo, hi, lineno)
        kind, _var_type, _, _ = self.symbols.lookup_var(name)
        if kind == "const":
            self.err(f"Não é possível alterar uma constante: '{name}'", lineno)
        self.analyze(value_expr)
        vt = self.get_type(value_expr)
        if vt is not None and self._normalize_type(vt) != "CHARACTER":
            self.err(
                f"Atribuição a substring de '{name}': lado direito deve ser CHARACTER",
                lineno,
            )
        self.symbols.initialize(name)

    def visit_index(self, node):
        _, name, expr, lineno = node
        try:
            _, var_type, _, _ = self.symbols.lookup_var(name)
            if not isinstance(var_type, tuple) or var_type[0] != "array":
                self.err(f"'{name}' não é um array", lineno)
        except SemanticError:
            self.err(f"Array '{name}' não declarado", lineno)
        self.symbols.initialize(name)
        self.analyze(expr)

    def _mark_def_from_call_arg(self, arg):
        target = None
        if isinstance(arg, str):
            target = arg
        elif isinstance(arg, tuple) and arg[0] in ("index", "substring_ref"):
            target = arg[1]
        if target:
            self.symbols.initialize(target)

    def _check_call_args(self, name, param_types, args, lineno):
        if len(param_types) != len(args):
            self.err(
                f"'{name}' esperava {len(param_types)} argumentos, mas recebeu {len(args)}",
                lineno,
            )
        for i, (arg, expected_type) in enumerate(zip(args, param_types)):
            if expected_type is not None:
                actual_type = self.get_type(arg)
                if actual_type is not None and not self._types_compatible(expected_type, actual_type):
                    self.err(
                        f"Argumento {i + 1} de '{name}': esperava {expected_type}, recebeu {actual_type}",
                        lineno,
                    )

    def visit_call_stmt(self, node):
        _, name, args, lineno = node
        try:
            kind, _, param_types, _ = self.symbols.lookup_fun(name)
        except SemanticError:
            self.err(f"Subrotina '{name}' não declarada", lineno)
        if kind != "sub":
            self.err(f"CALL só pode invocar subrotinas: '{name}' não é subrotina", lineno)
        self._check_call_args(name, param_types, args, lineno)
        prev = self._call_args_allow_uninit
        self._call_args_allow_uninit = True
        try:
            for arg in args:
                self.analyze(arg)
        finally:
            self._call_args_allow_uninit = prev
        for arg in args:
            self._mark_def_from_call_arg(arg)

    def visit_call(self, node):
        _, name, args, lineno = node
        if name in self.INTRINSICS:
            arity, _ = self.INTRINSICS[name]
            if arity != -1 and arity != len(args):
                self.err(f"'{name}' esperava {arity} argumentos, mas recebeu {len(args)}", lineno)
        else:
            try:
                _, _, param_types, _ = self.symbols.lookup_fun(name)
                self._check_call_args(name, param_types, args, lineno)
            except SemanticError as e:
                if "não declarada" in str(e) or "não é função" in str(e):
                    try:
                        _, type_, _, _ = self.symbols.lookup_var(name)
                        if isinstance(type_, tuple) and type_[0] == "array":
                            array_dims = type_[2]
                            expected = len(array_dims) if isinstance(array_dims, list) else 1
                            if len(args) != expected:
                                self.err(
                                    f"'{name}' espera {expected} índices, recebeu {len(args)}",
                                    lineno,
                                )
                        else:
                            self.err(f"'{name}' não é uma função nem um array", lineno)
                    except SemanticError:
                        self.err(f"'{name}' não declarado", lineno)
                else:
                    raise
        for arg in args:
            self.analyze(arg)
