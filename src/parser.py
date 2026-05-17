import ply.yacc as yacc
from tokenizer import Lexer

class Parser:

    tokens = Lexer.tokens

    precedence = (
        ('left', 'OP_EQV', 'OP_NEQV'),
        ('left', 'OP_OR'),
        ('left', 'OP_AND'),
        ('right', 'OP_NOT'),
        ('left', 'OP_EQ', 'OP_NE', 'OP_LT', 'OP_LE', 'OP_GT', 'OP_GE'),
        ('left', 'OP_CONCAT'),
        ('left', '+', '-'),
        ('left', '*', '/'),
        ('right', 'UMINUS'),
        ('right', 'OP_POW'),
    )

    # Programa

    def p_start(self, p):
        r"""
        start : program
              | program subprograms
              | subprograms
        """
        if len(p) == 2:
            p[0] = ('start', p[1])
        else:
            p[0] = ('start', p[1], p[2])


    def p_program(self, p):
        r"program : PROGRAM IDENTIFIER NEWLINE body END NEWLINE"
        p[0] = ('program', p[2], p[4], p.lineno(1))

    # Subprogramas

    def p_subprograms(self, p):
        r"""
        subprograms : subprogram
                    | subprograms subprogram
        """
        p[0] = p[1] + [p[2]] if len(p) == 3 else [p[1]]

    def p_subprogram(self, p):
        r"""
        subprogram : function
                   | subroutine
        """
        p[0] = p[1]


    def p_function(self, p):
        r"function : type FUNCTION IDENTIFIER '(' arg_list ')' NEWLINE body END NEWLINE"
        p[0] = ('function', p[1], p[3], p[5], p[8], p.lineno(2))

    def p_subroutine_noparens(self, p):
        r"subroutine_noparens : SUBROUTINE IDENTIFIER"
        p[0] = (p[2], [], p.lineno(1))

    def p_subroutine(self, p):
        r"""
        subroutine : SUBROUTINE IDENTIFIER '(' arg_list ')' NEWLINE body END NEWLINE
                   | subroutine_noparens NEWLINE body END NEWLINE
        """
        if len(p) == 10:
            p[0] = ('subroutine', p[2], p[4], p[7], p.lineno(1))
        else:
            name, args, lineno = p[1]
            p[0] = ('subroutine', name, args, p[3], lineno)

    # Corpo

    def p_body(self, p):
        r"body : declarations statements"
        p[0] = ('body', p[1], p[2])

    def p_declarations(self, p):
        r"""
        declarations : declarations declaration
                    | empty
        """
        p[0] = [] if len(p) == 2 else p[1] + [p[2]]

    def p_declaration(self, p):
        r"""
        declaration : type var_list NEWLINE
                    | DIMENSION dim_decl_list NEWLINE
                    | DATA data_group NEWLINE
                    | COMMON ident_opt var_list NEWLINE
                    | PARAMETER '(' list_const ')' NEWLINE
        """
        lineno = p.lineno(1)
        if p[1] == 'DIMENSION':
            p[0] = ('dimension_list', p[2], lineno)
        elif p[1] == 'DATA':
            p[0] = ('data', [p[2]], lineno)
        elif p[1] == 'COMMON':
            p[0] = ('common', [(p[2], p[3])], lineno)
        elif p[1] == 'PARAMETER':
            p[0] = ('parameter', p[3], lineno)
        else:
            p[0] = ('declaration', p[1], p[2], lineno)

    def p_ident_opt(self, p):
        r"""
        ident_opt : '/' IDENTIFIER '/'
                  | '/' '/'
                  | empty
        """
        if len(p) == 4:
            p[0] = p[2]
        else:
            p[0] = None

    def p_dim_decl_list(self, p):
        """
        dim_decl_list : dim_decl_list ',' dim_decl
                      | dim_decl
        """
        p[0] = p[1] + [p[3]] if len (p) == 4 else [p[1]]

    def p_dim_decl(self, p):
        r"dim_decl : IDENTIFIER '(' int_list ')'"
        p[0] = (p[1], p[3])

    def p_var_list(self, p):
        r"""
        var_list : var_item
                 | var_item ',' var_list
        """
        p[0] = [p[1]] if len(p) == 2 else [p[1]] + p[3]

    def p_var_item(self, p):
        r"var_item : IDENTIFIER arrayopt"
        p[0] = ('var', p[1], p[2])

    def p_list_const(self, p):
        r"""
        list_const : IDENTIFIER '=' expr
                   | list_const ',' IDENTIFIER '=' expr
        """
        p[0] = [(p[1], p[3])] if len(p) == 4 else p[1] + [(p[3], p[5])]

    def p_arrayopt(self, p):
        r"""
        arrayopt : '(' int_list ')'
                 | empty
        """
        if len(p) == 4:
            dims = p[2]
            p[0] = dims[0] if len(dims) == 1 else dims
        else:
            p[0] = None

    def p_data_group(self, p):
        r"data_group : var_list '/' data_val_list '/'"
        objs = []
        for item in p[1]:
            _, name, idx = item
            if idx is None:
                objs.append(('whole', name))
            elif isinstance(idx, list):
                objs.append(('elem', name, idx))
            else:
                objs.append(('elem', name, [idx]))
        p[0] = (objs, p[3])

    def p_data_val_list(self, p):
        """
        data_val_list : data_val
                      | data_val_list ',' data_val
        """
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

    def p_data_val(self, p):
        """
        data_val : INT '*' data_literal
                | data_literal
        """
        p[0] = ('rep', p[1], p[3]) if len(p) == 4 else p[1]
        
    def p_data_literal(self, p):
        """
        data_literal : INT
                    | REALNUMB
                    | STR
                    | BOOL
        """
        p[0] = p[1]
    
    def p_type(self, p):
        """
        type : INTEGER
            | REAL
            | LOGICAL
            | DOUBLE_PRECISION
            | CHARACTER stropt
        """
        if len(p) == 2:
            p[0] = 'REAL' if p[1] == 'DOUBLE_PRECISION' else p[1]
        else:
            p[0] = ('CHARACTER', p[2]) if p[2] else 'CHARACTER'

    def p_stropt(self, p):
        r"""
        stropt : '*' INT
               | empty
        """
        p[0] = p[2] if len(p) == 3 else None

    # Statements

    def p_statements(self, p):
        r"""
        statements : statements statement
                   | empty
        """
        if len(p) == 3:
            p[0] = p[1] + ([p[2]] if p[2] is not None else [])
        else:
            p[0] = []

    def p_statement(self, p):
        r"""
        statement : stmt
                  | INT stmt
                  | NEWLINE
        """
        if len(p) == 3:
            p[0] = ('labeled', p[1], p[2])
        elif p.slice[1].type == 'NEWLINE':
            p[0] = None
        else:
            p[0] = p[1]

    def p_stmt(self, p):
        r"""
        stmt : do_loop
             | assignment
             | io
             | call_stmt
             | stop_stmt
             | continue_stmt
             | RETURN NEWLINE
             | if_stmt
             | goto_stmt
        """
        if len(p) == 3 and p.slice[1].type == 'RETURN':
            p[0] = ('return', p.lineno(1))
        else:
            p[0] = p[1]

    def p_stop_stmt(self, p):
        r"""
        stop_stmt : STOP NEWLINE
                  | STOP INT NEWLINE
                  | STOP STR NEWLINE
        """
        lineno = p.lineno(1)
        if len(p) == 3:
            p[0] = ('stop', lineno)
        else:
            p[0] = ('stop', p[2], lineno)

    def p_continue_stmt(self, p):
        r"continue_stmt : CONTINUE NEWLINE"
        p[0] = ('continue', p.lineno(1))

    def p_assignment(self, p):
        r"""
        assignment : IDENTIFIER '=' expr NEWLINE
                   | IDENTIFIER '(' int_list ')' '=' expr NEWLINE
                   | IDENTIFIER '(' substring_range ')' '=' expr NEWLINE
        """
        if len(p) == 5:
            p[0] = ('assignment', p[1], p[3], p.lineno(1))
        elif len(p) == 8:
            mid = p[3]
            if isinstance(mid, tuple) and mid[0] == 'sspan':
                _, lo, hi = mid
                p[0] = ('assignment_substring', p[1], lo, hi, p[6], p.lineno(1),)
            else:
                p[0] = ('assignment_array', p[1], mid, p[6], p.lineno(1))

    def p_substring_range(self, p):
        r"""
        substring_range : expr ':' expr
                        | expr ':'
                        | ':' expr
                        | ':'
        """
        if len(p) == 4:
            p[0] = ('sspan', p[1], p[3])
        elif len(p) == 3:
            if p.slice[1].type == ':':
                p[0] = ('sspan', None, p[2])
            else:
                p[0] = ('sspan', p[1], None)
        else:
            p[0] = ('sspan', None, None)

    # Expressões

    def p_expr(self, p):
        r"""
        expr : expr '+' expr
             | expr '-' expr
             | expr '*' expr
             | expr '/' expr
             | expr OP_CONCAT expr
             | expr OP_POW expr
             | expr OP_EQ expr
             | expr OP_NE expr
             | expr OP_LT expr
             | expr OP_LE expr
             | expr OP_GT expr
             | expr OP_GE expr
             | expr OP_AND expr
             | expr OP_OR expr
             | expr OP_EQV expr
             | expr OP_NEQV expr
             | OP_NOT expr
             | '-' expr %prec UMINUS
             | atom
        """
        if len(p) == 4:
            if p.slice[2].type == 'OP_CONCAT':
                p[0] = ('//', p[1], p[3])
            else:
                p[0] = (p[2], p[1], p[3])
        elif len(p) == 3:
            if p.slice[1].type == 'OP_NOT':
                p[0] = ('OP_NOT', p[2])
            else:
                p[0] = ('neg', p[2])
        else:
            p[0] = p[1]

    def p_atom(self, p):
        r"""
        atom : INT
             | REALNUMB
             | STR
             | BOOL
             | IDENTIFIER
             | IDENTIFIER '(' substring_range ')'
             | IDENTIFIER '(' arg_list ')'
             | '(' expr ')'
        """
        if len(p) == 2:
            if p.slice[1].type == 'STR':
                p[0] = ('str_lit', p[1])
            else:
                p[0] = p[1]
        elif len(p) == 4:
            p[0] = p[2]
        elif len(p) == 5:
            mid = p[3]
            if isinstance(mid, tuple) and mid[0] == 'sspan':
                _, lo, hi = mid
                p[0] = ('substring_ref', p[1], lo, hi, p.lineno(1))
            else:
                p[0] = ('call', p[1], mid, p.lineno(1))

    # I/O

    def p_io(self, p):
        r"""
        io : print_stmt
           | read_stmt
           | write_stmt
        """
        p[0] = p[1]

    def p_print(self, p):
        r"""
        print_stmt : PRINT '*' ',' output_list NEWLINE
                   | PRINT STR ',' output_list NEWLINE
        """
        lineno = p.lineno(1)
        if p[2] == '*':
            p[0] = ('print', ('ld',), p[4], lineno)
        else:
            p[0] = ('print', ('chs', p[2]), p[4], lineno)

    def p_write(self, p):
        r"""
        write_stmt : WRITE '*' ',' output_list NEWLINE
                   | WRITE '(' '*' ',' '*' ')' output_list NEWLINE
        """
        lineno = p.lineno(1)
        if p[2] == '*':
            p[0] = ('write', ('ld',), p[4], lineno)
        else:
            p[0] = ('write', ('ld',), p[7], lineno)

    def p_output_list(self, p):
        r"""
        output_list : expr
                    | output_list ',' expr
        """
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

    def p_read_stmt(self, p):
        r"""
        read_stmt : READ '*' ',' read_list NEWLINE
                  | READ '(' '*' ',' '*' ')' read_list NEWLINE
        """
        lineno = p.lineno(1)
        if p[2] == '*':
            p[0] = ('read', ('ld',), p[4], lineno)
        else:
            p[0] = ('read', ('ld',), p[7], lineno)

    def p_read_list(self, p):
        r"""
        read_list : read_item
                  | read_list ',' read_item
        """
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

    def p_read_item(self, p):
        r"""
        read_item : IDENTIFIER
                  | IDENTIFIER '(' expr ')'
                  | IDENTIFIER '(' substring_range ')'
        """
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 5:
            mid = p[3]
            if isinstance(mid, tuple) and mid[0] == 'sspan':
                _, lo, hi = mid
                p[0] = ('substring_ref', p[1], lo, hi, p.lineno(1))
            else:
                p[0] = ('index', p[1], mid, p.lineno(1))

    def p_call_stmt(self, p):
        r"""
        call_stmt : CALL IDENTIFIER '(' arg_list ')' NEWLINE
                  | CALL IDENTIFIER NEWLINE
        """
        if len(p) == 4:
            p[0] = ('call_stmt', p[2], [], p.lineno(1))
        else:
            p[0] = ('call_stmt', p[2], p[4], p.lineno(1))

    def p_arg_list(self, p):
        r"""
        arg_list : expr
                 | arg_list ',' expr
                 | empty
        """
        if len(p) == 2:
            p[0] = [] if p[1] is None else [p[1]]
        else:
            p[0] = p[1] + [p[3]]

    # Controlo de fluxo

    def p_if_stmt(self, p):
        r"""
        if_stmt : IF '(' expr ')' stmt
                | IF '(' expr ')' THEN NEWLINE body ENDIF NEWLINE
                | IF '(' expr ')' THEN NEWLINE body ELSE NEWLINE body ENDIF NEWLINE
                | IF '(' expr ')' THEN NEWLINE body elseif_chain ENDIF NEWLINE
        """
        lineno = p.lineno(1)
        if len(p) == 6:
            p[0] = ('if', p[3], p[5], None, None, lineno)
        elif len(p) == 10:
            p[0] = ('if', p[3], p[7], None, None, lineno)
        elif len(p) == 13:
            p[0] = ('if', p[3], p[7], p[10], None, lineno)
        else:
            p[0] = ('if', p[3], p[7], None, p[8], lineno)

    def p_elseif_chain(self, p):
        r"""
        elseif_chain : ELSEIF '(' expr ')' THEN NEWLINE body
                     | ELSEIF '(' expr ')' THEN NEWLINE body elseif_chain
                     | ELSE NEWLINE body
        """
        if p[1] == 'ELSE':
            p[0] = ('else', p[3])
        elif len(p) == 8:
            p[0] = ('elseif', p[3], p[7], None, p.lineno(1))
        else:
            p[0] = ('elseif', p[3], p[7], p[8], p.lineno(1))

    def p_do_loop(self, p):
        r"""
        do_loop : DO INT IDENTIFIER '=' expr ',' expr NEWLINE statements
                | DO INT IDENTIFIER '=' expr ',' expr ',' expr NEWLINE statements
        """
        lineno = p.lineno(1)
        if len(p) == 10:
            p[0] = ('do', p[2], p[3], p[5], p[7], None, p[9], lineno)
        else:
            p[0] = ('do', p[2], p[3], p[5], p[7], p[9], p[11], lineno)

    def p_goto_stmt(self, p):
        r"""
        goto_stmt : GOTO INT NEWLINE
                  | GOTO '(' int_list ')' ',' IDENTIFIER NEWLINE
        """
        lineno = p.lineno(1)
        if len(p) == 4:
            p[0] = ('goto', p[2], lineno)
        else:
            p[0] = ('goto_computed', p[3], p[6], lineno)

    def p_int_list(self, p):
        r"""
        int_list : item
                 | int_list ',' item
        """
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[3]]

    def p_item(self, p):
        r"""
        item : INT
             | IDENTIFIER
        """
        p[0] = p[1]

    def p_empty(self, p):
        r"empty :"
        p[0] = None

    def p_error(self, p):
        raise SyntaxError(
            f"Token inesperado: '{p.value}' (tipo: {p.type}) na linha {p.lineno}"
            if p else "Fim de ficheiro inesperado"
        )

    # Build e Parse

    def build(self, **kwargs):
        self.lexer = Lexer()
        self.lexer.build()
        self.parser = yacc.yacc(module=self, **kwargs, debug=False)

    def parse(self, data: str):
        if not data.endswith('\n'):
            data += '\n'
        return self.parser.parse(data, lexer=self.lexer)