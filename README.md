# PL_G13
Processamento de Linguagens - Realização do trabalho prático - UMINHO LEI 2526

## Descrição Geral

Este projeto consiste no desenvolvimento de um compilador para um subconjunto da linguagem Fortran 77. O compilador realiza análise léxica, sintática e semântica, aplica otimizações simples e gera código EWVM.

## Instruções de Utilização

Para correr todos os testes do compilador:

```bash
python3 src/main.py
```

Para compilar um ficheiro Fortran específico:

```bash
python3 src/main.py caminho/para/ficheiro.f
```

O ficheiro EWVM gerado fica na mesma pasta do ficheiro `.f`, com a extensão `.ewvm`.

## Grupo de Trabalho

Constituintes do grupo de trabalho:

- a100753 - Rui Miguel Sampaio Castro
- a106923 - Eduardo Santana de Freitas
- a106924 - Diogo António Azevedo Ribeiro Cardoso