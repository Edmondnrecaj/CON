from asmlib import Assembler, Lexing, Parsing, Simulation

import argparse
from typing import Dict, List, Optional, Tuple

TT_COMMA = 'Comma'
TT_COMMENT = 'Comment'
TT_INTEGER = 'Integer'
TT_NEWLINE = 'Newline'
TT_REGISTER = 'Register'
TT_WORD = 'Word'

TT_MNEMONIC = Parsing.TokenTypeAlias('Mnemonic', [TT_WORD])
TT_LABEL = Parsing.TokenTypeAlias('Label', [TT_WORD, TT_REGISTER])


class IsaSupportExtension:
    @staticmethod
    def setup_assembler_arguments(parser: argparse.ArgumentParser):
        # setup mutually exclusive selection of TOY ISA variants
        modes = parser.add_argument_group(
            'ISA Modes',
            'Select the used ISA variant. (default: -t)').add_mutually_exclusive_group()
        parser.set_defaults(mode='-t')
        for mode, help in ISA_DESCRIPTIONS.items():
            modes.add_argument(mode, dest='mode', action='store_const', const=mode, help=help)

    @staticmethod
    def update_assembler_isa(isa: List[Assembler.InstDescription], args: argparse.Namespace):
        isa += instructions(args.mode)

    setup_simulator_arguments = setup_assembler_arguments
    update_simulator_isa = update_assembler_isa


################################################################################
#
# Assembler directives:
#
# ORG ... define the "origin", i.e. start address of the following instruction
#
#   example:
#     ORG 0x10    ; put the following instruction at address 0x10
#
#
# DW  ... define the contents of one or several words in main memory
#
#   examples:
#
#     A DW 5      ; symbolic address A with value 5
#     B DW 0xC    ; symbolic address B with hex-value C
#     D DW 7 8 9  ; define the contents of 3 memory locations starting with
#                 ; symbolic address D
#
# DUP ... reserve memory locations
#
#   example:
#
#     D DUP 5     ; reserve 5 memory locations beginning at symbolic address D
#                 ; the values are not defined
#
################################################################################


class OrgDescription(Assembler.InstDescription):
    def __init__(self):
        super().__init__("ORG", [Parsing.Match(TT_INTEGER, name='addr')])

    def construct(self, addr: int, mnemonic: Lexing.Token, arguments: Dict[str, Lexing.Token],
                  asm_ctx: Assembler.Context) -> Tuple[int, Optional[Assembler.Instruction]]:
        next_addr = asm_ctx.resolve_integer(arguments['addr'], addr, 255)
        asm_ctx._auto_org = False
        return (next_addr, None)


class DupDescription(Assembler.InstDescription):
    def __init__(self):
        super().__init__("DUP", [Parsing.Match(TT_INTEGER, name='size')])

    def construct(self, addr: int, mnemonic: Lexing.Token, arguments: Dict[str, Lexing.Token],
                  asm_ctx: Assembler.Context) -> Tuple[int, Optional[Assembler.Instruction]]:
        inst = Assembler.Instruction(self, addr, mnemonic, arguments)
        inst.size = asm_ctx.resolve_integer(arguments['size'], 1, 256 - addr)
        return (addr + inst.size, inst)

    def size(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> int:
        return inst.size

    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        return [0] * inst.size


class DwDescription(Assembler.InstDescription):
    def __init__(self, arg_seperator_parser: Optional[Parsing.Parser] = None):
        element_parser = Parsing.Match(TT_INTEGER, name='values')
        # FIXME this does only work for the toy relaxed case.
        if arg_seperator_parser is not None:
            element_parser += arg_seperator_parser
        super().__init__("DW", [Parsing.RepetitionParser(element_parser, min_rep=1)])

    def construct(self, addr: int, mnemonic: Lexing.Token,
                  arguments: Dict[str, List[Lexing.Token]],
                  asm_ctx: Assembler.Context) -> Tuple[int, Optional[Assembler.Instruction]]:
        inst = Assembler.Instruction(self, addr, mnemonic, arguments)
        inst.size = len(arguments['values'])
        # TODO add check for number similar to asm_ctx.resolve_integer(, 1, 256-addr)
        return (addr + inst.size, inst)

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.values = [asm_ctx.resolve_integer(x, 0, 65535) for x in inst.tokens['values']]

    def size(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> int:
        return inst.size

    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        return inst.values


################################################################################
#
# TOY instruction set:
#
# Instruction formats of the original TOY:
#
#              | .... | .... | .... | .... |
#   Format 1:  |  op  |  d   |  s   |  t   |
#   Format 2:  |  op  |  d   |    addr     |
#
#
# ARITHMETIC and LOGICAL operations
#     1: ADD Rd Rs Rt     ; addition          R[d] <- R[s] + R[t]
#     2: SUB Rd Rs Rt     ; subtraction       R[d] <- R[s] - R[t]
#     3: AND Rd Rs Rt     ; bitwise and       R[d] <- R[s] & R[t]
#     4: XOR Rd Rs Rt     ; bitwise excl. or  R[d] <- R[s] ^ R[t]
#     5: SHL Rd Rs Rt     ; shift left        R[d] <- R[s] << R[t]
#     6: SHR Rd Rs Rt     ; shift right       R[d] <- R[s] >> R[t]
#
# TRANSFER between registers and memory
#     7: LDA Rd addr      ; load address      R[d] <- addr
#     8: LD  Rd addr      ; load              R[d] <- mem[addr]
#     9: ST  Rd addr      ; store             mem[addr] <- R[d]
#     A: LDI Rd Rt        ; load indirect     R[d] <- mem[R[t]]
#     B: STI Rd Rt        ; store indirect    mem[R[t]] <- R[d]
#
# CONTROL
#     0: HLT              ; halt
#     C: BZ Rd addr       ; branch zero       if (R[d] == 0) PC <- addr
#     D: BP Rd addr       ; branch positive   if (R[d] >  0) PC <- addr
#     E: JR Rd            ; jump register     PC <- R[d]
#     F: JL Rd addr       ; jump and link     R[d] <- PC + 1; PC <- addr
#
# Note that we encode unused bits in the instruction formats always as 0 to
# simplify instruction set extensions. For example, the HLT instruction is
# 0xxx according to the ISA definition which we encoded as 0000.
#
################################################################################


class FormatBase(Assembler.InstDescription, Simulation.InstDescription):
    def __init__(self, mnemonic, arg_parsers, major_opcode, implementation):
        super().__init__(mnemonic, arg_parsers)
        self.major_opcode = major_opcode
        self.implementation = implementation

    def construct(self, addr: int, mnemonic: Lexing.Token, arguments: Dict[str, Lexing.Token],
                  asm_ctx: Assembler.Context) -> Tuple[int, Optional[Assembler.Instruction]]:
        if asm_ctx._auto_org and addr < 0x10:
            addr = 0x10
        return super().construct(addr, mnemonic, arguments, asm_ctx)

    def patterns(self) -> Tuple[int, int]:
        return (0xF000, self.major_opcode << 12)

    def execute(self, inst: Simulation.Instruction, state: Simulation.ExecutionState,
                data_interface: Simulation.MemorySubsystem):
        self.implementation(inst, state, data_interface)


class Format1Register1(FormatBase):
    def __init__(self, mnemonic, major_opcode, implementation):
        super().__init__(mnemonic,
                         [Parsing.Match(TT_REGISTER, name='rd')],
                         major_opcode, implementation)

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rd = asm_ctx.resolve_integer(inst.tokens['rd'], 0, 15, 'Register number')

    # encoding = "0b{op:4}{rd:4}00000000"
    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        return [(self.major_opcode << 12) | (inst.rd << 8)]

    def patterns(self) -> Tuple[int, int]:
        return (0xF0FF, self.major_opcode << 12)

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        inst.rd = (encoding >> 8) & 0xF
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        return "{} R{:X}".format(self.mnemonic, inst.rd)


class Format1Register2(FormatBase):
    def __init__(self, mnemonic, major_opcode, implementation):
        super().__init__(
            mnemonic,
            [Parsing.Match(TT_REGISTER, name='rd'), Parsing.Match(TT_REGISTER, name='rt')],
            major_opcode, implementation)

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rd = asm_ctx.resolve_integer(inst.tokens['rd'], 0, 15, 'Register number')
        inst.rt = asm_ctx.resolve_integer(inst.tokens['rt'], 0, 15, 'Register number')

    # encoding = "0b{op:4}{rd:4}0000{rt:4}"
    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        return [(self.major_opcode << 12) | (inst.rd << 8) | inst.rt]

    def patterns(self) -> Tuple[int, int]:
        return (0xF0F0, self.major_opcode << 12)

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        inst.rd = (encoding >> 8) & 0xF
        inst.rt = encoding & 0xF
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        return "{} R{:X} R{:X}".format(self.mnemonic, inst.rd, inst.rt)


class Format1Register3(FormatBase):
    def __init__(self, mnemonic, major_opcode, implementation):
        super().__init__(
            mnemonic,
            [Parsing.Match(TT_REGISTER, name='rd'),
             Parsing.Match(TT_REGISTER, name='rs'),
             Parsing.Match(TT_REGISTER, name='rt')],
            major_opcode, implementation)

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rd = asm_ctx.resolve_integer(inst.tokens['rd'], 0, 15, 'Register number')
        inst.rs = asm_ctx.resolve_integer(inst.tokens['rs'], 0, 15, 'Register number')
        inst.rt = asm_ctx.resolve_integer(inst.tokens['rt'], 0, 15, 'Register number')

    # encoding = "0b{op:4}{rd:4}{rs:4}{rt:4}"
    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        return [(self.major_opcode << 12) | (inst.rd << 8) | (inst.rs << 4) | inst.rt]

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        inst.rd = (encoding >> 8) & 0xF
        inst.rs = (encoding >> 4) & 0xF
        inst.rt = encoding & 0xF
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        return "{} R{:X} R{:X} R{:X}".format(self.mnemonic, inst.rd, inst.rs, inst.rt)

    def execute(self, inst: Simulation.Instruction, state: Simulation.ExecutionState,
                data_interface: Simulation.MemorySubsystem):
        state[inst.rd] = self.implementation(state[inst.rs], state[inst.rt])
        state.pc += 1


class Format2(FormatBase):
    def __init__(self, mnemonic, major_opcode, implementation):
        super().__init__(
            mnemonic,
            [Parsing.Match(TT_REGISTER, name='rd'),
             Parsing.Match(TT_INTEGER, name='addr') | Parsing.Match(TT_LABEL, name='label')],
            major_opcode, implementation)

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rd = asm_ctx.resolve_integer(inst.tokens['rd'], 0, 15, 'Register number')
        if 'addr' in inst.tokens:
            inst.addr = asm_ctx.resolve_integer(inst.tokens['addr'], 0, 255, 'Address')
        else:
            inst.addr = asm_ctx.resolve_label(inst.tokens['label'], 0, 255)

    # encoding = "0b{op:4}{rd:4}{addr:8}"
    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        return [(self.major_opcode << 12) | (inst.rd << 8) | inst.addr]

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        inst.rd = (encoding >> 8) & 0xF
        inst.addr = encoding & 0xFF
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        return "{} R{:X} 0x{:X}".format(self.mnemonic, inst.rd, inst.addr)


class FormatNoArg(FormatBase):
    def __init__(self, mnemonic, major_opcode, implementation):
        super().__init__(mnemonic, [], major_opcode, implementation)

    # encoding = "0b{op:4}000000000000"
    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        return [self.major_opcode << 12]

    def patterns(self) -> Tuple[int, int]:
        return (0xFFFF, self.major_opcode << 12)

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        return Simulation.Instruction(self, address)

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        return "{}".format(self.mnemonic)


def impl_lda(inst: Simulation.Instruction, state: Simulation.ExecutionState,
             data_interface: Simulation.MemorySubsystem):
    state[inst.rd] = inst.addr
    state.pc += 1


def impl_ld(inst: Simulation.Instruction, state: Simulation.ExecutionState,
            data_interface: Simulation.MemorySubsystem):
    state[inst.rd] = data_interface[inst.addr]
    state.pc += 1


def impl_st(inst: Simulation.Instruction, state: Simulation.ExecutionState,
            data_interface: Simulation.MemorySubsystem):
    data_interface[inst.addr] = state[inst.rd]
    state.pc += 1


def impl_ldi(inst: Simulation.Instruction, state: Simulation.ExecutionState,
             data_interface: Simulation.MemorySubsystem):
    state[inst.rd] = data_interface[state[inst.rt]]
    state.pc += 1


def impl_sti(inst: Simulation.Instruction, state: Simulation.ExecutionState,
             data_interface: Simulation.MemorySubsystem):
    data_interface[state[inst.rt]] = state[inst.rd]
    state.pc += 1


def impl_hlt(inst: Simulation.Instruction, state: Simulation.ExecutionState,
             data_interface: Simulation.MemorySubsystem):
    state.end_of_execution = True
    state.pc += 1


def impl_bz(inst: Simulation.Instruction, state: Simulation.ExecutionState,
            data_interface: Simulation.MemorySubsystem):
    if state[inst.rd] == 0:
        state.pc = inst.addr
    else:
        state.pc += 1


def impl_bp(inst: Simulation.Instruction, state: Simulation.ExecutionState,
            data_interface: Simulation.MemorySubsystem):
    if state[inst.rd] > 0 and state[inst.rd] < 0x8000:
        state.pc = inst.addr
    else:
        state.pc += 1


def impl_jr(inst: Simulation.Instruction, state: Simulation.ExecutionState,
            data_interface: Simulation.MemorySubsystem):
    state.pc = state[inst.rd]


def impl_jl(inst: Simulation.Instruction, state: Simulation.ExecutionState,
            data_interface: Simulation.MemorySubsystem):
    state[inst.rd] = state.pc + 1
    state.pc = inst.addr


################################################################################
#
# Instruction set extensions in S-TOY over standard TOY:
#
# The LDI and STI instructions have been extended to support an additional
# offset immediate argument that is added to the value of Rt. The major opcode
# has not been changed for these instructions and the immediate is encoded
# into the previously unused s field of the instruction format 1.
#
# Adst: LDI Rd s Rt    ; indirect load with offset:
#                      ; R[d] <- mem[R[t] + s]
#
# Bdst: STI Rd s Rt    ; indirect store with offset:
#                      ; mem[R[t] + s] <- R[d]
#
# Additionally, new instructions that directly manipulate a stack have been
# added to S-TOY. These instructions use register RF as stack pointer and are
# extensions into the original `HLT` opcode 0. The d register field is used to
# differentiate between the new instructions and `HLT` is encoded as
# 00xx (x ... don't care) on S-TOY.
#
# 01xt: PUSH Rt   ; Push value in register Rt onto the stack.
#                 ;
#                 ; (1) R[F] <- R[F] - 1
#                 ; (2) mem[R[F]] <- R[t]
#
# 02xt: POP Rt    ; Pop value from the stack into register Rt.
#                 ;
#                 ; (1) R[t] <- mem[R[F]]
#                 ; (2) R[F] <- R[F] + 1
#
# 03im: CALL addr ; Call a sub routine by jumping to an immediate address and
#                 ; store the return address onto the stack. Note, in previous
#                 ; years, F0 (i.e., a special case for `JL R0, addr`) was used
#                 ; as opcode for this instruction.
#                 ;
#                 ; (1) R[F] <- R[F] - 1
#                 ; (2) mem[R[F]] <- PC + 1
#                 ;     PC <- imm
#
# 04xx: RET       ; Return from a sub routine call by loading the return address
#                 ; from the stack. Note, in previous years, E0 (i.e., `JR R0`)
#                 ; was used as opcode for this instruction.
#                 ;
#                 ; (1) PC <- mem[R[F]]
#                 ; (2) R[F] <- R[F] + 1
#
################################################################################

class Format1Register2Offset(FormatBase):
    def __init__(self, mnemonic, major_opcode, implementation):
        super().__init__(
            mnemonic,
            [Parsing.Match(TT_REGISTER, name='rd'),
             Parsing.Opt(Parsing.Match(TT_INTEGER, name='offset')),  # problematic with relaxed mode
             Parsing.Match(TT_REGISTER, name='rt')],
            major_opcode, implementation)

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rd = asm_ctx.resolve_integer(inst.tokens['rd'], 0, 15, 'Register number')
        inst.offset = 0
        if 'offset' in inst.tokens:
            inst.offset = asm_ctx.resolve_integer(inst.tokens['offset'], 0, 15, 'Offset')
        inst.rt = asm_ctx.resolve_integer(inst.tokens['rt'], 0, 15, 'Register number')

    # encoding = "0b{op:4}{rd:4}{offset:4}{rt:4}"
    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        return [(self.major_opcode << 12) | (inst.rd << 8) | (inst.offset << 4) | inst.rt]

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        inst.rd = (encoding >> 8) & 0xF
        inst.offset = (encoding >> 4) & 0xF
        inst.rt = encoding & 0xF
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        return "{} R{:X} 0x{:X} R{:X}".format(self.mnemonic, inst.rd, inst.offset, inst.rt)


class HltSubInstRegister1(FormatBase):
    def __init__(self, mnemonic, minor_opcode, implementation):
        super().__init__(
            mnemonic,
            [Parsing.Match(TT_REGISTER, name='rt')],
            0, implementation)
        self.minor_opcode = minor_opcode

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rt = asm_ctx.resolve_integer(inst.tokens['rt'], 0, 15, 'Register number')

    # encoding = "0b{maj_op:4}{min_op:4}0000{rt:4}"
    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        return [(self.major_opcode << 12) | (self.minor_opcode << 8) | inst.rt]

    def patterns(self) -> Tuple[int, int]:
        return (0xFFF0, (self.major_opcode << 12) | (self.minor_opcode << 8))

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        inst.rt = encoding & 0xF
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        return "{} R{:X}".format(self.mnemonic, inst.rt)


class HltSubInstAddr1(FormatBase):
    def __init__(self, mnemonic, minor_opcode, implementation):
        super().__init__(
            mnemonic,
            [Parsing.Match(TT_INTEGER, name='addr') | Parsing.Match(TT_LABEL, name='label')],
            0, implementation)
        self.minor_opcode = minor_opcode

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        if 'addr' in inst.tokens:
            inst.addr = asm_ctx.resolve_integer(inst.tokens['addr'], 0, 255, 'Address')
        else:
            inst.addr = asm_ctx.resolve_label(inst.tokens['label'], 0, 255)

    # encoding = "0b{maj_op:4}{min_op:4}{addr:8}"
    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        return [(self.major_opcode << 12) | (self.minor_opcode << 8) | inst.addr]

    def patterns(self) -> Tuple[int, int]:
        return (0xFF00, (self.major_opcode << 12) | (self.minor_opcode << 8))

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        inst.addr = encoding & 0xFF
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        return "{} 0x{:X}".format(self.mnemonic, inst.addr)


class HltSubInstNoArg(FormatBase):
    def __init__(self, mnemonic, minor_opcode, implementation):
        super().__init__(mnemonic, [], 0, implementation)
        self.minor_opcode = minor_opcode

    # encoding = "0b{maj_op:4}{min_op:4}00000000"
    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        return [(self.major_opcode << 12) | (self.minor_opcode << 8)]

    def patterns(self) -> Tuple[int, int]:
        return (0xFFFF, (self.major_opcode << 12) | (self.minor_opcode << 8))

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        return Simulation.Instruction(self, address)

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        return "{}".format(self.mnemonic)


def impl_ldi_offset(inst: Simulation.Instruction, state: Simulation.ExecutionState,
                    data_interface: Simulation.MemorySubsystem):
    state[inst.rd] = data_interface[state[inst.rt] + inst.offset]
    state.pc += 1


def impl_sti_offset(inst: Simulation.Instruction, state: Simulation.ExecutionState,
                    data_interface: Simulation.MemorySubsystem):
    data_interface[state[inst.rt] + inst.offset] = state[inst.rd]
    state.pc += 1


def impl_push(inst: Simulation.Instruction, state: Simulation.ExecutionState,
              data_interface: Simulation.MemorySubsystem):
    state[0xF] -= 1
    data_interface[state[0xF]] = state[inst.rt]
    state.pc += 1


def impl_pop(inst: Simulation.Instruction, state: Simulation.ExecutionState,
             data_interface: Simulation.MemorySubsystem):
    state[inst.rt] = data_interface[state[0xF]]
    state[0xF] += 1
    state.pc += 1


def impl_call(inst: Simulation.Instruction, state: Simulation.ExecutionState,
              data_interface: Simulation.MemorySubsystem):
    state[0xF] -= 1
    data_interface[state[0xF]] = state.pc + 1
    state.pc = inst.addr


def impl_ret(inst: Simulation.Instruction, state: Simulation.ExecutionState,
             data_interface: Simulation.MemorySubsystem):
    state.pc = data_interface[state[0xF]]
    state[0xF] += 1


ISA_DESCRIPTIONS = {'-t': 'standard TOY',
                    '-s': 'S-TOY (i.e., TOY with stack instructions)',
                    }


def instructions(mode: str = '-t'):
    ID_ADD = Format1Register3("ADD", 0x1, lambda rs, rt: rs + rt)
    ID_SUB = Format1Register3("SUB", 0x2, lambda rs, rt: rs - rt)
    ID_AND = Format1Register3("AND", 0x3, lambda rs, rt: rs & rt)
    ID_XOR = Format1Register3("XOR", 0x4, lambda rs, rt: rs ^ rt)
    ID_SHL = Format1Register3("SHL", 0x5, lambda rs, rt: rs << rt)
    ID_SHR = Format1Register3("SHR", 0x6, lambda rs, rt: rs >> rt)

    ID_LDA = Format2("LDA", 0x7, impl_lda)
    ID_LD = Format2("LD", 0x8, impl_ld)
    ID_ST = Format2("ST", 0x9, impl_st)

    ID_HLT = FormatNoArg("HLT", 0x0, impl_hlt)
    ID_BZ = Format2("BZ", 0xC, impl_bz)
    ID_BP = Format2("BP", 0xD, impl_bp)
    ID_JR = Format1Register1("JR", 0xE, impl_jr)
    ID_JL = Format2("JL", 0xF, impl_jl)

    ISA_INSTRUCTIONS = {'-t': [ID_ADD, ID_SUB, ID_AND, ID_XOR, ID_SHL, ID_SHR,
                               ID_LDA, ID_LD, ID_ST,
                               Format1Register2("LDI", 0xA, impl_ldi),
                               Format1Register2("STI", 0xB, impl_sti),
                               ID_HLT, ID_BZ, ID_BP, ID_JR, ID_JL],
                        '-s': [ID_ADD, ID_SUB, ID_AND, ID_XOR, ID_SHL, ID_SHR,
                               ID_LDA, ID_LD, ID_ST,
                               Format1Register2Offset("LDI", 0xA, impl_ldi_offset),
                               Format1Register2Offset("STI", 0xB, impl_sti_offset),
                               ID_HLT,
                               HltSubInstRegister1("PUSH", 0x1, impl_push),
                               HltSubInstRegister1("POP", 0x2, impl_pop),
                               HltSubInstAddr1("CALL", 0x3, impl_call),
                               HltSubInstNoArg("RET", 0x4, impl_ret),
                               ID_BZ, ID_BP, ID_JR, ID_JL],
                        }
    if mode in ISA_INSTRUCTIONS:
        return ISA_INSTRUCTIONS[mode]
    return []
