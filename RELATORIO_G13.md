# Relatório do Trabalho Prático — PL 2025/26 - Compilador FORTRAN 77

**Unidade Curricular:** Processamento de Linguagens (PL)  
**Ano Letivo:** 2025/2026  
**Grupo:** G13

| Nome | Número |
|---|---|
| Rui Miguel Sampaio Castro | A100753 |
| Eduardo Santana de Freitas | A106923 |
| Diogo António Azevedo Ribeiro Cardoso | A106924 |

---

## Índice

1. [Resumo](#1-resumo)
2. [Introdução e Objetivos](#2-introdução-e-objetivos)
3. [Visão Geral da Arquitetura](#3-visão-geral-da-arquitetura)
4. [Análise Léxica](#4-análise-léxica)
5. [Análise Sintática](#5-análise-sintática)
6. [Análise Semântica](#6-análise-semântica)
7. [Geração de Código EWVM](#7-geração-de-código-ewvm)
8. [Otimização](#8-otimização)
9. [Testes e Validação](#9-testes-e-validação)
10. [Limitações e Trabalho Futuro](#10-limitações-e-trabalho-futuro)
11. [Conclusão](#11-conclusão)

---

## 1. Resumo

Este relatório descreve o desenvolvimento de um compilador para um subconjunto significativo da linguagem **Fortran 77**, implementado em Python com recurso às ferramentas `ply.lex` e `ply.yacc`. O compilador realiza análise léxica, análise sintática, análise semântica e geração de código, sendo que a geração de código tem como alvo a **EWVM** (Educational Wide Virtual Machine).

---

## 2. Introdução e Objetivos

O projeto proposto no âmbito da unidade curricular de Processamento de Linguagens consistiu na construção de um compilador para a linguagem **Fortran 77 standard** (ANSI X3.9-1978), capaz de:

- Realizar análise léxica, sintática e semântica de programas Fortran;
- Gerar código executável para a máquina virtual EWVM;

---

## 3. Visão Geral da Arquitetura

O compilador segue uma arquitetura clássica de **pipeline**, onde cada fase consome a saída da anterior e produz uma representação adequada para a fase seguinte:

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────────┐    ┌─────────┐    ┌─────────┐
│  .f     │───▶│  Lexer   │───▶│  Parser  │───▶│ Semântica   │───▶│Optimizer│───▶│ Gerador │───▶ .ewvm
│(source) │    │(ply.lex) │    │(ply.yacc)│    │(visitantes) │    │ (AST)   │    │ (EWVM)  │
└─────────┘    └──────────┘    └──────────┘    └─────────────┘    └─────────┘    └─────────┘
```

### 3.1 Organização do Código

O projeto é estruturado de formula modular, de modo a ser mais compreensivel e de mais fácil atualização:

| Módulo | Responsabilidade |
|--------|------------------|
| `tokenizer.py` | Analisador léxico (PLY lex) |
| `parser.py` | Analisador sintático (PLY yacc) + gramática |
| `symbol_table.py` | Tabela de símbolos com suporte a âmbitos |
| `semantic/` | Pacote para análise semântica (core, declarações, statements, fluxo) |
| `optimizer.py` | Otimização sobre a AST |
| `ewvm/` | Geração de código EWVM (layout, emissão de expr/stmt) |
| `main.py` | Programa que deve ser executado |

### 3.2 Representação Intermédia (AST)

A AST é representada de forma simples e eficiente como **tuplos Python**, onde o primeiro elemento é uma *tag* simbólica que identifica o tipo de nó:

```python
('program', 'HELLO', ('body', [], [...]), 1)
('assignment', 'X', ('+', ('int', 5), ('int', 3)), 10)
('if', condition, then_body, else_body, elseif_chain, lineno)
```

A utilização de tuplos traz várias vanttagens entre as quais permitir um percurso recursivo fácil no analisador semântico e ser manipulada diretamente pelo otimizador.

---

## 4. Análise Léxica

**Ficheiro:** `src/tokenizer.py`  
**Ferramenta:** PLY Lex

### 4.1 Conjunto de Tokens

O lexer reconhece os seguintes tipos de tokens:

| Categoria | Tokens |
|-----------|--------|
| **Palavras-chave** | `PROGRAM`, `END`, `FUNCTION`, `SUBROUTINE`, `RETURN`, `CALL`, `INTEGER`, `REAL`, `LOGICAL`, `CHARACTER`, `DOUBLE_PRECISION`, `IF`, `THEN`, `ELSE`, `ELSEIF`, `ENDIF`, `DO`, `CONTINUE`, `GOTO`, `READ`, `PRINT`, `WRITE`, `DATA`, `DIMENSION`, `COMMON`, `PARAMETER`, `STOP` |
| **Operadores pontuados** | `.AND.`, `.OR.`, `.NOT.`, `.EQV.`, `.NEQV.`, `.EQ.`, `.NE.`, `.LT.`, `.LE.`, `.GT.`, `.GE.` |
| **Operadores simbólicos** | `+`, `-`, `*`, `/`, `**`, `//`, `=`, `(`, `)`, `,`, `:` |
| **Literais** | `INT` (números inteiros), `REALNUMB` (reais), `STR` (strings com aspas), `BOOL` (`.TRUE.`/`.FALSE.`) |
| **Outros** | `IDENTIFIER`, `NEWLINE` |

### 4.2 Decisões de Implementação

**Formato escolhido:** O grupo optou por implementar o compilador que suporte o **formato livre** (*free-form*), onde as linhas não têm posições de coluna fixas. Esta decisão simplificou significativamente o lexer e alinha-se com as práticas modernas de Fortran (Fortran 90+). Comentários são iniciados por `!` e a continuação de linha é feita com `&` no final da linha.

**Case-insensitivity:** As palavras-chave e identificadores são tratados de forma *case-insensitive*. O lexer normaliza os tokens para maiúsculas durante o reconhecimento, exceto em literais string onde o caso é preservado.

**Tratamento especial de `DOUBLE PRECISION`:** Implementámos uma regra específica que antecipa a sequência `DOUBLE` seguida de `PRECISION`, consumindo ambos como um único token `DOUBLE_PRECISION`, que é internamente tratado como `REAL`.

**Informação de localização:** Para mensagens de erro mais úteis, o lexer regista a **linha e coluna** de cada token utilizando a função `find_column()`, permitindo assim visualizar e identificar qual o token responsável pelo erro.


### 4.3 Tratamento de Erros Léxicos

Caracteres não reconhecidos disparam uma mensagem de erro com indicação precisa da posição (linha e coluna), e o lexer continua a processamento (*skip*) detetando assim múltiplos erros. As mensagens são armazenadas em `lex_errors` e, se houver qualquer erro léxico, o compilador termina antes da análise sintática.

---

## 5. Análise Sintática

**Ficheiro:** `src/parser.py`  
**Ferramenta:** PLY Yacc

### 5.1 Gramática Implementada

A gramática foi projetada para cobrir as construções do subconjunto Fortran 77, com ênfase na **resolução de ambiguidades** típicas da linguagem.

#### Estrutura de Alto Nível

```
start → program | program subprograms | subprograms
program → PROGRAM IDENTIFIER NEWLINE body END NEWLINE
subprograms → subprogram | subprograms subprogram
subprogram → function | subroutine
function → type FUNCTION IDENTIFIER '(' arg_list ')' NEWLINE body END NEWLINE
subroutine → SUBROUTINE IDENTIFIER '(' arg_list')' NEWLINE body END NEWLINE | subroutine_noparens NEWLINE body END NEWLINE
subroutine_noparens → SUBROUTINE IDENTIFIER
```

#### Corpo e Declarações

```
body → declarations statements
declarations → declarations declaration | empty
declaration → type var_list NEWLINE
            | DIMENSION dim_decl_list NEWLINE
            | DATA data_group NEWLINE
            | COMMON ident_opt var_list NEWLINE
            | PARAMETER '(' list_const ')' NEWLINE
```

#### Expressões (com precedência explícita)

A precedência é definida na tabela abaixo (da mais fraca para a mais forte):

| Nível | Operadores |
|-------|------------|
| 1 | `.EQV.`, `.NEQV.` |
| 2 | `.OR.` |
| 3 | `.AND.` |
| 4 | `.NOT.` (unário, direita) |
| 5 | `.EQ.`, `.NE.`, `.LT.`, `.LE.`, `.GT.`, `.GE.` |
| 6 | `//` (concatenação) |
| 7 | `+`, `-` (binários) |
| 8 | `*`, `/` |
| 9 | `-` unário (`UMINUS`) |
| 10| `**` (potência, direita) |

Esta definição permite expressões como:
```fortran
IF (A .GT. 0 .AND. B .LT. 10 .OR. C .EQ. 0) THEN
```
sem ambiguidade de parsing.

### 5.2 Construção da AST

Cada regra de produção constrói um tuplo com a estrutura:

```python
def p_program(self, p):
    r"program : PROGRAM IDENTIFIER NEWLINE body END NEWLINE"
    p[0] = ('program', p[2], p[4], p.lineno(1))
```

O número de linha (`p.lineno(1)`) é preservado para permitir mensagens de erro semântico mais completas.

### 5.3 Tratamento de casos específicos

1. **Chamada de função** vs. **acesso a array** vs. **substring**:
   ```fortran
   X = FUNC(A)     ! chamada de função
   X = ARRAY(I)    ! acesso a array
   X = STR(1:3)    ! substring
   ```

    A solução implementada:
    - `atom → IDENTIFIER '(' arg_list ')'` → chamada de função
    - `atom → IDENTIFIER '(' substring_range ')'` → substring
    - `read_item → IDENTIFIER '(' expr ')'` → array index

    A produção `substring_range` produz um tuplo especial `('sspan', lo, hi)` que é distinguido nas regras superiores.

2. **Subrotina sem parênteses** (válido em Fortran 77):
   A gramática inclui a produção `subroutine_noparens` para capturar o caso em que a subroutine não recebe uma lista de argumentos .

---

## 6. Análise Semântica

**Pacote:** `src/semantic/`  
**Tabela de Símbolos:** `src/symbol_table.py`

### 6.1 Arquitetura do analisador semântico

O analisador semântico foi estruturado segundo o **padrão Visitor**, com métodos `visit_<node_type>` para cada tipo de nó na AST. Para manter o código organizado face à dimensão da linguagem, os visitors foram distribuídos por quatro mixins:

| Mixin | Responsabilidade |
|-------|------------------|
| `SemanticCoreMixin` | Tipos de expressões, intrínsecas, percurso geral e rótulos |
| `SemanticDeclarationsMixin` | `DECLARATION`, `DIMENSION`, `DATA`, `COMMON`, `PARAMETER` |
| `SemanticStatementsMixin` | Atribuições, I/O, chamadas, arrays, substrings |
| `SemanticControlFlowMixin` | `IF`, `DO`, `GOTO`, operadores unários especiais |

A classe `SemanticAnalyzer` herda de todos os mixins, agregando a funcionalidade completa.

### 6.2 Tabela de Símbolos

A tabela de símbolos implementa um conjunto de dicionários para suportar scopes diferentes (programa principal, funções, subrotinas):

```python
class SymbolTable:
    def __init__(self):
        self.__table = [{}]  
        self.__var_count = 0
```

Cada entrada na tabela regista:
- **kind**: `var`, `const`, `fun`, `sub`
- **type**: tipo da entidade (ex: `INTEGER`, `REAL`, `LOGICAL`, `CHARACTER`, ou tuplo para arrays)
- **index**: índice interno (para alocação de memória)
- **initialized**: booleano que indica se a variável já foi inicializada

**Operações principais:**
- `push()` / `pop()`: gerir scopes aninhados
- `declare_var()`: declarar variável no scope atual
- `lookup_var()`: procurar variável na pilha (do mais interno para o externo)
- `promote_var_to_const()`: converter variável em constante (`PARAMETER`)
- `declare_fun()` / `declare_sub()`: declarar subprogramas e funções

### 6.3 Verificações Semânticas Implementadas

#### Declarações
- Duplicação de identificadores no mesmo scope
- Compatibilidade entre tipo declarado e tipo de retorno de função
- Dimensões de arrays consistentes entre declarações
- `PARAMETER` só pode ser aplicado a variáveis simples

#### Expressões
- Tipos compatíveis em operações binárias:
  - Aritméticas: `INTEGER` com `INTEGER` → `INTEGER`; `INTEGER` ou `REAL` com `REAL`  → `REAL`
  - Lógicas: operandos devem ser `LOGICAL`
  - Relacionais: operandos devem ser comparáveis (numéricos ou strings)
  - Concatenação `//`: operandos devem ser `CHARACTER`
- Substrings: apenas aplicáveis a variáveis `CHARACTER` escalares

#### Fluxo de Controlo
- **Rótulos**: são recolhidos com deteção de duplicados
- **GOTO**: verificação de existência do rótulo destino
- **DO**: a variável de controlo deve ser `INTEGER` ou `REAL`; o corpo deve conter uma instrução com o rótulo do `DO` (tipicamente `CONTINUE`)
- **IF**: condição deve ser `LOGICAL`

#### Subprogramas
- **Aridade**: número de argumentos deve corresponder à declaração
- **Tipos dos argumentos**: compatibilidade com os parâmetros formais
- **Chamada**: `CALL` só pode invocar subrotinas, enquanto que as funções só podem ser usadas em expressões
- **Retorno**: todas as funções devem atribuir valor ao prórprio nome da função

#### Inicialização
- Uso de variáveis não inicializadas é detetado (exceto em contextos específicos como argumentos de `CALL`)
- `DATA` inicializa variáveis no momento da declaração
- `PARAMETER` define constantes imutáveis

### 6.4 Exemplo de Verificação Semântica

**Código inválido:**
```fortran
PROGRAM TEST
    INTEGER X
    X = Y + 1      ! Y não declarada
    PRINT *, X
END
```

**Mensagem de erro:**
```
Erro semântico: Variável 'Y' não declarada (linha 3)
```

---

## 7. Geração de Código EWVM

**Pacote:** `src/ewvm/`

### 7.1 Visão Geral da EWVM

A EWVM (Educational Wide Virtual Machine) é uma máquina virtual stack-based com as seguintes características:
- **Pilha de operandos** para computação
- **Memória heap** para alocação dinâmica (usada para variáveis globais, COMMON, e resultados de funções)
- **Frame pointer** para acesso a variáveis locais e parâmetros
- **Instruções** típicas: `PUSHI`, `PUSHF`, `PUSHS`, `ADD`, `SUB`, `MUL`, `DIV`, `JUMP`, `CALL`, `RETURN`, `READ`, `WRITEI`, etc.

### 7.2 Layout de Memória

Antes da geração de código, o compilador calcula o **layout de memória**:

```python
class LayoutBuilder:
    def build(self) -> ProgramLayout:
        # 1. Recolher todas as variáveis globais e COMMON blocks
        # 2. Alocar variáveis na heap (endereços consecutivos)
        # 3. Reservar temporários para potenciação (pow_tmp0, pow_tmp1, str_tmp)
        # 4. Construir tabela ASCII para conversão char→string
        # 5. Para cada subprograma, calcular layout da frame (parâmetros + locais)
```

**Organização da memória:**
```
Heap:
  [0...N-1]  Variáveis globais + COMMON
  [N...N+2]  Temporários (pow_tmp0, pow_tmp1, str_tmp)
  [N+3...M]  Tabela ASCII (128 células)
```

**Frame de subprograma:**
```
        +-----------------+
        |  parâmetro N     |  ← FP + (N)
        |  ...             |
        |  parâmetro 1     |
        +-----------------+
        |  variável local 1|  ← FP - 1
        |  ...             |
        |  variável local K|
        +-----------------+
```

### 7.3 Estratégia de Emissão

A geração de código segue um padrão visitor semelhante à análise semântica, com mixins especializados:

| Mixin | Responsabilidade |
|-------|------------------|
| `EWVMEmitCoreMixin` | Operações de baixo nível: etiquetas, heap, células, tabela ASCII |
| `EWVMExprMixin` | Expressões: aritmética, lógica, arrays, strings, intrínsecas, chamadas |
| `EWVMStmtMixin` | Statements: programa, DATA, I/O, IF, DO, CALL, RETURN |

### 7.4 Exemplos de Emissão

**Atribuição simples:**
```fortran
X = 42
```
Gera:
```
PUSHI 42
STOREL 0       (assumindo X na posição 0 da frame)
```

**DO loop:**
```fortran
DO 10 I = 1, 10
    S = S + I
10 CONTINUE
```
Gera:
```
PUSHI 1
STOREL I
L1:
PUSHL I
PUSHI 10
INFEQ
JZ L2
PUSHL S
PUSHL I
ADD
STOREL S
PUSHL I
PUSHI 1
ADD
STOREL I
JUMP L1
L2:
```

### 7.5 Tratamento de Arrays

O acesso a arrays multidimensionais utiliza **cálculo de offset** baseado na ordem de armazenamento *column-major* (padrão Fortran):

```python
def fortran_offset_1based(dims, idxs):
    # Exemplo: array(2,3) com índices (i,j)
    # offset = (i-1) + (j-1) * 2
    off, stride = 0, 1
    for j in range(len(dims)):
        off += (idxs[j] - 1) * stride
        stride *= int(dims[j])
    return off
```

---

## 8. Otimização

**Ficheiro:** `src/optimizer.py`

### 8.1 Técnicas Implementadas

O otimizador percorre a AST e aplica transformações locais antes da geração de código:

| Técnica | Descrição | Exemplo |
|---------|-----------|---------|
| **Constant folding** | Avaliação de expressões constantes em tempo de compilação | `2 + 3` → `5` |
| **Simplificação algébrica** | Eliminação de operações neutras | `x + 0` → `x`; `x * 1` → `x` |
| **Simplificação lógica** | Eliminação de operações lógicas redundantes | `x .AND. .TRUE.` → `x` |
| **Remoção de código morto** | Eliminação de instruções sem efeito | `x = x` é removido |
| **IF constante** | Remoção de branches que nunca são executadas | `IF (.FALSE.) THEN ...` remove o corpo |


### 8.2 Preservação de Rótulos

A otimização não remove instruções etiquetadas que possam ser destino de `GOTO` ou `DO`. Se um `CONTINUE` etiquetado se tornar o único conteúdo de um `DO`, ele é mantido ou substituído por `CONTINUE` se necessário.

---

## 9. Testes e Validação

### 9.1 Estrutura dos Testes

O conjunto de testes está organizada em três diretórios:

```
tests/
├── valid/          # Programas que devem ser aceites
│   ├── program/
│   ├── expressions/
│   ├── if/
│   ├── do/
│   ├── goto/
│   ├── subprograms/
│   ├── arrays_dimension/
│   ├── common/
│   ├── data/
│   └── substring/
├── invalid/        # Programas que devem ser rejeitados 
│   ├── variables/
│   ├── calls/
│   ├── do/
│   ├── if/
│   ├── goto/
│   └── ...
└── examples/       # Exemplos do enunciado (5 testes)
```

### 9.2 Execução de Testes

O comando `python3 src/main.py` sem argumentos executa **todos os testes**:

## 10. Limitações e Trabalho Futuro

### 10.1 Limitações Atuais

| Limitação | Descrição |
|-----------|-----------|
| **Formato fixo** | O compilador não suporta o formato tradicional de colunas fixas |
| **IMPLICIT** | Declarações implícitas de tipos (IMPLICIT NONE é assumido) |
| **I/O formatado** | Apenas formato livre (`*`) é suportado; `FORMAT` não implementado |
| **Unidades de ficheiro** | READ/WRITE apenas para stdin/stdout (unidade *) |
| **DOUBLE PRECISION** | Tratado como REAL (não há precisão estendida na VM) |
| **Intrínsecas** | Apenas 7 funções intrínsecas estão implementadas |
| **DATA com implied-DO** | Não suporta repetições complexas no DATA |
| **Substrings** | Apenas sobre variáveis CHARACTER escalares (não arrays) |

### 10.2 Trabalho Futuro

Extensões possíveis para melhorar o compilador:

1. **Suporte a FORMAT**: Implementar parsing de formatos e geração de I/O formatado
2. **Arquivos**: Suporte a READ/WRITE com unidades de ficheiro
3. **INCLUDE**: Processamento de ficheiros incluídos
4. **Mais intrínsecas**: `SQRT`, `EXP`, `LOG`, `MAX`, `MIN`, `CHAR`, `ICHAR`
5. **Otimizações globais**: Análise de fluxo de dados, eliminação de subexpressões comuns
6. **Suporte a IMPLICIT**: Regras de tipagem implícita (I-N rule)

---

## 11. Conclusão

O compilador desenvolvido cumpre com sucesso os objetivos propostos no enunciado do projeto, implementando um **subconjunto significativo da linguagem Fortran 77** com as quatro fases clássicas: análise léxica, análise sintática, análise semântica e geração de código.

**Principais realizações:**

- **Corretude**: 69 testes implementados, todos aprovados, cobrindo desde programas simples até construções avançadas como arrays multidimensionais, COMMON blocks, DATA initialization e substrings.
- **Modularidade**: Código organizado em módulos com responsabilidades bem definidas, utilizando o padrão Visitor para análise semântica e geração de código.
- **Funcionalidade**: Suporte completo a tipos, expressões, controlo de fluxo, subprogramas, arrays, estruturas estáticas (`COMMON`, `DATA`, `PARAMETER`) e otimizações.
- **Eficiência**: Otimizador com constant folding e simplificações algébricas; geração de código EWVM com layout de memória calculado estaticamente.

Assim, o grupo conclui que o projeto permitiu consolidar conhecimentos fundamentais sobre **processamento de linguagens** , construção de lexers e parsers, implementação de análise semântica com tabela de símbolos, e geração de código para uma máquina virtual. A arquitetura modular adotada facilita futuras extensões, como suporte a I/O formatado ou novas otimizações.