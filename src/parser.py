import ply.yacc as yacc
from tokenizer import Lexer


tokens = Lexer.tokens
def p_program(p):
    '''
    Program : PROGRAM IDENTIFIER Stmt_block END
    '''
    p[0] = ('program', p[2], p[3])

# Statement Block
def p_stmt_block_rec(p):
    '''
    Stmt_block : Stmt_block Statement
    '''
    p[0] = p[1] + [p[2]]

def p_stmt_block_one(p):
    '''
    Stmt_block : Statement
    '''
    p[0] = [p[1]]


# STATEMENTS
def p_statement(p):
    '''
    Statement : Declaration
              | Assignment
              | If_stmt
              | Do_stmt
              | Goto_stmt
              | Io_stmt
              | Continue_stmt
              | Return_stmt
              | Label_stmt
    '''
    p[0] = p[1]


# LABEL
def p_label_stmt(p):
    '''
    Label_stmt : LABEL Statement
    '''
    p[0] = ('label', p[1], p[2])


# Declarations
def p_declaration(p):
    '''
    Declaration : Type_spec Var_list
    '''
    p[0] = ('decl', p[1], p[2])

def p_type_spec(p):
    '''
    Type_spec : INTEGER
              | REAL
              | LOGICAL
              | CHARACTER
    '''
    p[0] = p[1]

# Lista de variáveis
def p_var_list_rec(p):
    '''
    Var_list : Var_list ',' Var
    '''
    p[0] = p[1] + [p[3]]

def p_var_list_one(p):
    '''
    Var_list : Var
    '''
    p[0] = [p[1]]

#Variáveis
def p_var_id(p):
    '''
    Var : IDENTIFIER
    '''
    p[0] = ('var', p[1])

def p_var_array(p):
    '''
    Var : IDENTIFIER '(' INT ')'
    '''
    p[0] = ('array', p[1], p[3])


# Assignments
def p_assignment_var(p):
    '''
    Assignment : IDENTIFIER '=' Expr
    '''
    p[0] = ('assign', p[1], p[3])

def p_assignment_array(p):
    '''
    Assignment : IDENTIFIER '(' Expr ')' '=' Expr
    '''
    p[0] = ('assign_array', p[1], p[3], p[6])


# If e If/Else
def p_if_stmt(p):
    '''
    If_stmt : IF '(' Expr ')' THEN Stmt_block ENDIF
            | IF '(' Expr ')' THEN Stmt_block ELSE Stmt_block ENDIF
    '''
    if len(p) == 8:
        p[0] = ('if', p[3], p[6])
    else:
        p[0] = ('if_else', p[3], p[6], p[8])


# DO
def p_do_stmt(p):
    '''
    Do_stmt : DO LABEL IDENTIFIER '=' Expr ',' Expr
            | DO LABEL IDENTIFIER '=' Expr ',' Expr ',' Expr
    '''
    if len(p) == 8:
        p[0] = ('do', p[2], p[3], p[5], p[7], ('int', 1))
    else:
        p[0] = ('do', p[2], p[3], p[5], p[7], p[9])


# GOTO
def p_goto_stmt(p):
    '''
    Goto_stmt : GOTO LABEL
    '''
    p[0] = ('goto', p[2])


# CONTINUE / RETURN
def p_continue_stmt(p):
    '''
    Continue_stmt : CONTINUE
    '''
    p[0] = ('continue',)

def p_return_stmt(p):
    '''
    Return_stmt : RETURN
    '''
    p[0] = ('return',)


# IO
def p_io_stmt(p):
    '''
    Io_stmt : READ '*' ',' Arg_list
            | PRINT '*' ',' Arg_list
    '''
    p[0] = (p[1].lower(), p[4])


def p_arg_list_rec(p):
    '''
    Arg_list : Arg_list ',' Expr
    '''
    p[0] = p[1] + [p[3]]

def p_arg_list_one(p):
    '''
    Arg_list : Expr
    '''
    p[0] = [p[1]]


# ==========================================================
# EXPRESSÕES
# Precedência via níveis gramaticais
# OR -> AND -> REL -> ADD -> MUL -> POW -> UNARY -> ATOM
# ==========================================================

def p_expr(p):
    '''
    Expr : Or_expr
    '''
    p[0] = p[1]


# Or
def p_or_expr_rec(p):
    '''
    Or_expr : Or_expr OP_OR And_expr
    '''
    p[0] = ('binop', p[2], p[1], p[3])

def p_or_expr_one(p):
    '''
    Or_expr : And_expr
    '''
    p[0] = p[1]


# And
def p_and_expr_rec(p):
    '''
    And_expr : And_expr OP_AND Rel_expr
    '''
    p[0] = ('binop', p[2], p[1], p[3])

def p_and_expr_one(p):
    '''
    And_expr : Rel_expr
    '''
    p[0] = p[1]


# Expressões relacionais
def p_rel_expr_cmp(p):
    '''
    Rel_expr : Add_expr Relop Add_expr
    '''
    p[0] = ('binop', p[2], p[1], p[3])

def p_rel_expr_one(p):
    '''
    Rel_expr : Add_expr
    '''
    p[0] = p[1]


def p_relop(p):
    '''
    Relop : OP_EQ
          | OP_NE
          | OP_LT
          | OP_LE
          | OP_GT
          | OP_GE
    '''
    p[0] = p[1]


# Adição e subtração
def p_add_expr_binary(p):
    '''
    Add_expr : Add_expr '+' Mul_expr
             | Add_expr '-' Mul_expr
    '''
    p[0] = ('binop', p[2], p[1], p[3])

def p_add_expr_one(p):
    '''
    Add_expr : Mul_expr
    '''
    p[0] = p[1]


# Multiplicação e divisão
def p_mul_expr_binary(p):
    '''
    Mul_expr : Mul_expr '*' Pow_expr
             | Mul_expr '/' Pow_expr
    '''
    p[0] = ('binop', p[2], p[1], p[3])

def p_mul_expr_one(p):
    '''
    Mul_expr : Pow_expr
    '''
    p[0] = p[1]


# Potências, com  associatividade à direita
def p_pow_expr_rec(p):
    '''
    Pow_expr : Unary_expr OP_POW Pow_expr
    '''
    p[0] = ('binop', p[2], p[1], p[3])

def p_pow_expr_one(p):
    '''
    Pow_expr : Unary_expr
    '''
    p[0] = p[1]


# expressões unárias
def p_unary_minus(p):
    '''
    Unary_expr : '-' Unary_expr
    '''
    p[0] = ('neg', p[2])

def p_unary_not(p):
    '''
    Unary_expr : OP_NOT Unary_expr
    '''
    p[0] = ('not', p[2])

def p_unary_atom(p):
    '''
    Unary_expr : Atom
    '''
    p[0] = p[1]


# expressões atómicas
def p_atom_group(p):
    '''
    Atom : '(' Expr ')'
    '''
    p[0] = p[2]

def p_atom_int(p):
    '''
    Atom : INT
    '''
    p[0] = ('int', p[1])

def p_atom_real(p):
    '''
    Atom : REALNUMB
    '''
    p[0] = ('real', p[1])

def p_atom_bool(p):
    '''
    Atom : BOOL
    '''
    p[0] = ('bool', p[1])

def p_atom_str(p):
    '''
    Atom : STR
    '''
    p[0] = ('str', p[1])

def p_atom_id(p):
    '''
    Atom : IDENTIFIER
    '''
    p[0] = ('id', p[1])

def p_atom_call(p):
    '''
    Atom : IDENTIFIER '(' Arg_list ')'
    '''
    p[0] = ('call', p[1], p[3])

def p_error(p):
    if p:
        print(f"Erro sintático: token inesperado {p.type} ({p.value})")
    else:
        print("Erro sintático: fim inesperado do ficheiro")


parser = yacc.yacc()

if __name__ == '__main__':
    
    lx = Lexer()
    lx.build()

    with open("../tests/examples/hello.f", encoding="utf-8") as f:
        data = f.read()

    lx.input(data, fixed_form=True)

    result = parser.parse(lexer=lx.lexer)
    print(result)