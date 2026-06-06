# AI Agent — Ferramentas

Todas as ferramentas são implementadas em `chat/tools.py` como funções LangChain decoradas com `@tool`. O agente decide autonomamente quando chamá-las com base nos gatilhos descritos no system prompt.

## Tabela de ferramentas

| Ferramenta | Gatilhos principais | Descrição |
|---|---|---|
| `assembler` | "monte", "converta para binário/hex", "código de máquina de" | Converte instruções RISC-V para código de máquina (binário ou hex) |
| `disassembler` | "desmonte", "o que faz este binário/hex", "qual instrução" | Converte código de máquina RISC-V de volta para assembly |
| `base_converter` | "converta", "expresse em binário/hex/decimal", "complemento de dois" | Converte números entre bases (2–36), com suporte a complemento de dois |
| `float_to_ieee754` | "IEEE 754 de", "represente em ponto flutuante", "como fica X em 32 bits" | Converte float para representação binária IEEE 754 de 32 bits |
| `ieee754_to_float` | "o que representa este padrão de bits", "converta IEEE 754 para decimal" | Converte representação IEEE 754 (binário ou hex) para float |
| `imme_calc` | "imediato do branch", "offset de jal", "como fica o campo imm" | Calcula codificação de imediatos para formatos B (branch) e J (jal) |
| `base_add` | "some", "adição em base", "quanto é X + Y em binário/octal/hex" | Soma N números em qualquer base, exibindo carries coluna a coluna |
| `base_multiply` | "multiplique", "multiplicação em base", "produto de" | Multiplica dois números em qualquer base, exibindo produtos parciais |
| `search_knowledge` | "o professor falou", "nas aulas", "nos vídeos", conteúdo de aula | Busca trechos relevantes nas transcrições da disciplina via embeddings |

## Detalhes por ferramenta

### `assembler`

```python
assembler(instructions: str, output_base: int = 2) -> str
```

Aceita uma ou mais instruções separadas por `\n`. Suporta instruções R, I, S, B, U, J e pseudoinstruções (`ret`, `j`, `li`).

### `disassembler`

```python
disassembler(machine_code: str, input_base: int = 2) -> str
```

Aceita binário (32 bits) ou hexadecimal (8 dígitos) por linha.

### `base_converter`

```python
base_converter(
    number: str,
    from_base: int,
    to_base: int,
    signed_input: bool = False,
    signed_output: bool = False,
    precision: int = 10,
) -> str
```

`signed_input=True` interpreta entrada como complemento. `signed_output=True` + `precision=N` gera complemento de dois com N bits.

### `float_to_ieee754` / `ieee754_to_float`

Usa `struct.pack/unpack` para a conversão exata. Retorna a decomposição em sinal, expoente e mantissa com explicação dos valores.

### `imme_calc`

```python
imme_calc(value: str, format_type: str, input_type: str = "byte", base: int = 10) -> str
```

`format_type`: `"B"` para branch (beq, bne, blt, bge, bltu, bgeu) ou `"J"` para jal.
`input_type`: `"byte"` (offset em bytes) ou `"operacoes"` (número de instruções × 4).

### `base_add` / `base_multiply`

Pré-condição: todos os operandos devem estar na mesma base. Se necessário, converter antes com `base_converter`. Exibem o passo a passo com carries (add) ou produtos parciais (multiply).

### `search_knowledge`

Veja [../fluxos-de-dados/knowledge-retrieval.md](../fluxos-de-dados/knowledge-retrieval.md) para o fluxo completo.
