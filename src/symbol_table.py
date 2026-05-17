class SemanticError(Exception):
    pass

class SymbolTable():
    def __init__(self):
        self.__table = [{}]
        self.__var_count = 0

    def push(self): self.__table.append({})
    def pop(self): self.__table.pop()

    def declare_var(self, id, type_, kind='var'):
        if id in self.__table[-1]:
            raise SemanticError(f"Declaração duplicada: {id}")
        self.__table[-1][id] = (kind, type_, self.__var_count, False)
        self.__var_count += 1

    def promote_var_to_const(self, id, type_):
        for table in reversed(self.__table):
            if id in table:
                kind, _, idx, _ = table[id]
                if kind != "var":
                    raise SemanticError(f"PARAMETER '{id}' já existe e não é uma variável simples")
                table[id] = ("const", type_, idx, True)
                return
        raise SemanticError(f"Variável '{id}' não declarada")

    def initialize(self, id):
        for table in reversed(self.__table):
            if id in table:
                kind, type_, idx, _ = table[id]
                if kind == "fun": return
                table[id] = (kind, type_, idx, True)
                return
        raise SemanticError(f"Variável não declarada: {id}")

    def lookup_var(self, id):
        for table in reversed(self.__table):
            if id in table:
                if table[id][0] not in ("var", "const"):
                    raise SemanticError(f"Identificador não é variável: {id}")
                return table[id]
        raise SemanticError(f"Variável não declarada: {id}")

    def declare_fun(self, id, type_, params):
        if id in self.__table[-1]:
            raise SemanticError(f"Declaração duplicada: {id}")
        self.__table[-1][id] = ("fun", type_, params, None)

    def declare_sub(self, id, params):
        if id in self.__table[-1]:
            raise SemanticError(f"Declaração duplicada: {id}")
        self.__table[-1][id] = ("sub", None, params, None)

    def lookup_fun(self, id):
        for table in reversed(self.__table):
            if id in table:
                if table[id][0] not in ("fun", "sub"):
                    raise SemanticError(f"Identificador não é função: {id}")
                return table[id]
        raise SemanticError(f"Função não declarada: {id}")

    def outer_proc_kind(self, id):
        for table in reversed(self.__table[:-1]):
            if id in table and table[id][0] in ("fun", "sub"):
                return table[id][0]
        return None

    def lookup(self, id):
        for table in reversed(self.__table):
            if id in table: return table[id]
        raise SemanticError(f"Identificador não declarado: {id}")

    def update_type(self, id, type_):
        for table in reversed(self.__table):
            if id in table:
                kind, _, idx, initialized = table[id]
                table[id] = (kind, type_, idx, initialized)
                return
        raise SemanticError(f"Variável não declarada: {id}")

    def lookup_local(self, name):
        entry = self.__table[-1].get(name)
        if entry is None or entry[0] not in ("var", "const"): return None
        return entry