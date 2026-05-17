import ply.lex as lex

def find_column(token):
    text = token.lexer.lexdata
    line_start = text.rfind('\n', 0, token.lexpos) + 1
    return (token.lexpos - line_start) + 1
 
def getline(token) -> str:
    line_idx = token.lineno - 1
    lines = token.lexer.lexdata.split('\n')
    if line_idx < len(lines):
        return lines[line_idx]
    return ''


class Lexer:

    keywords = {
        # Estrutura do programa
        'program'              : 'PROGRAM',
        'end'                  : 'END',
        'stop'                 : 'STOP',

        # Subprogramas
        'function'             : 'FUNCTION',
        'subroutine'           : 'SUBROUTINE',
        'return'               : 'RETURN',
        'call'                 : 'CALL',

        # Tipos de dados
        'integer'              : 'INTEGER',
        'real'                 : 'REAL',
        'double_precision'     : 'DOUBLE_PRECISION',
        'character'            : 'CHARACTER',
        'logical'              : 'LOGICAL',

        # Controlo de fluxo
        'if'                   : 'IF',
        'then'                 : 'THEN',
        'else'                 : 'ELSE',
        'elseif'               : 'ELSEIF',
        'endif'                : 'ENDIF',
        'do'                   : 'DO',
        'continue'             : 'CONTINUE',
        'goto'                 : 'GOTO',

        # I/O
        'read'                 : 'READ',
        'print'                : 'PRINT',
        'write'                : 'WRITE',

        # Declarações
        'data'                 : 'DATA',
        'dimension'            : 'DIMENSION',
        'common'               : 'COMMON',
        'parameter'            : 'PARAMETER',
    }
    
    tokens = list(keywords.values()) + [
        # Literais
        'INT',
        'REALNUMB',
        'STR',
        'BOOL',
    
        # Identificador genérico
        'IDENTIFIER',
    
        # Operadores lógicos
        'OP_AND',
        'OP_OR',
        'OP_EQV',
        'OP_NEQV',
        'OP_NOT',
        'OP_LE',
        'OP_GE',
        'OP_GT',
        'OP_LT',
        'OP_NE',
        'OP_EQ',
    
        # Operador de potência
        'OP_POW',
        # Concatenação `//` de strings.
        'OP_CONCAT',

        'NEWLINE',
    ]
    
    # Literais
    literals = ['=', '+', '-', '*', '/', '(', ')', ',', ':']
    
    def t_BOOL(self, t):
        r'\.([Tt][Rr][Uu][Ee]|[Ff][Aa][Ll][Ss][Ee])\.'
        t.value = t.value.upper() == '.TRUE.'
        return t

    def t_OP_AND(self, t):
        r'\.[Aa][Nn][Dd]\.'
        return t

    def t_OP_OR(self, t):
        r'\.[Oo][Rr]\.'
        return t

    def t_OP_EQV(self, t):
        r'\.[Ee][Qq][Vv]\.'
        return t

    def t_OP_NEQV(self, t):
        r'\.[Nn][Ee][Qq][Vv]\.'
        return t

    def t_OP_NOT(self, t):
        r'\.[Nn][Oo][Tt]\.'
        return t

    def t_OP_LE(self, t):
        r'\.[Ll][Ee]\.'
        return t

    def t_OP_GE(self, t):
        r'\.[Gg][Ee]\.'
        return t

    def t_OP_GT(self, t):
        r'\.[Gg][Tt]\.'
        return t

    def t_OP_LT(self, t):
        r'\.[Ll][Tt]\.'
        return t

    def t_OP_NE(self, t):
        r'\.[Nn][Ee]\.'
        return t

    def t_OP_EQ(self, t):
        r'\.[Ee][Qq]\.'
        return t

    def t_OP_POW(self, t):
        r'\*\*'
        return t

    def t_OP_CONCAT(self, t):
        r'//'
        return t
    
    def t_CONTINUATION(self, t):
        r'&[ \t]*\n[ \t]*'
        t.lexer.lineno += 1
        pass
    
    def t_REALNUMB(self, t):
        r'(\d+\.\d*|\.\d+)([eEdD][+-]?\d+)?|\d+[eEdD][+-]?\d+'
        t.value = float(t.value.replace('d', 'e').replace('D', 'E'))
        return t
    
    def t_INT(self, t):
        r'\d+'
        t.value = int(t.value)
        return t
    
    def t_STR(self, t):
        r'\'(?:\'\'|[^\'])*\'|\"(?:\"\"|[^\"])*\"'
        t.value = t.value[1:-1]
        return t

    def t_IDENTIFIER(self, t):
        r'[a-zA-Z][a-zA-Z0-9_]*'
        lower = t.value.lower()
    
        if lower == 'double':
            current_pos = t.lexer.lexpos
            data = t.lexer.lexdata
            while current_pos < len(data) and data[current_pos] in ' \t':
                current_pos+=1

            word_end = current_pos
            while word_end < len(data) and (
                data[word_end].isalpha() or data[word_end].isdigit() or data[word_end] == '_'
            ):
                word_end += 1

            next_word = data[current_pos:word_end].lower()
            
            if next_word == 'precision':
                t.type = 'DOUBLE_PRECISION'
                t.value = 'DOUBLE_PRECISION'
                t.lexer.lexpos = word_end
                return t
            t.type = 'IDENTIFIER'
            t.value = 'DOUBLE'
            return t
    
        t.type = self.keywords.get(lower, 'IDENTIFIER')
        t.value = t.value.upper()
        return t

    def t_NEWLINE(self, t):
        r'(\r?\n[ \t]*)+'
        t.lexer.lineno += t.value.count('\n')
        return t
    
    # Comentários em free-form começam com '!'
    def t_COMMENT(self, t):
        r'!.*'
        pass
    
    # Ignorar espaços e tabs
    t_ignore = ' \t\r'
    
    def t_error(self, t):
        col = find_column(t)
        line = getline(t).rstrip()
        msg = (
            f"Erro léxico na linha {t.lineno}, coluna {col}: "
            f"caracter inesperado '{t.value[0]}'\n"
            f"  {line}\n"
            f"  {' ' * (col - 1)}^"
        )
        self.lex_errors.append(msg)
        t.lexer.skip(1)
    
    
    def build(self, **kwargs):
        self.lex_errors = []
        self.lexer = lex.lex(module=self, **kwargs)
 
    def input(self, data: str):
        self.lexer.lineno = 1
        self.lexer.input(data)
 
    def token(self):
        return self.lexer.token()

    def __iter__(self):
        return self.lexer.__iter__()