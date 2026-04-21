import ply.lex as lex
import sys

def find_column(token):
    '''
    Retorna o número da coluna em que o token se encontra na sua linha.
    '''
    text = token.lexer.lexdata
    line_start = text.rfind('\n', 0, token.lexpos) + 1
    return (token.lexpos - line_start) + 1
 
def getline(token) -> str:
    '''
    Retorna a string da linha do token dado como argumento.
    '''
    line_idx = token.lineno - 1
    lines = token.lexer.lexdata.split('\n')
    if line_idx < len(lines):
        return lines[line_idx]
    return ''


class Lexer:

    keywords = {
        'program'    : 'PROGRAM',
        'read'       : 'READ',
        'print'      : 'PRINT',
        'write'      : 'WRITE',
        'do'         : 'DO',
        'end'        : 'END',
        'continue'   : 'CONTINUE',
        'logical'    : 'LOGICAL',
        'if'         : 'IF',
        'then'       : 'THEN',
        'endif'      : 'ENDIF',
        'else'       : 'ELSE',
        'elseif'     : 'ELSEIF',
        'goto'       : 'GOTO',
        'function'   : 'FUNCTION',
        'return'     : 'RETURN',
        'subroutine' : 'SUBROUTINE',
        'real'       : 'REAL',
        'double'     : 'DOUBLE',
        'precision'  : 'PRECISION',
        'complex'    : 'COMPLEX',
        'character'  : 'CHARACTER',
        'integer'    : 'INTEGER',
        'stop'       : 'STOP',
        'call'       : 'CALL',
        'data'       : 'DATA',
        'dimension'  : 'DIMENSION',
        'common'     : 'COMMON',
        'parameter'  : 'PARAMETER',
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
    
        # Operador de concatenação de strings
        'OP_CONCAT',
    
        # Operador de potência
        'OP_POW',
    
        # Label numérico de linha
        'LABEL',
    
        'NEWLINE',
    ]
    
    # Literais de um só caracter (delimitadores e operadores simples)
    literals = ['=', '+', '-', '*', '/', '(', ')', ',', ':', '&', '%']
    
    def preprocess_fixed_form(self, data:str):
        out=[]
        for line in data.splitlines():
            if not line:
                out.append('')
                continue
            if line[0] in ('c','C','*','!'):
                out.append('')
                continue
            label = line[:5].strip()
            code = line[6:72] if len(line) > 6 else ''
            if label.isdigit():
                out.append(label + ' ' + code.rstrip())
            else:
                out.append(line.rstrip())
        return '\n'.join(out)
  
    def t_BOOL(self, t ):
        r'\.TRUE\.|\.FALSE\.'
        t.value = True if t.value.upper() == '.TRUE.' else False
        return t
    
    def t_OP_AND(self, t ):
        r'\.AND\.'
        return t
    
    def t_OP_OR(self, t ):
        r'\.OR\.'
        return t
    
    def t_OP_EQV(self, t ):
        r'\.EQV\.'
        return t
    
    def t_OP_NEQV(self, t ):
        r'\.NEQV\.'
        return t
    
    def t_OP_NOT(self, t ):
        r'\.NOT\.'
        return t
    
    def t_OP_LE(self, t ):
        r'\.LE\.'
        return t
    
    def t_OP_GE(self, t ):
        r'\.GE\.'
        return t
    
    def t_OP_GT(self, t ):
        r'\.GT\.'
        return t
    
    def t_OP_LT(self, t ):
        r'\.LT\.'
        return t
    
    def t_OP_NE(self, t ):
        r'\.NE\.'
        return t
    
    def t_OP_EQ(self, t ):
        r'\.EQ\.'
        return t
    
    def t_OP_CONCAT(self, t ):
        r'//'
        return t
    
    def t_OP_POW(self, t ):
        r'\*\*'
        return t
    
    def t_REALNUMB(self, t ):
        r'\d+\.\d*([eEdD][+-]?\d+)?|\d+[eEdD][+-]?\d+'
        t.value = float(t.value.replace('d', 'e').replace('D', 'E'))
        return t
    
    def t_LABEL(self, t):
        r'\d+'
        pos0 = t.lexpos == 0 or t.lexer.lexdata[t.lexpos-1] == '\n'
        if pos0:
            t.value = int(t.value)
            return t
        t.type='INT'
        t.value=int(t.value)
        return t
    

    def t_STR(self,t):
        r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\""
        raw=t.value[1:-1]
        if t.value[0]=="'":
            t.value=raw.replace("''","'")
        else:
            t.value=raw.replace('""','"')
        return t   
    
    #  Fortran é case-insensitive — normaliza tudo para minúsculas
    def t_IDENTIFIER(self, t ):
        r'[a-zA-Z][a-zA-Z0-9_]*'
        t.type = self.keywords.get(t.value.lower(), 'IDENTIFIER')
        # Mantém o valor original mas guarda também a versão normalizada
        t.value = t.value.upper()
        return t
    
    def t_NEWLINE(self, t ):
        r'\n+'
        t.lexer.lineno += len(t.value)
        #return t
    
    
    # Comentários em free-form começam com '!'
    def t_COMMENT(self, t ):
        r'!.*'
        pass
    
    # Ignorar espaços e tabs, mas não newlines
    t_ignore = ' \t\r'
    
    
    # ─────────────────────────────────────────────────────────────────────────────
    #  Tratamento de erros
    # ─────────────────────────────────────────────────────────────────────────────
    
    def t_error(self, t ):
        col = find_column(t)
        line = getline(t).rstrip()
        print(f"Erro léxico na linha {t.lineno}, coluna {col}: caracter inesperado '{t.value[0]}'")
        print(f"  {line}")
        print(f"  {' ' * (col - 1)}^")
        t.lexer.skip(1)
    
    
    def build(self, **kwargs):
        self.lexer = lex.lex(module=self, **kwargs)
 
    def input(self,data:str, fixed_form=True):
        self.lexer.lineno=1
        if fixed_form:
            data=self.preprocess_fixed_form(data)
        self.lexer.input(data)

    def token(self):
        return self.lexer.token()
    
    def test(self, data: str):
        self.lexer.lineno = 1
        self.lexer.input(data)
        for tok in self.lexer:
            print(tok)
    
    def __iter__(self):
        return self.lexer.__iter__()
    
    
if __name__ == '__main__':
    m = Lexer()
    m.build()

    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = f.read()
        m.test(data)
    else:
        examples = [
            '../tests/examples/hello.f',
            '../tests/examples/factorial.f',
            '../tests/examples/prime.f',
            '../tests/examples/sumlist.f',
            '../tests/examples/convert.f',
        ]
        for path in examples:
            print(f"\n{'='*60}")
            print(f"  {path}")
            print(f"{'='*60}")
            with open(path) as f:
                data = f.read()
            m.test(data)