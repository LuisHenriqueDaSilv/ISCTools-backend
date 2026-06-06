import struct

from langchain_core.tools import tool
from sqlalchemy.orm import Session

from src.knowledge import service as knowledge_service

_SIMBOLOS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

_INSTRUCTION_SET: dict[str, dict] = {
    "add":    {"opcode": "0110011", "funct3": "000", "funct7": "0000000"},
    "sub":    {"opcode": "0110011", "funct3": "000", "funct7": "0100000"},
    "addi":   {"opcode": "0010011", "funct3": "000"},
    "slli":   {"opcode": "0010011", "funct3": "001"},
    "slti":   {"opcode": "0010011", "funct3": "010"},
    "sltiu":  {"opcode": "0010011", "funct3": "011"},
    "xori":   {"opcode": "0010011", "funct3": "100"},
    "srli":   {"opcode": "0010011", "funct3": "101", "funct7": "0000000"},
    "srai":   {"opcode": "0010011", "funct3": "101", "funct7": "0100000"},
    "ori":    {"opcode": "0010011", "funct3": "110"},
    "andi":   {"opcode": "0010011", "funct3": "111"},
    "lb":     {"opcode": "0000011", "funct3": "000"},
    "lh":     {"opcode": "0000011", "funct3": "001"},
    "lw":     {"opcode": "0000011", "funct3": "010"},
    "lbu":    {"opcode": "0000011", "funct3": "100"},
    "lhu":    {"opcode": "0000011", "funct3": "101"},
    "auipc":  {"opcode": "0010111"},
    "sb":     {"opcode": "0100011", "funct3": "000"},
    "sh":     {"opcode": "0100011", "funct3": "001"},
    "sw":     {"opcode": "0100011", "funct3": "010"},
    "mul":    {"opcode": "0110011", "funct3": "000", "funct7": "0000001"},
    "mulh":   {"opcode": "0110011", "funct3": "001", "funct7": "0000001"},
    "mulhsu": {"opcode": "0110011", "funct3": "010", "funct7": "0000001"},
    "mulhu":  {"opcode": "0110011", "funct3": "011", "funct7": "0000001"},
    "div":    {"opcode": "0110011", "funct3": "100", "funct7": "0000001"},
    "divu":   {"opcode": "0110011", "funct3": "101", "funct7": "0000001"},
    "rem":    {"opcode": "0110011", "funct3": "110", "funct7": "0000001"},
    "srl":    {"opcode": "0110011", "funct3": "101", "funct7": "0000000"},
    "sra":    {"opcode": "0110011", "funct3": "101", "funct7": "0100000"},
    "sll":    {"opcode": "0110011", "funct3": "001", "funct7": "0000000"},
    "slt":    {"opcode": "0110011", "funct3": "010", "funct7": "0000000"},
    "sltu":   {"opcode": "0110011", "funct3": "011", "funct7": "0000000"},
    "xor":    {"opcode": "0110011", "funct3": "100", "funct7": "0000000"},
    "or":     {"opcode": "0110011", "funct3": "110", "funct7": "0000000"},
    "and":    {"opcode": "0110011", "funct3": "111", "funct7": "0000000"},
    "lui":    {"opcode": "0110111"},
    "beq":    {"opcode": "1100011", "funct3": "000"},
    "bne":    {"opcode": "1100011", "funct3": "001"},
    "blt":    {"opcode": "1100011", "funct3": "100"},
    "bge":    {"opcode": "1100011", "funct3": "101"},
    "bltu":   {"opcode": "1100011", "funct3": "110"},
    "bgeu":   {"opcode": "1100011", "funct3": "111"},
    "jalr":   {"opcode": "1100111", "funct3": "000"},
    "jal":    {"opcode": "1101111"},
    "ecall":  {"opcode": "1110011", "funct3": "000"},
    "uret":   {"opcode": "1110011", "funct3": "000"},
    "ret":    {},
    "j":      {"opcode": "1101111"},
    "li":     {"opcode": "0010011", "funct3": "000"},
}

_REGISTER_MAP: dict[str, str] = {
    "x0": "00000", "zero": "00000",
    "x1": "00001", "ra": "00001",
    "x2": "00010", "sp": "00010",
    "x3": "00011", "gp": "00011",
    "x4": "00100", "tp": "00100",
    "x5": "00101", "t0": "00101",
    "x6": "00110", "t1": "00110",
    "x7": "00111", "t2": "00111",
    "x8": "01000", "s0": "01000",
    "x9": "01001", "s1": "01001",
    "x10": "01010", "a0": "01010",
    "x11": "01011", "a1": "01011",
    "x12": "01100", "a2": "01100",
    "x13": "01101", "a3": "01101",
    "x14": "01110", "a4": "01110",
    "x15": "01111", "a5": "01111",
    "x16": "10000", "a6": "10000",
    "x17": "10001", "a7": "10001",
    "x18": "10010", "s2": "10010",
    "x19": "10011", "s3": "10011",
    "x20": "10100", "s4": "10100",
    "x21": "10101", "s5": "10101",
    "x22": "10110", "s6": "10110",
    "x23": "10111", "s7": "10111",
    "x24": "11000", "s8": "11000",
    "x25": "11001", "s9": "11001",
    "x26": "11010", "s10": "11010",
    "x27": "11011", "s11": "11011",
    "x28": "11100", "t3": "11100",
    "x29": "11101", "t4": "11101",
    "x30": "11110", "t5": "11110",
    "x31": "11111", "t6": "11111",
}

_REGISTER_NAMES = [
    "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
    "s0", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
    "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
    "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6",
]

_OPCODE_MAP: dict = {
    "0000011": {"000": "lb", "001": "lh", "010": "lw", "100": "lbu", "101": "lhu"},
    "0010011": {
        "000": "addi", "001": "slli", "010": "slti", "011": "sltiu",
        "100": "xori", "101": {"0000000": "srli", "0100000": "srai"},
        "110": "ori", "111": "andi",
    },
    "0010111": {"auipc": "auipc"},
    "0100011": {"000": "sb", "001": "sh", "010": "sw"},
    "0110011": {
        "000": {"0000000": "add", "0100000": "sub"},
        "101": {"0000000": "srl", "0100000": "sra"},
        "0000001": {"000": "mul", "001": "mulh", "010": "mulhsu", "011": "mulhu",
                    "100": "div", "101": "divu", "110": "rem", "111": "remu"},
        "001": "sll", "010": "slt", "011": "sltu",
        "100": "xor", "110": "or", "111": "and",
    },
    "0110111": {"lui": "lui"},
    "1100011": {"000": "beq", "001": "bne", "100": "blt", "101": "bge", "110": "bltu", "111": "bgeu"},
    "1100111": {"000": "jalr"},
    "1101111": {"jal": "jal"},
    "1110011": {},
}


# ---------------------------------------------------------------------------
# Helpers for base conversion
# ---------------------------------------------------------------------------

def _int_to_base(val: int, base: int) -> str:
    if val == 0:
        return "0"
    result = ""
    while val > 0:
        result = _SIMBOLOS[val % base] + result
        val //= base
    return result


def _complement_to_signed(num: str, base: int) -> int:
    n = len(num)
    max_val = base ** n
    val = int(num, base)
    if num[0] == _SIMBOLOS[base - 1] and val >= max_val // 2:
        val -= max_val
    return val


def _to_complement(num_str: str, base: int, n_digits: int) -> str:
    is_negative = num_str.startswith("-")
    num_abs = num_str[1:] if is_negative else num_str
    # num_str is already in base `base` (sign-magnitude)
    val = int(num_abs, base) if num_abs not in ("", "0") else 0
    if not is_negative:
        return _int_to_base(val, base).zfill(n_digits).upper()
    complement = (base ** n_digits) - val
    return _int_to_base(complement, base).zfill(n_digits).upper()


def _converter_base(
    num: str,
    base_origin: int,
    base_dest: int,
    complement_origin: bool = False,
    result_complement: bool = False,
    precision: int = 10,
) -> str:
    num = num.upper().strip()
    domain = set(_SIMBOLOS[:base_origin])
    for char in num:
        if char != "-" and char not in domain:
            raise ValueError(f"Caractere inválido '{char}' para base {base_origin}.")

    if complement_origin:
        val = _complement_to_signed(num, base_origin)
    else:
        if num.startswith("-"):
            val = -int(num[1:], base_origin)
        else:
            val = int(num, base_origin)

    negative = val < 0
    abs_val = abs(val)
    converted = _int_to_base(abs_val, base_dest) if abs_val > 0 else "0"
    if negative:
        converted = "-" + converted

    if result_complement:
        return _to_complement(converted, base_dest, precision)
    return converted


# ---------------------------------------------------------------------------
# Helpers for assembler
# ---------------------------------------------------------------------------

def _assemble_one(instruction: str) -> str:
    parts = instruction.lower().replace(",", " ").replace("(", " ").replace(")", "").split()
    instr = parts[0]
    args = parts[1:]
    details = _INSTRUCTION_SET.get(instr)
    if details is None:
        return f"Instrução desconhecida: {instr}"

    def reg(name: str) -> str:
        r = _REGISTER_MAP.get(name)
        if r is None:
            raise ValueError(f"Registrador inválido: {name}")
        return r

    def imm(val: str, bits: int) -> str:
        return _converter_base(val, 10, 2, False, True, bits)

    match instr:
        case "add" | "sub" | "mul" | "mulh" | "mulhsu" | "mulhu" | "div" | "divu" | "rem" | \
             "srl" | "sra" | "sll" | "slt" | "sltu" | "xor" | "or" | "and":
            return details["funct7"] + reg(args[2]) + reg(args[1]) + details["funct3"] + reg(args[0]) + details["opcode"]

        case "addi" | "slli" | "slti" | "sltiu" | "ori" | "andi" | "xori":
            return imm(args[2], 12) + reg(args[1]) + details["funct3"] + reg(args[0]) + details["opcode"]

        case "srli" | "srai":
            return details["funct7"] + imm(args[2], 5) + reg(args[1]) + details["funct3"] + reg(args[0]) + details["opcode"]

        case "lb" | "lh" | "lw" | "lbu" | "lhu":
            imme = imm(args[1], 12)
            return imme + reg(args[2]) + details["funct3"] + reg(args[0]) + details["opcode"]

        case "auipc":
            return imm(args[1], 20) + reg(args[0]) + details["opcode"]

        case "sb" | "sh" | "sw":
            imme = imm(args[1], 12)
            return imme[:7] + reg(args[0]) + reg(args[2]) + details["funct3"] + imme[7:12] + details["opcode"]

        case "lui":
            return imm(args[1], 20) + reg(args[0]) + details["opcode"]

        case "beq" | "bne" | "blt" | "bge" | "bltu" | "bgeu":
            imme = _imme_calc_raw(args[2], "B", "byte", 10)
            return imme[:7] + reg(args[1]) + reg(args[0]) + details["funct3"] + imme[20:25] + details["opcode"]

        case "jalr":
            return imm(args[2], 12) + reg(args[1]) + details["funct3"] + reg(args[0]) + details["opcode"]

        case "jal":
            imme = _imme_calc_raw(args[1], "J", "byte", 10)
            return imme + reg(args[0]) + details["opcode"]

        case "ecall":
            return "00000000000000000000000001110011"
        case "uret":
            return "00000000001000000000000001110011"
        case "ret":
            return "00000000000000001000000001100111"

        case "j":
            imme = _imme_calc_raw(args[0], "J", "byte", 10)
            return imme + "00000" + details["opcode"]

        case "li":
            return imm(args[1], 12) + "00000" + details["funct3"] + reg(args[0]) + details["opcode"]

        case _:
            return f"Formato não implementado: {instr}"


# ---------------------------------------------------------------------------
# Helper for immeCalc (raw bit string, used internally by assembler)
# ---------------------------------------------------------------------------

def _imme_calc_raw(value: str, fmt: str, input_type: str, base: int) -> str:
    new_num = int(value)
    if input_type == "operacoes":
        new_num *= 4
    bin_str = _converter_base(str(new_num), base, 2, False, True, 32)
    if fmt == "J":
        return bin_str[0] + bin_str[21:31] + bin_str[20] + bin_str[12:20]
    elif fmt == "B":
        return (
            bin_str[0]
            + bin_str[21:27]
            + "xxxxxxxxxxxxx"
            + bin_str[27:31]
            + bin_str[20]
            + "xxxxxxx"
        )
    return "FMTS desconhecido"


# ---------------------------------------------------------------------------
# Helper for disassembler
# ---------------------------------------------------------------------------

def _disassemble_one(binary: str) -> str:
    if len(binary) != 32:
        raise ValueError(f"Instrução deve ter 32 bits, recebeu {len(binary)}")

    opcode = binary[25:32]
    rd = int(binary[20:25], 2)
    funct3 = binary[17:20]
    rs1 = int(binary[12:17], 2)
    rs2 = int(binary[7:12], 2)
    funct7 = binary[0:7]
    omap = _OPCODE_MAP

    match opcode:
        case "0000011":
            imme = binary[0:12]
            name = omap[opcode][funct3]
            return f"{name} {_REGISTER_NAMES[rd]}, {int(imme, 2)}({_REGISTER_NAMES[rs1]})"

        case "0010011":
            if funct3 == "101":
                imme = binary[7:12]
                name = omap[opcode][funct3][funct7]
                return f"{name} {_REGISTER_NAMES[rd]}, {_REGISTER_NAMES[rs1]}, {_converter_base(imme, 2, 10, True, False)}"
            else:
                imme = binary[0:12]
                name = omap[opcode][funct3]
                return f"{name} {_REGISTER_NAMES[rd]}, {_REGISTER_NAMES[rs1]}, {_converter_base(imme, 2, 10, True, False)}"

        case "0010111":
            imme = binary[0:20]
            return f"auipc {_REGISTER_NAMES[rd]}, {_converter_base(imme, 2, 10, True, False)}"

        case "0100011":
            imme1 = binary[0:7]
            imme2 = binary[20:25]
            name = omap[opcode][funct3]
            return f"{name} {_REGISTER_NAMES[rs2]}, {int(imme1 + imme2, 2)}({_REGISTER_NAMES[rs1]})"

        case "0110011":
            if funct7 == "0000001":
                name = omap[opcode][funct7][funct3]
                return f"{name} {_REGISTER_NAMES[rd]}, {_REGISTER_NAMES[rs1]}, {_REGISTER_NAMES[rs2]}"
            elif funct3 in ("000", "101"):
                name = omap[opcode][funct3][funct7]
                return f"{name} {_REGISTER_NAMES[rd]}, {_REGISTER_NAMES[rs1]}, {_REGISTER_NAMES[rs2]}"
            else:
                name = omap[opcode][funct3]
                return f"{name} {_REGISTER_NAMES[rd]}, {_REGISTER_NAMES[rs1]}, {_REGISTER_NAMES[rs2]}"

        case "0110111":
            imme = binary[0:20]
            return f"lui {_REGISTER_NAMES[rd]}, 0x{_converter_base(imme, 2, 16, False, False)}"

        case "1100011":
            sign = binary[0]
            imme = (binary[24] + binary[1:7] + binary[20:24] + "0").zfill(32) if sign == "0" else \
                   (binary[24] + binary[1:7] + binary[20:24] + "0").rjust(32, sign)
            name = omap[opcode][funct3]
            return f"{name} {_REGISTER_NAMES[rs1]}, {_REGISTER_NAMES[rs2]}, {_converter_base(imme, 2, 10, True, False)}"

        case "1100111":
            imme = binary[0:12]
            return f"jalr {_REGISTER_NAMES[rd]}, {_REGISTER_NAMES[rs1]}, {_converter_base(imme, 2, 10, True, False)}"

        case "1101111":
            sign = binary[0]
            raw = binary[12:20] + binary[11] + binary[1:11] + "0"
            imme = raw.zfill(32) if sign == "0" else raw.rjust(32, sign)
            return f"jal {_REGISTER_NAMES[rd]}, {int(_converter_base(imme, 2, 10, True, False))}"

        case "1110011":
            rs2b = binary[7:12]
            return "uret" if rs2b == "00010" else "ecall"

        case _:
            raise ValueError(f"Opcode desconhecido: {opcode}")


# ---------------------------------------------------------------------------
# LangChain tools (public interface for the agent)
# ---------------------------------------------------------------------------

@tool
def assembler(instructions: str, output_base: int = 2) -> str:
    """Converte instruções assembly RISC-V para código de máquina.

    Args:
        instructions: Uma ou mais instruções RISC-V, separadas por quebra de linha.
        output_base: Base de saída (2 = binário, 16 = hexadecimal).
    """
    results = []
    for line in instructions.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            binary = _assemble_one(line)
            if output_base == 16:
                hex_val = _converter_base(binary, 2, 16, False, True, 8)
                results.append(f"{line}  →  0x{hex_val}")
            else:
                results.append(f"{line}  →  {binary}")
        except Exception as e:
            results.append(f"{line}  →  Erro: {e}")
    return "\n".join(results)


@tool
def disassembler(machine_code: str, input_base: int = 2) -> str:
    """Converte código de máquina RISC-V de volta para assembly.

    Args:
        machine_code: Código de máquina, uma instrução por linha (binário ou hex).
        input_base: Base da entrada (2 = binário, 16 = hexadecimal).
    """
    results = []
    for line in machine_code.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            clean = line.replace("0x", "").replace("0b", "").upper()
            binary = _converter_base(clean, input_base, 2, False, True, 32)
            results.append(f"{line}  →  {_disassemble_one(binary)}")
        except Exception as e:
            results.append(f"{line}  →  Erro: {e}")
    return "\n".join(results)


@tool
def base_converter(
    number: str,
    from_base: int,
    to_base: int,
    signed_input: bool = False,
    signed_output: bool = False,
    precision: int = 10,
) -> str:
    """Converte um número de uma base numérica para outra.

    Args:
        number: Número a converter (como string, ex: '1010', 'FF', '-42').
        from_base: Base de origem (2 a 36).
        to_base: Base de destino (2 a 36).
        signed_input: Se True, interpreta a entrada como complemento (ex: '11110000' em base 2 = valor negativo).
        signed_output: Se True, gera saída em representação de complemento com largura definida por precision.
        precision: Número de dígitos no resultado quando signed_output=True.
    """
    result = _converter_base(number, from_base, to_base, signed_input, signed_output, precision)
    label = {2: "binário", 8: "octal", 10: "decimal", 16: "hexadecimal"}.get(to_base, f"base {to_base}")
    return f"{number} (base {from_base}) = {result} ({label})"


@tool
def float_to_ieee754(number: float) -> str:
    """Converte um número de ponto flutuante para representação binária IEEE 754 de precisão simples (32 bits).

    Args:
        number: Número float a converter.
    """
    packed = struct.pack(">f", number)
    int_repr = struct.unpack(">I", packed)[0]
    binary = format(int_repr, "032b")
    sign = binary[0]
    exponent = binary[1:9]
    mantissa = binary[9:]
    exp_val = int(exponent, 2) - 127
    return (
        f"IEEE 754 de {number}:\n"
        f"  Binário: {binary}\n"
        f"  Sinal:    bit[31] = {sign} ({'negativo' if sign == '1' else 'positivo'})\n"
        f"  Expoente: bits[30:23] = {exponent} = {int(exponent, 2)} (valor = {int(exponent, 2)} - 127 = {exp_val})\n"
        f"  Mantissa: bits[22:0] = {mantissa}"
    )


@tool
def ieee754_to_float(binary_str: str, input_base: int = 2) -> str:
    """Converte uma representação IEEE 754 (binário ou hex) para número de ponto flutuante.

    Args:
        binary_str: Representação IEEE 754 (32 bits em binário ou 8 dígitos em hex).
        input_base: Base da entrada (2 = binário, 16 = hexadecimal).
    """
    clean = binary_str.strip().replace("0x", "").replace("0b", "").upper()
    if input_base == 16:
        int_val = int(clean, 16)
    else:
        int_val = int(clean.zfill(32), 2)

    packed = struct.pack(">I", int_val)
    value = struct.unpack(">f", packed)[0]
    binary = format(int_val, "032b")
    return (
        f"IEEE 754 '{binary_str}' = {value}\n"
        f"  Binário: {binary}\n"
        f"  Sinal:    {binary[0]} ({'negativo' if binary[0] == '1' else 'positivo'})\n"
        f"  Expoente: {binary[1:9]} = {int(binary[1:9], 2)} (valor = {int(binary[1:9], 2) - 127})\n"
        f"  Mantissa: {binary[9:]}"
    )


@tool
def imme_calc(value: str, format_type: str, input_type: str = "byte", base: int = 10) -> str:
    """Calcula a codificação de imediatos para os formatos B (branch) e J (jal) do RISC-V.

    Args:
        value: Valor do imediato (como string).
        format_type: 'B' para instruções de branch (beq, bne, etc.) ou 'J' para jal.
        input_type: 'byte' para offset em bytes (padrão), 'operacoes' para número de instruções.
        base: Base numérica do valor de entrada (padrão 10 = decimal).
    """
    new_num = int(value)
    if input_type == "operacoes":
        new_num *= 4

    bin_str = _converter_base(str(new_num), base, 2, False, True, 32)

    if format_type == "B":
        imm_12 = bin_str[0]
        imm_11 = bin_str[20]
        imm_10_5 = bin_str[21:27]
        imm_4_1 = bin_str[27:31]
        return (
            f"Imediato {value} (= {new_num} bytes) no formato B:\n"
            f"  imm[12]   = {imm_12}  → bit 31 da instrução\n"
            f"  imm[10:5] = {imm_10_5} → bits 30:25 da instrução\n"
            f"  imm[4:1]  = {imm_4_1}   → bits 11:8 da instrução\n"
            f"  imm[11]   = {imm_11}  → bit 7 da instrução\n"
            f"\nEstrutura [31..0]: {imm_12} {imm_10_5} [rs2(5)] [rs1(5)] [f3(3)] {imm_4_1} {imm_11} [opcode(7)]"
        )
    elif format_type == "J":
        imm_20 = bin_str[0]
        imm_10_1 = bin_str[21:31]
        imm_11 = bin_str[20]
        imm_19_12 = bin_str[12:20]
        return (
            f"Imediato {value} (= {new_num} bytes) no formato J:\n"
            f"  imm[20]    = {imm_20}          → bit 31 da instrução\n"
            f"  imm[10:1]  = {imm_10_1}  → bits 30:21 da instrução\n"
            f"  imm[11]    = {imm_11}          → bit 20 da instrução\n"
            f"  imm[19:12] = {imm_19_12} → bits 19:12 da instrução\n"
            f"\nEstrutura [31..0]: {imm_20} {imm_10_1} {imm_11} {imm_19_12} [rd(5)] [opcode(7)]"
        )
    else:
        return f"Formato desconhecido: '{format_type}'. Use 'B' ou 'J'."


def _validate_base(base: int) -> str | None:
    if not (2 <= base <= 36):
        return "Base inválida: deve estar entre 2 e 36."
    return None


def _validate_digits(num: str, base: int) -> str | None:
    domain = set(_SIMBOLOS[:base])
    for ch in num:
        if ch not in domain:
            return f"Caractere inválido '{ch}' para base {base}."
    return None


def _parse_signed(num: str) -> tuple[int, str]:
    if num.startswith("-"):
        return -1, num[1:]
    return 1, num


def _sum_magnitudes(mags: list[str], base: int) -> tuple[list[int], list[int]]:
    """Return (result_digits, carry_digits) for column-by-column sum."""
    width = max(len(m) for m in mags)
    padded = [m.zfill(width) for m in mags]
    result = []
    carries = []
    carry = 0
    for col in range(width - 1, -1, -1):
        total = carry + sum(_SIMBOLOS.index(p[col]) for p in padded)
        result.append(total % base)
        carry = total // base
        carries.append(carry)
    if carry > 0:
        result.append(carry)
        carries.append(0)
    result.reverse()
    carries.reverse()
    return result, carries


def _digits_to_str(digits: list[int]) -> str:
    return "".join(_SIMBOLOS[d] for d in digits)


def _add_magnitudes_raw(a: str, b: str, base: int) -> str:
    result_digits, _ = _sum_magnitudes([a, b], base)
    return _digits_to_str(result_digits)


def _multiply_mag_by_digit(mag: str, digit_val: int, base: int) -> str:
    result = []
    carry = 0
    for ch in reversed(mag):
        prod = _SIMBOLOS.index(ch) * digit_val + carry
        result.append(prod % base)
        carry = prod // base
    while carry > 0:
        result.append(carry % base)
        carry //= base
    result.reverse()
    return _digits_to_str(result) if result else "0"


@tool
def base_add(operands: list[str], base: int) -> str:
    """Soma N números em uma base qualquer, exibindo o passo a passo com linha de carry.

    Args:
        operands: Lista de números a somar, como strings na base indicada.
                  Use prefixo '-' para negativos (ex: '-1011').
        base: Base numérica comum a todos os operandos (2 a 36).
    """
    err = _validate_base(base)
    if err:
        return err
    if len(operands) < 2:
        return "Informe ao menos dois operandos."

    parsed = []
    for op in operands:
        op = op.upper().strip()
        sign, mag = _parse_signed(op)
        verr = _validate_digits(mag, base)
        if verr:
            return verr
        parsed.append((sign, mag))

    signs = [s for s, _ in parsed]

    if len(set(signs)) > 1:
        total = sum(sign * int(mag, base) for sign, mag in parsed)
        result_sign = "-" if total < 0 else ""
        result_str = _int_to_base(abs(total), base) if total != 0 else "0"
        label = {2: "binário", 8: "octal", 10: "decimal", 16: "hexadecimal"}.get(base, f"base {base}")
        expr = " + ".join((f"(-{mag})" if s == -1 else mag) for s, mag in parsed)
        return (
            "Operandos de sinais opostos — soma realizada via conversão decimal intermediária.\n"
            f"{expr} = {result_sign}{result_str} ({label})"
        )

    common_sign = signs[0]
    mags = [mag for _, mag in parsed]
    result_digits, carries = _sum_magnitudes(mags, base)
    result_str = _digits_to_str(result_digits)

    # --- format grid ---
    cell = max(2, len(_SIMBOLOS[base - 1]) + 1)
    op_width = max(len(m) for m in mags)
    padded = [m.zfill(op_width) for m in mags]
    has_extra = len(result_str) > op_width
    extra_area = (len(result_str) - op_width) * cell if has_extra else 0

    def fmt_digits(s: str, width: int) -> str:
        return "".join(c.rjust(cell) for c in s.zfill(width))

    # All number rows are right-aligned: rightmost digit at same column.
    # Operator column (1 char: " " or "+") sits immediately left of digits.
    # Operand rows: operator + extra_area_spaces + op_width digits
    # Result row:   sign_char + result_len digits  (auto-right-aligned)
    op_digits_part = lambda m: " " * extra_area + fmt_digits(m, op_width)
    num_row_width = 1 + extra_area + op_width * cell  # same as 1 + len(result)

    # carries[1:] = carry-outs for op_width cols (when has_extra, carries[0]=0 is padding)
    carry_display = carries[1:] if has_extra else carries
    all_zero = all(c == 0 for c in carry_display)

    lines = []
    if not all_zero:
        # carry values right-align over op columns; "  Carry:" is a left label
        carry_vals = "".join(str(c).rjust(cell) for c in carry_display)
        # pad so carry values align with op digit columns
        carry_line = "  Carry:" + " " * (num_row_width - 8 - len(carry_vals) + extra_area) + carry_vals
        lines.append(carry_line)

    lines.append(" " + op_digits_part(padded[0]))
    for mag in padded[1:]:
        lines.append("+" + op_digits_part(mag))

    lines.append("-" * num_row_width)

    result_sign = "-" if common_sign == -1 else " "
    lines.append(result_sign + fmt_digits(result_str, len(result_str)))

    return "\n".join(lines)


@tool
def base_multiply(a: str, b: str, base: int) -> str:
    """Multiplica dois números em uma base qualquer, exibindo produtos parciais.

    Args:
        a: Primeiro operando como string na base indicada. Use '-' para negativo.
        b: Segundo operando como string na base indicada. Use '-' para negativo.
        base: Base numérica dos operandos (2 a 36).
    """
    err = _validate_base(base)
    if err:
        return err

    a = a.upper().strip()
    b = b.upper().strip()
    sign_a, mag_a = _parse_signed(a)
    sign_b, mag_b = _parse_signed(b)

    verr = _validate_digits(mag_a, base)
    if verr:
        return verr
    verr = _validate_digits(mag_b, base)
    if verr:
        return verr

    result_sign = -1 if sign_a != sign_b else 1
    cell = max(2, len(_SIMBOLOS[base - 1]) + 1)

    partials = []
    for i, ch in enumerate(reversed(mag_b)):
        digit_val = _SIMBOLOS.index(ch)
        prod = _multiply_mag_by_digit(mag_a, digit_val, base)
        partials.append((prod, digit_val, i))

    total = 0
    for prod_str, _, shift in partials:
        total += int(prod_str, base) * (base ** shift)
    result_str = _int_to_base(total, base) if total != 0 else "0"

    # total_width covers partial products and result; op_width covers the header
    total_width = max(len(result_str), max(len(p) + s for p, _, s in partials))
    op_width = max(len(mag_a), len(mag_b))

    def fmt_op(s: str) -> str:
        return "".join(c.rjust(cell) for c in s.zfill(op_width))

    def fmt_full(s: str) -> str:
        return "".join(c.rjust(cell) for c in s.zfill(total_width))

    # headers are right-aligned within total_width display
    h_indent = " " * ((total_width - op_width) * cell)
    lines = []
    lines.append(h_indent + " " + fmt_op(mag_a))
    lines.append(h_indent + "×" + fmt_op(mag_b))
    lines.append(h_indent + " " + "-" * (op_width * cell + 1))

    for prod_str, digit_val, shift in partials:
        left_pad = total_width - len(prod_str) - shift
        row = (" " * left_pad * cell
               + "".join(c.rjust(cell) for c in prod_str)
               + " " * shift * cell)
        comment = f"  (× {_SIMBOLOS[digit_val]}, shift {shift})"
        lines.append(" " + row + comment)

    lines.append(" " + "-" * (total_width * cell + 3))
    prefix = "-" if result_sign == -1 else " "
    lines.append(prefix + fmt_full(result_str))

    return "\n".join(lines)


def make_search_knowledge(db: Session, api_key: str):
    @tool
    def search_knowledge(
        query: str,
        source_type: str | None = None,
        video_source: str | None = None,
    ) -> str:
        """Busca trechos relevantes nos materiais da disciplina (aulas OAC e vídeos ISC).
        Use sempre que o estudante referenciar conteúdo de aula, pedir exemplos do professor
        ou mencionar "o professor falou", "nas aulas", "nos vídeos". Prefira sempre buscar
        antes de responder com conhecimento próprio sobre os materiais do curso.

        Args:
            query: Pergunta ou termo de busca em linguagem natural.
            source_type: Filtro opcional — "aulas_oac" ou "youtube_isc".
            video_source: Filtro opcional — nome do arquivo de vídeo (ex: "OAC_2022-01-17.mp4").
        """
        results = knowledge_service.search(db, query, api_key, source_type=source_type, video_source=video_source)
        if not results:
            return "Nenhum trecho relevante encontrado nos materiais da disciplina."
        parts = []
        for i, r in enumerate(results, 1):
            parts.append(
                f"[{i}] {r['video_source']} ({r['source_type']}) "
                f"[{r['timestamp_start']:.1f}s – {r['timestamp_end']:.1f}s]\n{r['content']}"
            )
        return "\n\n---\n\n".join(parts)

    return search_knowledge


def get_tools(db: Session, api_key: str) -> list:
    return [
        assembler,
        disassembler,
        base_converter,
        float_to_ieee754,
        ieee754_to_float,
        imme_calc,
        base_add,
        base_multiply,
        make_search_knowledge(db, api_key),
    ]
