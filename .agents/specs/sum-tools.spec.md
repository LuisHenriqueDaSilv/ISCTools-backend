# Spec: `base_add` e `base_multiply`

### 1. Assinaturas

```python
@tool
def base_add(operands: list[str], base: int) -> str:
    """Soma N números em uma base qualquer, exibindo o passo a passo com linha de carry.

    Args:
        operands: Lista de números a somar, como strings na base indicada.
                  Use prefixo '-' para negativos (ex: '-1011').
        base: Base numérica comum a todos os operandos (2 a 36).
    """

@tool
def base_multiply(a: str, b: str, base: int) -> str:
    """Multiplica dois números em uma base qualquer, exibindo produtos parciais.

    Args:
        a: Primeiro operando como string na base indicada. Use '-' para negativo.
        b: Segundo operando como string na base indicada. Use '-' para negativo.
        base: Base numérica dos operandos (2 a 36).
    """
```

---

### 2. Validações (ambas as tools)

| Condição | Erro retornado |
|---|---|
| `base` fora de [2, 36] | `"Base inválida: deve estar entre 2 e 36."` |
| Dígito inválido para a base | `"Caractere inválido 'X' para base N."` |
| `operands` vazio ou com 1 elemento | `"Informe ao menos dois operandos."` |

Reutilizar `_SIMBOLOS` e a validação já existente em `_converter_base`.

---

### 3. Algoritmo — `base_add`

#### 3.1 Tratamento de sinal
1. Separar sinal e magnitude de cada operando.
2. Se **todos os sinais forem iguais**: somar as magnitudes e aplicar o sinal ao resultado.
3. Se **sinais mistos**: converter cada parcela para decimal, somar algebricamente, converter o resultado de volta para a base. Mostrar nota: `"Operandos de sinais opostos — soma realizada via conversão decimal intermediária."` (não exibir grade de carry nesse caso, pois o passo a passo seria subtração, fora do escopo desta tool).

#### 3.2 Soma de magnitudes (mesmo sinal)
1. Normalizar comprimento: pad com `'0'` à esquerda até todos terem o mesmo tamanho.
2. Iterar colunas **da direita para a esquerda**:
   - `total = carry_in + Σ dígitos da coluna`
   - `digit_out = total % base`
   - `carry_out = total // base`
3. Se ao final `carry_out > 0`, acrescentar à esquerda do resultado.

#### 3.3 Formato de saída

```
  Carry:  0  1  1  0
          1  0  1  1
        + 0  1  1  0
        + 0  0  1  1
        -----------
        1  0  1  0  0
```

Regras de formatação:
- Cada dígito ocupa uma célula de largura fixa (largura = 1 + len do maior dígito em bases > 10, ou 2 para bases ≤ 10).
- A linha `Carry:` exibe os carries produzidos em cada coluna; suprimir a linha inteira se todos os carries forem zero.
- O operador (`+`) aparece alinhado à esquerda, somente no segundo operando (os demais ficam recuados com espaço).
- Linha separadora de `-` com o mesmo comprimento da linha mais longa.
- Resultado precedido de sinal se negativo.

---

### 4. Algoritmo — `base_multiply`

#### 4.1 Tratamento de sinal
1. Extrair sinais de `a` e `b`.
2. Calcular sinal do resultado: negativo se exatamente um dos dois for negativo.
3. Trabalhar apenas com as magnitudes.

#### 4.2 Produtos parciais
1. Iterar cada dígito de `b` **da direita para a esquerda** (índice `i`, começando em 0):
   - Multiplicar a magnitude de `a` pelo dígito `b[i]`, dígito a dígito com carry.
   - Resultado parcial = produto + `i` zeros à direita (shift).
2. Somar todos os produtos parciais usando a lógica de `base_add` (internamente, sem formatar novamente).
3. Aplicar sinal ao resultado final.

#### 4.3 Formato de saída

```
        1  0  1  1
      ×    1  1  0
      -----------
        0  0  0  0      (× 0, shift 0)
     1  0  1  1         (× 1, shift 1)
  1  0  1  1            (× 1, shift 2)
  -------------------
  1  0  0  0  0  1  0
```

Regras de formatação:
- Cada produto parcial é alinhado à direita com padding de zeros (ou espaços) para refletir o shift.
- O comentário `(× D, shift N)` é exibido ao final de cada linha de produto parcial.
- A linha de separação final tem o comprimento do resultado.
- Resultado precedido de sinal se negativo.

---

### 5. Adições ao `_SYSTEM_PROMPT` em `agent.py`

```
**base_add** — chame para somar dois ou mais números na mesma base, exibindo carries coluna a coluna.
Gatilhos: "some", "adição em base", "quanto é X + Y em binário/octal/hex", "resultado da soma".
Pré-condição: se os operandos estiverem em bases diferentes, converta-os primeiro com base_converter para a base desejada, depois chame base_add.

**base_multiply** — chame para multiplicar dois números em uma base, exibindo produtos parciais.
Gatilhos: "multiplique", "multiplicação em base", "quanto é X × Y em binário/octal/hex", "produto de".
Pré-condição: mesma que base_add — bases devem ser iguais; converta antes com base_converter se necessário.
```

---

### 6. Registro em `get_tools()`

```python
def get_tools() -> list:
    return [
        assembler, disassembler, base_converter,
        float_to_ieee754, ieee754_to_float, imme_calc,
        base_add, base_multiply,   # novas tools
    ]
```

---

### 7. Exemplos de entrada/saída esperada

**`base_add(["1011", "0110", "0011"], 2)`**
```
  Carry:  1  1  1
          1  0  1  1
        + 0  1  1  0
        + 0  0  1  1
        -----------
        1  0  1  0  0
```

**`base_multiply("1011", "110", 2)`**
```
        1  0  1  1
      ×    1  1  0
      -----------
        0  0  0  0      (× 0, shift 0)
     1  0  1  1         (× 1, shift 1)
  1  0  1  1            (× 1, shift 2)
  -------------------
  1  0  0  0  0  1  0
```

**`base_add(["1A", "-0B"], 16)`**
```
Operandos de sinais opostos — soma realizada via conversão decimal intermediária.
1A + (-0B) = F (hexadecimal)
```
