"""Declarações estáticas: tipos, DIMENSION, DATA, COMMON, PARAMETER."""
from symbol_table import SemanticError


class SemanticDeclarationsMixin:
    def visit_declaration(self, node):
        _, tipo, var_list, lineno = node
        tipo_canonico = self._normalize_type(tipo)

        for var in var_list:
            _, name, array_dim = var

            outer_kind = self.symbols.outer_proc_kind(name)
            if outer_kind == "sub":
                self.err(f"Declaração de tipo inválida: '{name}' é uma subrotina", lineno)
            if outer_kind == "fun" and array_dim is not None:
                self.err(f"Declaração inválida: '{name}' é uma função", lineno)
            if outer_kind == "fun" and array_dim is None:
                try:
                    _, ret_type, _, _ = self.symbols.lookup_fun(name)
                except SemanticError:
                    ret_type = None
                if (
                    tipo_canonico is not None
                    and ret_type is not None
                    and self._normalize_type(ret_type) != tipo_canonico
                ):
                    self.err(
                        f"Tipo declarado para a função '{name}' ({tipo_canonico}) "
                        f"não coincide com o tipo de retorno ({self._normalize_type(ret_type)})",
                        lineno,
                    )
                continue

            if array_dim is not None:
                resolved_ad = self._resolve_dim_spec(array_dim, lineno)
                tipo_efetivo = ("array", tipo_canonico, resolved_ad)
            else:
                tipo_efetivo = tipo_canonico

            local = self.symbols.lookup_local(name)
            if local is None:
                self.symbols.declare_var(name, tipo_efetivo)
            elif local[1] is None:
                self.symbols.update_type(name, tipo_efetivo)
            elif isinstance(local[1], tuple) and local[1][0] == "array" and local[1][1] is None:
                if isinstance(tipo_efetivo, tuple) and tipo_efetivo[0] == "array":
                    self.symbols.update_type(name, tipo_efetivo)
                else:
                    self.symbols.update_type(name, ("array", tipo_canonico, local[1][2]))
            else:
                self.err(f"Declaração duplicada: '{name}'", lineno)

    def visit_dimension_list(self, node):
        _, pairs, lineno = node
        for name, dimensions in pairs:
            resolved = self._resolve_dim_spec(dimensions, lineno)
            try:
                local = self.symbols.lookup_local(name)
                if local is None:
                    self.symbols.declare_var(name, ("array", None, resolved))
                else:
                    kind, type_, _, _ = local
                    if isinstance(type_, tuple) and type_[0] == "array":
                        if type_[2] != resolved:
                            self.err(f"Redimensionamento inválido do array '{name}'", lineno)
                    else:
                        self.err(f"'{name}' já foi declarado como escalar", lineno)
            except SemanticError:
                self.err(f"Declaração duplicada: '{name}'", lineno)

    def visit_data(self, node):
        _, groups, lineno = node
        for objs, raw_vals in groups:
            expanded = self._expand_data_values(raw_vals, lineno)
            slot_types = self._data_group_slot_types(objs, lineno)
            if len(expanded) != len(slot_types):
                self.err(
                    f"DATA: neste grupo há {len(slot_types)} unidade(s) de armazenamento "
                    f"mas {len(expanded)} constante(s)",
                    lineno,
                )
            for i, (val, dest_t) in enumerate(zip(expanded, slot_types)):
                val_t = self._data_literal_type(val)
                if dest_t is not None and val_t is not None:
                    if not self._types_compatible(dest_t, val_t):
                        self.err(
                            f"DATA: constante {i + 1} incompatível com o destino "
                            f"(destino {dest_t}, constante {val_t})",
                            lineno,
                        )
            for name in self._data_group_target_names(objs):
                try:
                    self.symbols.initialize(name)
                except SemanticError as e:
                    if "não declarada" in str(e):
                        self.err(f"Variável '{name}' no DATA não declarada", lineno)
                    raise

    def _expand_data_values(self, raw_vals, lineno):
        out = []
        for x in raw_vals:
            if isinstance(x, tuple) and x[0] == "rep":
                n = x[1]
                if n < 1:
                    self.err(f"DATA: repetição {n}*... inválida", lineno)
                out.extend([x[2]] * n)
            else:
                out.append(x)
        return out

    def _data_group_target_names(self, objs):
        return sorted({o[1] for o in objs})

    def _array_storage_units(self, type_):
        if not (isinstance(type_, tuple) and type_[0] == "array"):
            return 1
        dims = type_[2]
        if isinstance(dims, list):
            n = 1
            for d in dims:
                n *= d
            return n
        return int(dims)

    def _array_element_base_type(self, arr_type):
        return self._normalize_type(arr_type[1]) if arr_type[1] is not None else None

    def _data_group_slot_types(self, objs, lineno):
        slot_types = []
        for o in objs:
            if o[0] == "whole":
                name = o[1]
                try:
                    kind, t, _, _ = self.symbols.lookup_var(name)
                except SemanticError:
                    self.err(f"Variável '{name}' no DATA não declarada", lineno)
                if kind == "const":
                    self.err(f"DATA não pode dar valor a constante '{name}'", lineno)
                if isinstance(t, tuple) and t[0] == "array":
                    et = self._array_element_base_type(t)
                    slot_types.extend([et] * self._array_storage_units(t))
                else:
                    slot_types.append(self._normalize_type(t))
            else:
                name, idxs = o[1], o[2]
                try:
                    kind, t, _, _ = self.symbols.lookup_var(name)
                except SemanticError:
                    self.err(f"Variável '{name}' no DATA não declarada", lineno)
                if kind == "const":
                    self.err(f"DATA não pode dar valor a constante '{name}'", lineno)
                if not (isinstance(t, tuple) and t[0] == "array"):
                    self.err(f"DATA: '{name}' com subscritos não é um array", lineno)
                dims = t[2]
                if isinstance(dims, list):
                    if len(idxs) != len(dims):
                        self.err(
                            f"DATA: '{name}' tem {len(dims)} dimensão(ões), "
                            f"recebeu {len(idxs)} subscrito(s)",
                            lineno,
                        )
                    for k, ub in enumerate(dims):
                        ix = self._resolve_parameter_int(idxs[k], lineno, ctx="DATA: subscrito")
                        if ix < 1 or ix > ub:
                            self.err(f"DATA: subscrito {ix} fora de 1..{ub}", lineno)
                else:
                    if len(idxs) != 1:
                        self.err(
                            f"DATA: '{name}' é vetor (1 dimensão), "
                            f"recebeu {len(idxs)} subscrito(s)",
                            lineno,
                        )
                    ix = self._resolve_parameter_int(idxs[0], lineno, ctx="DATA: subscrito")
                    if ix < 1 or ix > dims:
                        self.err(f"DATA: subscrito {ix} fora de 1..{dims}", lineno)
                slot_types.append(self._array_element_base_type(t))
        return slot_types

    def _data_literal_type(self, lit):
        if isinstance(lit, bool):
            return "LOGICAL"
        if isinstance(lit, int):
            return "INTEGER"
        if isinstance(lit, float):
            return "REAL"
        if isinstance(lit, str):
            return "CHARACTER"
        return None

    def visit_common(self, node):
        _, parts, lineno = node
        for block_name, var_list in self._merge_common_segments(parts):
            self._process_common_block(block_name, var_list, lineno)

    @staticmethod
    def _merge_common_segments(parts):
        if not parts:
            return []
        merged, cur_name, cur_vl = [], parts[0][0], list(parts[0][1])
        for name, vl in parts[1:]:
            if name == cur_name:
                cur_vl.extend(vl)
            else:
                merged.append((cur_name, cur_vl))
                cur_name, cur_vl = name, list(vl)
        merged.append((cur_name, cur_vl))
        return merged

    def _norm_common_dims(self, type_, array_dim_common, lineno):
        if array_dim_common is not None:
            resolved = self._resolve_dim_spec(array_dim_common, lineno)
            return tuple(resolved) if isinstance(resolved, list) else (resolved,)
        if type_ is None:
            return None
        if isinstance(type_, tuple) and type_[0] == "array":
            d = type_[2]
            return tuple(d) if isinstance(d, list) else (int(d),)
        return None

    def _finalize_common_pending_unit(self):
        for block_key, var_entries in self._common_pending_unit.items():
            self._merge_common_into_global(block_key, list(var_entries), 0)

    def _process_common_block(self, block_name, var_list, lineno):
        block_key = block_name if block_name else "__BLANK__"
        current_vars = []
        for var in var_list:
            _, name, array_dim = var
            try:
                kind, type_, _, _ = self.symbols.lookup_var(name)
                if kind == "const":
                    self.err(f"COMMON: '{name}' é constante", lineno)
                current_vars.append((name, type_, array_dim))
            except SemanticError:
                effective_type = ("array", None, array_dim) if array_dim is not None else None
                self.symbols.declare_var(name, effective_type)
                current_vars.append((name, effective_type, array_dim))

        self._common_pending_unit.setdefault(block_key, []).extend(current_vars)

    def _merge_common_into_global(self, block_key, current_vars, lineno):
        if block_key in self.common_blocks:
            prev_vars = self.common_blocks[block_key]
            if len(current_vars) != len(prev_vars):
                self.err(
                    f"COMMON /{block_key if block_key != '__BLANK__' else ' '}/: "
                    f"nesta unidade há {len(current_vars)} entidade(s), "
                    f"na primeira ocorrência {len(prev_vars)}",
                    lineno,
                )
            for i, ((_, t1, ad1), (_, t2, ad2)) in enumerate(zip(current_vars, prev_vars), start=1):
                ed1 = self._norm_common_dims(t1, ad1, lineno)
                ed2 = self._norm_common_dims(t2, ad2, lineno)
                if ed1 != ed2:
                    self.err(
                        f"COMMON: posição {i} - dimensões do array não coincidem "
                        f"com a primeira ocorrência",
                        lineno,
                    )
        self.common_blocks[block_key] = current_vars

    def visit_parameter(self, node):
        _, pairs, lineno = node
        for name, expr in pairs:
            self.analyze(expr)
            expr_type = self.get_type(expr)
            if expr_type is None:
                self.err(f"Não foi possível inferir o tipo do PARAMETER '{name}'", lineno)
            param_type = self._normalize_type(expr_type)
            lit = self._const_eval_literal(expr)
            try:
                self.symbols.declare_var(name, param_type, kind="const")
            except SemanticError as e:
                if "Declaração duplicada" in str(e):
                    try:
                        self.symbols.promote_var_to_const(name, param_type)
                    except SemanticError as e2:
                        self.err(str(e2), lineno)
                else:
                    raise
            self.symbols.initialize(name)
            if lit is not None:
                self._parameter_values[name] = lit
