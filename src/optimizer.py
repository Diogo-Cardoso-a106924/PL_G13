class ASTOptimizer:
    _EXPR_OPS = frozenset({"neg","+","-","*","/","**","//",".EQ.",".NE.",".LT.",".LE.",".GT.",".GE.",".AND.",".OR.",".EQV.",".NEQV."})

    def optimize(self, node):
        return self._opt_node(node)

    def _opt_node(self, node):
        if node is None:
            return None
        if isinstance(node, list):
            out = []
            for item in node:
                new_item = self._opt_node(item)
                if new_item is None:
                    continue
                out.append(new_item)
            return out
        if isinstance(node, (int, float, bool, str)):
            return node
        if not isinstance(node, tuple) or not node:
            return node

        kind = node[0]
        if self._is_expr_node(node):
            return self._opt_expr(node)

        handler = getattr(self, f"_opt_{kind}", None)
        if handler is not None:
            return handler(node)
        return self._opt_generic(node)

    @staticmethod
    def _is_expr_node(node):
        return isinstance(node, tuple) and bool(node) and isinstance(node[0], str) and node[0] in ASTOptimizer._EXPR_OPS

    def _opt_generic(self, node): return tuple([node[0]] + [self._opt_node(ch) for ch in node[1:]])

    def _opt_expr(self, expr):
        if expr is None or isinstance(expr, (int, float, bool, str)):
            return expr
        if not isinstance(expr, tuple) or not expr:
            return expr

        kind = expr[0]
        if kind == "neg" and len(expr) == 2:
            expr = ("neg", self._opt_expr(expr[1]))
        elif len(expr) == 3 and self._is_expr_node(expr):
            expr = (kind, self._opt_expr(expr[1]), self._opt_expr(expr[2]))
        else:
            return self._opt_node(expr)

        folded = self._try_fold(expr)
        if folded is not None:
            return folded
        return self._simplify_algebraic(expr)

    def _try_fold(self, expr):
        val = self._const_eval(expr)
        if val is None:
            return None
        if isinstance(val, str):
            return ("str_lit", val)
        return val

    def _const_eval(self, node):
        if isinstance(node, (bool, int, float)):
            return node
        if isinstance(node, tuple) and len(node) == 2 and node[0] == "str_lit":
            return node[1]
        if not isinstance(node, tuple) or not node:
            return None

        kind = node[0]
        if kind == "neg":
            inner = self._const_eval(node[1])
            if isinstance(inner, (int, float)):
                return -inner
            return None

        if len(node) != 3:
            return None

        op = kind
        left = self._const_eval(node[1])
        right = self._const_eval(node[2])
        if left is None or right is None:
            return None

        op_upper = op.upper() if isinstance(op, str) else op

        if op == "+" and isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left + right
        if op == "-" and isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left - right
        if op == "*" and isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left * right
        if op == "/" and isinstance(left, (int, float)) and isinstance(right, (int, float)) and right != 0:
            return left / right
        if op in ("**",) and isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left ** right
        if op == "//" and isinstance(left, str) and isinstance(right, str):
            return left + right

        if op_upper == ".EQ.":
            return left == right
        if op_upper == ".NE.":
            return left != right
        if op_upper == ".LT.":
            return left < right
        if op_upper == ".LE.":
            return left <= right
        if op_upper == ".GT.":
            return left > right
        if op_upper == ".GE.":
            return left >= right
        if op_upper == ".AND." and isinstance(left, bool) and isinstance(right, bool):
            return left and right
        if op_upper == ".OR." and isinstance(left, bool) and isinstance(right, bool):
            return left or right
        if op_upper == ".EQV." and isinstance(left, bool) and isinstance(right, bool):
            return left == right
        if op_upper == ".NEQV." and isinstance(left, bool) and isinstance(right, bool):
            return left != right

        return None

    def _simplify_algebraic(self, expr):
        if not isinstance(expr, tuple) or not expr:
            return expr

        kind = expr[0]
        if kind == "neg":
            inner = expr[1]
            if isinstance(inner, tuple) and inner and inner[0] == "neg":
                return inner[1]
            return expr

        if len(expr) != 3:
            return expr

        op, left, right = expr
        op_upper = op.upper() if isinstance(op, str) else op

        if op == "+":
            if self._is_zero(right):
                return left
            if self._is_zero(left):
                return right
        elif op == "-":
            if self._is_zero(right):
                return left
        elif op == "*":
            if self._is_one(right):
                return left
            if self._is_one(left):
                return right
            if self._is_zero(right) or self._is_zero(left):
                return 0
        elif op == "/":
            if self._is_one(right):
                return left
            if self._is_zero(left):
                return 0
        elif op_upper == ".AND.":
            if right is True:
                return left
            if left is True:
                return right
            if right is False or left is False:
                return False
        elif op_upper == ".OR.":
            if right is False:
                return left
            if left is False:
                return right
            if right is True or left is True:
                return True

        return expr

    @staticmethod
    def _is_zero(node): return isinstance(node, (int, float)) and node == 0
    @staticmethod
    def _is_one(node): return isinstance(node, (int, float)) and node == 1

    def _opt_start(self, node):
        return ("start", self._opt_node(node[1])) if len(node)==2 else ("start", self._opt_node(node[1]), self._opt_node(node[2]))

    def _opt_program(self, node):
        _, n, b, l = node; return ("program", n, self._opt_node(b), l)

    def _opt_function(self, node):
        _, r, n, a, b, l = node; return ("function", r, n, a, self._opt_node(b), l)

    def _opt_subroutine(self, node):
        _, n, a, b, l = node; return ("subroutine", n, a, self._opt_node(b), l)

    def _opt_body(self, node): return ("body", self._opt_node(node[1]), self._opt_node(node[2]))

    def _opt_assignment(self, node):
        _, name, expr, lineno = node
        expr2 = self._opt_expr(expr)
        if isinstance(expr2, str) and expr2 == name:
            return None
        return ("assignment", name, expr2, lineno)

    def _opt_assignment_array(self, node):
        _, name, idx_exprs, expr, lineno = node
        return (
            "assignment_array",
            name,
            self._opt_node(idx_exprs),
            self._opt_expr(expr),
            lineno,
        )

    def _opt_assignment_substring(self, node):
        _, name, lo, hi, expr, lineno = node
        return (
            "assignment_substring",
            name,
            self._opt_expr(lo) if lo is not None else None,
            self._opt_expr(hi) if hi is not None else None,
            self._opt_expr(expr),
            lineno,
        )

    def _opt_print(self, node): return ("print", node[1], [self._opt_expr(x) for x in node[2]], node[3])

    def _opt_write(self, node): return ("write", node[1], [self._opt_expr(x) for x in node[2]], node[3])

    def _opt_read(self, node):
        _, io_pair, read_list, lineno = node
        return ("read", self._opt_node(io_pair), self._opt_node(read_list), lineno)

    def _opt_call_stmt(self, node):
        _, name, args, lineno = node
        return ("call_stmt", name, [self._opt_expr(a) for a in args], lineno)

    def _opt_call(self, node):
        _, name, args, lineno = node
        return ("call", name, [self._opt_expr(a) for a in args], lineno)

    def _opt_index(self, node): return ("index", node[1], self._opt_expr(node[2]), node[3])

    def _opt_substring_ref(self, node):
        _, name, lo, hi, lineno = node
        return (
            "substring_ref",
            name,
            self._opt_expr(lo) if lo is not None else None,
            self._opt_expr(hi) if hi is not None else None,
            lineno,
        )

    def _opt_labeled(self, node):
        _, label, stmt = node
        optimized_stmt = self._opt_node(stmt)
        if optimized_stmt is None:
            optimized_stmt = ("continue", None)
        return ("labeled", label, optimized_stmt)

    def _opt_if(self, node):
        _, cond, then_b, else_b, elseif_chain, lineno = node
        cond2 = self._opt_expr(cond)
        then2 = self._opt_node(then_b)
        else2 = self._opt_node(else_b)
        elseif2 = self._opt_node(elseif_chain)

        if cond2 is True:
            return then2
        if cond2 is False:
            return else2 if else2 is not None else elseif2

        return ("if", cond2, then2, else2, elseif2, lineno)

    def _opt_elseif(self, node):
        _, cond, body, next_chain, lineno = node
        cond2 = self._opt_expr(cond)
        body2 = self._opt_node(body)
        next2 = self._opt_node(next_chain)

        if cond2 is True:
            return body2
        if cond2 is False:
            return next2

        return ("elseif", cond2, body2, next2, lineno)

    def _opt_else(self, node): return ("else", self._opt_node(node[1]))

    def _opt_do(self, node):
        _, label, var, start, end, step, body, lineno = node
        return (
            "do",
            label,
            var,
            self._opt_expr(start),
            self._opt_expr(end),
            self._opt_expr(step) if step is not None else None,
            self._opt_node(body),
            lineno,
        )

def optimize_ast(ast): return ASTOptimizer().optimize(ast)