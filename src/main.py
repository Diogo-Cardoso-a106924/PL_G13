import sys
import os
from typing import Optional
from parser import Parser
from semantic import SemanticAnalyzer
from optimizer import optimize_ast
from ewvm import generate_ewvm
from symbol_table import SemanticError

BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):    print(f"  ✓ {msg}")
def fail(msg):  print(f"  ✗ {msg}")


# Compilação de um ficheiro

def compile_file(
    path: str,
    expect_error: bool = False,
) -> bool:
    try:
        with open(path) as f:
            data = f.read()
    except FileNotFoundError:
        fail(f"Ficheiro não encontrado: {path}")
        return False

    try:
        parser = Parser()
        parser.build()
        ast = parser.parse(data)

        if parser.lexer.lex_errors:
            for err in parser.lexer.lex_errors:
                print(err)
            raise SyntaxError("Erros léxicos encontrados")

        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)

        ast = optimize_ast(ast)

        if not expect_error:
            emit_ewvm = path.rsplit(".", 1)[0] + ".ewvm"
            vm = generate_ewvm(ast)
            with open(emit_ewvm, "w", encoding="utf-8") as out:
                out.write(vm)

        if expect_error:
            fail("Esperava um erro mas o programa foi aceite")
            return False
        else:
            ok("Programa aceite")
            return True

    except SyntaxError as e:
        if expect_error:
            ok(f"Erro sintático/léxico detetado (esperado): {e}")
            return True
        else:
            fail(f"Erro léxico/sintático inesperado: {e}")
            return False

    except SemanticError as e:
        if expect_error:
            ok(f"Erro semântico detetado (esperado): {e}")
            return True
        else:
            fail(f"Erro semântico inesperado: {e}")
            return False


# Modo de teste

def collect_f_tests(root: str):
    """Todos os `.f` sob `root` (recursivo), ordenados por caminho."""
    if not os.path.isdir(root):
        return []
    out = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.endswith('.f'):
                out.append(os.path.join(dirpath, name))
    return sorted(out)


def run_test_suite(
    valid_dir: str,
    invalid_dir: str,
    examples_dir: Optional[str] = None,
):
    """
    Corre todos os ficheiros `.f` em valid_dir, invalid_dir e examples_dir (inclui subpastas).
    """
    passed = 0
    failed = 0

    if os.path.isdir(valid_dir):
        files = collect_f_tests(valid_dir)
        if files:
            print(f"\n{BOLD}── Testes válidos (devem ser aceites) ──{RESET}")
            for path in files:
                label = os.path.relpath(path, valid_dir)
                print(f"\n  {BOLD}{label}{RESET}")
                if compile_file(
                    path,
                    expect_error=False,
                ):
                    passed += 1
                else:
                    failed += 1

    if os.path.isdir(invalid_dir):
        files = collect_f_tests(invalid_dir)
        if files:
            print(f"\n{BOLD}── Testes inválidos (devem dar erro) ──{RESET}")
            for path in files:
                label = os.path.relpath(path, invalid_dir)
                print(f"\n  {BOLD}{label}{RESET}")
                if compile_file(
                    path,
                    expect_error=True,
                ):
                    passed += 1
                else:
                    failed += 1

    if examples_dir and os.path.isdir(examples_dir):
        files = collect_f_tests(examples_dir)
        if files:
            print(f"\n{BOLD}── Exemplos ──{RESET}")
            for path in files:
                label = os.path.relpath(path, examples_dir)
                name = os.path.basename(path).lower()
                expect_err = name.startswith("erro_")
                status_msg = "deve dar erro" if expect_err else "deve ser aceite"
                print(f"\n  {BOLD}{label}{RESET} ({status_msg})")
                if compile_file(
                    path,
                    expect_error=expect_err,
                ):
                    passed += 1
                else:
                    failed += 1

    total = passed + failed
    print(f"\n{BOLD}{'─'*42}{RESET}")
    print(f"  {BOLD}{passed}/{total} testes passaram{RESET}")
    if failed > 0:
        print(f"  {failed} falhou(aram)")
    print()

    return failed == 0


if __name__ == '__main__':
    args = sys.argv[1:]
    paths = [a for a in args if not a.startswith('--')]

    if paths:
        print(f"\n{BOLD}Modo manual{RESET}")
        all_ok = True
        for path in paths:
            print(f"\n{BOLD}── {path} ──{RESET}")
            expect_err = 'invalid' in path
            if not compile_file(
                path,
                expect_error=expect_err,
            ):
                all_ok = False
        sys.exit(0 if all_ok else 1)

    # Sem argumentos - corre todos os testes
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    valid_dir   = os.path.join(base, 'tests', 'valid')
    invalid_dir = os.path.join(base, 'tests', 'invalid')
    examples_dir = os.path.join(base, 'tests', 'examples')

    print(f"{BOLD}Compilador Fortran 77 — Suite de Testes{RESET}")

    success = run_test_suite(
        valid_dir,
        invalid_dir,
        examples_dir=examples_dir,
    )
    sys.exit(0 if success else 1)
