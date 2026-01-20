from asmlib import Assembler, Lexing, Parsing, Simulation
from .BitVec import BitVec

import argparse

import os
from typing import Dict, List, Optional, Tuple, Union

TT_COLON = 'Colon'
TT_COMMA = 'Comma'
TT_COMMENT = 'Comment'
TT_INTEGER = 'Integer'
TT_LBRACKET = 'Opening Bracket'
TT_NEWLINE = 'Newline'
TT_REGISTER = 'Register'
TT_RBRACKET = 'Closing Bracket'
TT_WORD = 'Word'

TT_LABEL = Parsing.TokenTypeAlias('Label', [TT_WORD, TT_REGISTER])
TT_MNEMONIC = Parsing.TokenTypeAlias('Mnemonic', [TT_WORD])


class IsaSupportExtension:
    @staticmethod
    def setup_assembler_arguments(parser: argparse.ArgumentParser):
        # TODO setup mutually exclusive selection of RISC-V ISA variants
        return

    @staticmethod
    def update_assembler_isa(isa: List[Assembler.InstDescription], args: argparse.Namespace):
        isa += instructions('')

    setup_simulator_arguments = setup_assembler_arguments
    update_simulator_isa = update_assembler_isa


################################################################################
#
# Assembler directives:
#
# .org ... define the "origin", i.e. start address of the following instruction
#
#   example:
#     .org 0x10    # put the following instruction at address 0x10
#
#
# .word  ... define the contents of one or several 32-bit words in main memory
#
#   examples:
#
#     A: .word 5       # symbolic address A with value 5
#     B: .word 0xC     # symbolic address B with hex-value C
#     D: .word 7, 8, 9 # define the contents of 3 memory words starting with
#                      # symbolic address D
#
################################################################################
class OrgDirectiveDescription(Assembler.InstDescription):
    def __init__(self):
        super().__init__(".org", [Parsing.Match(TT_INTEGER, name='addr')])

    def construct(self, addr: int, mnemonic: Lexing.Token, arguments: Dict[str, Lexing.Token],
                  asm_ctx: Assembler.Context) -> Tuple[int, Optional[Assembler.Instruction]]:
        return (arguments['addr'].value, None)


class WordDirectiveDescription(Assembler.InstDescription):
    def __init__(self):
        super().__init__(".word",
                         [Parsing.MultiMatch([TT_INTEGER, TT_LABEL], name='head') +
                          Parsing.RepetitionParser(
                              Parsing.Match(TT_COMMA) +
                              Parsing.MultiMatch([TT_INTEGER, TT_LABEL], name='tail'))])

    def construct(self, addr: int, mnemonic: Lexing.Token,
                  arguments: Dict[str, Union[Lexing.Token, List[Lexing.Token]]],
                  asm_ctx: Assembler.Context) -> Tuple[int, Optional[Assembler.Instruction]]:
        arguments['values'] = [arguments.pop('head')] + arguments.pop('tail', [])
        inst = Assembler.Instruction(self, addr, mnemonic, arguments)
        inst.size = len(arguments['values'])*4
        return (addr + inst.size, inst)

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        def resolve_int_or_label(token: Lexing.Token):
            if token.type == TT_INTEGER:
                return asm_ctx.resolve_integer(token, -2**31, (2**32)-1) % 2**32
            return asm_ctx.resolve_label(token, 0, (2**32)-1)

        inst.values = [resolve_int_or_label(x) for x in inst.tokens['values']]

    def size(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> int:
        return inst.size

    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        res = []
        for v in inst.values:
            res += list(v.to_bytes(4, 'little'))
        return res


####################################################################################################
#
# RISC-V Instruction Formats:
# ---------------------------
#
#                             31          25 24      20 19      15 14  12 11       7 6            0
# R-Type(opc,funct3,funct7): |    funct7    |   rs2    |   rs1    |funct3|   rd     |     opc      |
# I-Type(opc,funct3):        |          imm[11:0]      |   rs1    |funct3|   rd     |     opc      |
# S-Type(opc,funct3):        |  imm[11:5]   |   rs2    |   rs1    |funct3| imm[4:0] |     opc      |
# B-Type(opc,funct3):        | imm[12|10:5] |   rs2    |   rs1    |funct3|im[4:1|11]|     opc      |
# U-Type(opc):               |                imm[31:12]                 |   rd     |     opc      |
# J-Type(opc):               |           imm[20|10:1|11|19:12]           |   rd     |     opc      |
#
# RISC-V Immediate Formats (z denotes a fixed zero bit):
# ------------------------------------------------------
#
#                             31 30                 20 19            12 11 10         5 4      1  0
# I-Immediate:               |                 <-- sext 31                |    30:25   |  24:21 |20|
# S-Immediate:               |                 <-- sext 31                |    30:25   |  11:8  | 7|
# B-Immediate:               |               <-- sext 31               | 7|    30:25   |  11:8  | z|
# U-Immediate:               |31|        30:20        |      19:12     |            zzzzzz         |
# J-Immediate:               |       <-- sext 31      |      19:12     |20|    30:25   |  24:21 | z|
#
####################################################################################################
# BitVec shorthands for often-used widths
BV3 = lambda v: BitVec(v, 3)
BV5 = lambda v: BitVec(v, 5)
BV7 = lambda v: BitVec(v, 7)
BV12 = lambda v: BitVec(v, 12)


def abi_register_name(register: int, abi: bool) -> str:
    assert 0 <= register <= 31
    if abi:
        abi_names = [
            'zero', 'ra', 'sp', 'gp', 'tp', 't0', 't1', 't2',
            'fp', 's1', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5',
            'a6', 'a7',  's2', 's3', 's4', 's5', 's6', 's7',
            's8', 's9', 's10', 's11', 't3', 't4', 't5', 't6'
        ]
        return abi_names[register]
    else:
        return 'x{}'.format(register)


class RType(Assembler.InstDescription, Simulation.InstDescription):
    def __init__(self, mnemonic, opcode, funct3, funct7, implementation):
        super().__init__(mnemonic, [Parsing.Match(TT_REGISTER, name='rd'),
                                    Parsing.Match(TT_REGISTER, name='rs1'),
                                    Parsing.Match(TT_REGISTER, name='rs2')])
        self.opcode = opcode
        self.funct3 = funct3
        self.funct7 = funct7
        self.implementation = implementation

    def size(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> int:
        return 4

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rd = asm_ctx.resolve_integer(inst.tokens['rd'], 0, 31, 'Register number')
        inst.rs1 = asm_ctx.resolve_integer(inst.tokens['rs1'], 0, 31, 'Register number')
        inst.rs2 = asm_ctx.resolve_integer(inst.tokens['rs2'], 0, 31, 'Register number')

    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        val = BitVec.concat(BV7(self.funct7), BV5(inst.rs2), BV5(inst.rs1), BV3(self.funct3),
                            BV5(inst.rd), BV7(self.opcode)).n
        return list(val.to_bytes(4, 'little'))

    def patterns(self) -> Tuple[int, int]:
        mask = BitVec.concat(BV7(-1), BV5(0), BV5(0), BV3(-1), BV5(0), BV7(-1)).n
        match = BitVec.concat(BV7(self.funct7), BV5(0), BV5(0), BV3(self.funct3), BV5(0),
                              BV7(self.opcode)).n
        return (mask, match)

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        v = BitVec(encoding, 32)
        inst.rd = v[11:7].n
        inst.rs1 = v[19:15].n
        inst.rs2 = v[24:20].n
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        abi = kwargs.get('abi', False)
        return "{} {}, {}, {}".format(self.mnemonic,
                                      abi_register_name(inst.rd, abi),
                                      abi_register_name(inst.rs1, abi),
                                      abi_register_name(inst.rs2, abi))

    def execute(self, inst: Simulation.Instruction, state: Simulation.ExecutionState,
                data_interface: Simulation.MemorySubsystem):
        state[inst.rd] = self.implementation(state[inst.rs1], state[inst.rs2])
        state.pc += 4


class IType(Assembler.InstDescription, Simulation.InstDescription):
    def __init__(self, mnemonic, arg_parsers, opcode, funct3, implementation):
        super().__init__(mnemonic, arg_parsers)
        self.opcode = opcode
        self.funct3 = funct3
        self.implementation = implementation

    def size(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> int:
        return 4

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rd = asm_ctx.resolve_integer(inst.tokens['rd'], 0, 31, 'Register number')
        inst.rs1 = asm_ctx.resolve_integer(inst.tokens['rs1'], 0, 31, 'Register number')
        inst.imm = asm_ctx.resolve_integer(inst.tokens['imm'], -2**11, 2**11 - 1,
                                           'Immediate/Offset')

    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        imm = BitVec(inst.imm, 12)
        val = BitVec.concat(imm, BV5(inst.rs1), BV3(self.funct3), BV5(inst.rd), BV7(self.opcode)).n
        return list(val.to_bytes(4, 'little'))

    def patterns(self) -> Tuple[int, int]:
        mask = BitVec.concat(BV12(0), BV5(0), BV3(-1), BV5(0), BV7(-1)).n
        match = BitVec.concat(BV12(0), BV5(0), BV3(self.funct3), BV5(0), BV7(self.opcode)).n
        return (mask, match)

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        v = BitVec(encoding, 32)
        inst.rd = v[11:7].n
        inst.rs1 = v[19:15].n
        inst.imm = v[31:20].sn
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        abi = kwargs.get('abi', False)
        return "{} {}, {}({})".format(self.mnemonic,
                                      abi_register_name(inst.rd, abi),
                                      inst.imm,
                                      abi_register_name(inst.rs1, abi))

    def execute(self, inst: Simulation.Instruction, state: Simulation.ExecutionState,
                data_interface: Simulation.MemorySubsystem):
        self.implementation(inst, state, data_interface)


class SType(Assembler.InstDescription, Simulation.InstDescription):
    def __init__(self, mnemonic, opcode, funct3, implementation):
        super().__init__(mnemonic,
                         [Parsing.Match(TT_REGISTER, name='rs2'),
                          (Parsing.Match(TT_INTEGER, name='imm') +
                           Parsing.Match(TT_LBRACKET) +
                           Parsing.Match(TT_REGISTER, name='rs1') +
                           Parsing.Match(TT_RBRACKET)) |
                          Parsing.Match(TT_LABEL, name='label')])
        self.opcode = opcode
        self.funct3 = funct3
        self.implementation = implementation

    def size(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> int:
        return 4

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rs2 = asm_ctx.resolve_integer(inst.tokens['rs2'], 0, 31, 'Register number')
        if 'label' in inst.tokens:
            inst.rs1 = 0
            inst.imm = asm_ctx.resolve_label(inst.tokens['label'], 0, 2**11 - 1)
        else:
            inst.rs1 = asm_ctx.resolve_integer(inst.tokens['rs1'], 0, 31, 'Register number')
            inst.imm = asm_ctx.resolve_integer(inst.tokens['imm'], -2**11, 2**11 - 1,
                                               'Immediate/Offset')

    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        imm = BitVec(inst.imm, 12)
        val = BitVec.concat(imm[11:5], BV5(inst.rs2), BV5(inst.rs1), BV3(self.funct3), imm[4:0],
                            BV7(self.opcode)).n
        return list(val.to_bytes(4, 'little'))

    def patterns(self) -> Tuple[int, int]:
        mask = BitVec.concat(BV7(0), BV5(0), BV5(0), BV3(-1), BV5(0), BV7(-1)).n
        match = BitVec.concat(BV7(0), BV5(0), BV5(0), BV3(self.funct3), BV5(0), BV7(self.opcode)).n
        return (mask, match)

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        v = BitVec(encoding, 32)
        inst.rs1 = v[19:15].n
        inst.rs2 = v[24:20].n
        inst.imm = BitVec.concat(v[31:25], v[11:7]).sn
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        abi = kwargs.get('abi', False)
        return "{} {}, {}({})".format(self.mnemonic,
                                      abi_register_name(inst.rs2, abi),
                                      inst.imm,
                                      abi_register_name(inst.rs1, abi))

    def execute(self, inst: Simulation.Instruction, state: Simulation.ExecutionState,
                data_interface: Simulation.MemorySubsystem):
        self.implementation(inst, state, data_interface)


class BType(Assembler.InstDescription, Simulation.InstDescription):
    def __init__(self, mnemonic, opcode, funct3, implementation):
        super().__init__(mnemonic,
                         [Parsing.Match(TT_REGISTER, name='rs1'),
                          Parsing.Match(TT_REGISTER, name='rs2'),
                          Parsing.Match(TT_LABEL, name='label') |
                          Parsing.Match(TT_INTEGER, name='imm')])
        self.opcode = opcode
        self.funct3 = funct3
        self.implementation = implementation

    def size(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> int:
        return 4

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rs1 = asm_ctx.resolve_integer(inst.tokens['rs1'], 0, 31, 'Register number')
        inst.rs2 = asm_ctx.resolve_integer(inst.tokens['rs2'], 0, 31, 'Register number')
        if 'label' in inst.tokens:
            inst.imm = asm_ctx.resolve_label_offset(inst, inst.tokens['label'], -2**12, 2**12 - 1,
                                                    alignment=2)
        else:
            inst.imm = asm_ctx.resolve_integer(inst.tokens['imm'], -2**12, 2**12 - 1, alignment=2)

    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        imm = BitVec(inst.imm, 13)
        val = BitVec.concat(imm[12], imm[10:5], BV5(inst.rs2), BV5(inst.rs1), BV3(self.funct3),
                            imm[4:1], imm[11], BV7(self.opcode)).n
        return list(val.to_bytes(4, 'little'))

    def patterns(self) -> Tuple[int, int]:
        mask = BitVec.concat(BV7(0), BV5(0), BV5(0), BV3(-1), BV5(0), BV7(-1)).n
        match = BitVec.concat(BV7(0), BV5(0), BV5(0), BV3(self.funct3), BV5(0), BV7(self.opcode)).n
        return (mask, match)

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        v = BitVec(encoding, 32)
        inst.rs1 = v[19:15].n
        inst.rs2 = v[24:20].n
        inst.imm = BitVec.concat(v[31], v[7], v[30:25], v[11:8], BitVec(0, 1)).sn
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        abi = kwargs.get('abi', False)
        return "{} {}, {}, {}".format(self.mnemonic,
                                      abi_register_name(inst.rs1, abi),
                                      abi_register_name(inst.rs2, abi),
                                      inst.imm)

    def execute(self, inst: Simulation.Instruction, state: Simulation.ExecutionState,
                data_interface: Simulation.MemorySubsystem):
        if self.implementation(state[inst.rs1], state[inst.rs2]):
            state.pc += inst.imm
        else:
            state.pc += 4

class UType(Assembler.InstDescription, Simulation.InstDescription):
    def __init__(self, mnemonic, opcode, implementation):
        super().__init__(mnemonic,
                         [Parsing.Match(TT_REGISTER, name='rd'),
                           Parsing.Match(TT_INTEGER, name='imm'),
                          ])
        self.opcode = opcode
        self.implementation = implementation

    def size(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> int:
        return 4

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rd = asm_ctx.resolve_integer(inst.tokens['rd'], 0, 31, 'Register number')
        inst.imm = asm_ctx.resolve_integer(inst.tokens['imm'], 0, 2**20 - 1) << 12

    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        imm = BitVec(inst.imm >> 12, 20)
        val = BitVec.concat(imm, BV5(inst.rd), BV7(self.opcode)).n
        return list(val.to_bytes(4, 'little'))

    def patterns(self) -> Tuple[int, int]:
        mask = BV7(-1).n
        match = BV7(self.opcode).n
        return (mask, match)

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        v = BitVec(encoding, 32)
        inst.rd = v[11:7].n
        inst.imm = BitVec.concat(v[31:12], BitVec(0, 12)).sn
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        abi = kwargs.get('abi', False)
        return "{} {}, {}".format(self.mnemonic, abi_register_name(inst.rd, abi),
                                  inst.imm >> 12)

    def execute(self, inst: Simulation.Instruction, state: Simulation.ExecutionState,
                data_interface: Simulation.MemorySubsystem):
        self.implementation(inst, state, data_interface)


class JType(Assembler.InstDescription, Simulation.InstDescription):
    def __init__(self, mnemonic, opcode):
        super().__init__(mnemonic,
                         [Parsing.Match(TT_REGISTER, name='rd'),
                          (Parsing.Match(TT_LABEL, name='label') |
                           Parsing.Match(TT_INTEGER, name='imm')),
                          ])
        self.opcode = opcode

    def size(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> int:
        return 4

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rd = asm_ctx.resolve_integer(inst.tokens['rd'], 0, 31, 'Register number')
        if 'label' in inst.tokens:
            inst.imm = asm_ctx.resolve_label_offset(inst, inst.tokens['label'], -2**20, 2**20 - 1,
                                                    alignment=2)
        else:
            inst.imm = asm_ctx.resolve_integer(inst.tokens['imm'], -2**20, 2**20 - 1, alignment=2)

    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        imm = BitVec(inst.imm, 21)
        val = BitVec.concat(imm[20], imm[10:1], imm[11], imm[19:12], BV5(inst.rd),
                            BV7(self.opcode)).n
        return list(val.to_bytes(4, 'little'))

    def patterns(self) -> Tuple[int, int]:
        mask = BV7(-1).n
        match = BV7(self.opcode).n
        return (mask, match)

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        v = BitVec(encoding, 32)
        inst.rd = v[11:7].n
        inst.imm = BitVec.concat(v[31], v[19:12], v[20], v[30:25], v[24:21], BitVec(0, 1)).sn
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        abi = kwargs.get('abi', False)
        return "{} {}, {}".format(self.mnemonic,
                                  abi_register_name(inst.rd, abi),
                                  inst.imm)

    def execute(self, inst: Simulation.Instruction, state: Simulation.ExecutionState,
                data_interface: Simulation.MemorySubsystem):
        next_pc = state.pc + 4
        state.pc = (state.pc + inst.imm) & ~1
        state[inst.rd] = next_pc


class RawType(Assembler.InstDescription, Simulation.InstDescription):
    def __init__(self, mnemonic, opcode, implementation):
        super().__init__(mnemonic, [])
        self.opcode = opcode
        self.implementation = implementation

    def size(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> int:
        return 4

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        pass

    def encode(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context) -> List[int]:
        return list(self.opcode.to_bytes(4, 'little'))

    def patterns(self) -> Tuple[int, int]:
        mask = BitVec(-1, 32).n
        match = self.opcode
        return (mask, match)

    def decode(self, address: int, encoding: int,
               state: Optional[Simulation.ExecutionState] = None) -> Simulation.Instruction:
        inst = Simulation.Instruction(self, address)
        return inst

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        return self.mnemonic

    def execute(self, inst: Simulation.Instruction, state: Simulation.ExecutionState,
                data_interface: Simulation.MemorySubsystem):
        self.implementation(inst, state, data_interface)


###############################################################################
# Helper Instruction Formats
###############################################################################
class LoadType(IType):
    def __init__(self, mnemonic, opcode, funct3, implementation):
        super().__init__(mnemonic,
                         [Parsing.Match(TT_REGISTER, name='rd'),
                          (Parsing.Match(TT_INTEGER, name='imm') +
                           Parsing.Match(TT_LBRACKET) +
                           Parsing.Match(TT_REGISTER, name='rs1') +
                           Parsing.Match(TT_RBRACKET)) |
                          Parsing.Match(TT_LABEL, name='label')],
                         opcode,
                         funct3,
                         implementation)

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rd = asm_ctx.resolve_integer(inst.tokens['rd'], 0, 31, 'Register number')
        if 'label' in inst.tokens:
            inst.rs1 = 0
            inst.imm = asm_ctx.resolve_label(inst.tokens['label'], 0, 2**11 - 1)
        else:
            inst.rs1 = asm_ctx.resolve_integer(inst.tokens['rs1'], 0, 31, 'Register number')
            inst.imm = asm_ctx.resolve_integer(inst.tokens['imm'], -2**11, 2**11 - 1,
                                               'Immediate/Offset')


class ImmOffsetType(IType):
    def __init__(self, mnemonic, opcode, funct3, implementation):
        super().__init__(mnemonic,
                         [Parsing.Match(TT_REGISTER, name='rd'),
                          (Parsing.Match(TT_INTEGER, name='imm') +
                           Parsing.Match(TT_LBRACKET) +
                           Parsing.Match(TT_REGISTER, name='rs1') +
                           Parsing.Match(TT_RBRACKET)),
                          ],
                         opcode,
                         funct3,
                         implementation)


class ImmType(IType):
    def __init__(self, mnemonic, opcode, funct3, implementation):
        super().__init__(mnemonic,
                         [Parsing.Match(TT_REGISTER, name='rd'),
                           Parsing.Match(TT_REGISTER, name='rs1'),
                           Parsing.Match(TT_INTEGER, name='imm') |
                           Parsing.Match(TT_LABEL, name='label')
                          ],
                         opcode,
                         funct3,
                         implementation)

    def resolve(self, inst: Assembler.Instruction, asm_ctx: Assembler.Context):
        inst.rd = asm_ctx.resolve_integer(inst.tokens['rd'], 0, 31, 'Register number')
        inst.rs1 = asm_ctx.resolve_integer(inst.tokens['rs1'], 0, 31, 'Register number')
        if 'label' in inst.tokens:
            inst.imm = asm_ctx.resolve_label(inst.tokens['label'], 0, 2**11 - 1)
        else:
            inst.imm = asm_ctx.resolve_integer(inst.tokens['imm'], -2**11, 2**12 - 1,
                                               'Immediate/Offset')

    def format(self, inst: Simulation.Instruction, **kwargs:int) -> str:
        abi = kwargs.get('abi', False)
        return "{} {}, {}, {}".format(self.mnemonic,
                                      abi_register_name(inst.rd, abi),
                                      abi_register_name(inst.rs1, abi),
                                       inst.imm)


###############################################################################
# Implementation Helpers
###############################################################################
def impl_lw(inst: Simulation.Instruction, state: Simulation.ExecutionState,
            data_interface: Simulation.MemorySubsystem):
    state[inst.rd] = int.from_bytes(data_interface.read(state[inst.rs1] + inst.imm, 4),
                                    'little', signed=True)
    state.pc += 4


def impl_sw(inst: Simulation.Instruction, state: Simulation.ExecutionState,
            data_interface: Simulation.MemorySubsystem):

    data_interface.write(state[inst.rs1] + inst.imm, list(state[inst.rs2].to_bytes(4, 'little',
                                                                                   signed=True)))
    state.pc += 4


def impl_addi(inst: Simulation.Instruction, state: Simulation.ExecutionState,
            data_interface: Simulation.MemorySubsystem):
    state[inst.rd] = state[inst.rs1] + inst.imm
    state.pc += 4


def impl_lui(inst: Simulation.Instruction, state: Simulation.ExecutionState,
            data_interface: Simulation.MemorySubsystem):
    state[inst.rd] = inst.imm
    state.pc += 4


def impl_jalr(inst: Simulation.Instruction, state: Simulation.ExecutionState,
              data_interface: Simulation.MemorySubsystem):
    next_pc = state.pc + 4
    state.pc = (state[inst.rs1] + inst.imm) & ~1
    state[inst.rd] = next_pc


def impl_ebreak(inst: Simulation.Instruction, state: Simulation.ExecutionState,
                data_interface: Simulation.MemorySubsystem):
    state.end_of_execution = True
    state.pc += 4


def impl_mret(inst: Simulation.Instruction, state: Simulation.ExecutionState,
              data_interface: Simulation.MemorySubsystem):
    state.pc = state.old_pc


###################################################################################################
# Nano RISC-V
# ===========
#
# Instruction Set:
# ----------------
#
#  R-Type(0x33,0x0,0x0): ADD    rd, rs1, rs2      ; addition         R[d] <- R[s1] + R[s2]
#  I-Type(0x03,0x2):     LW     rd, imm(rs1)      ; load word        R[d] <- mem[R[s1] + imm]
#                        LW     rd, label         ;                  R[d] <- mem[R[0] + %lo(label)]
#  S-Type(0x23,0x2):     SW     rs2, imm(rs1)     ; store word       mem[R[s1] + imm] <- R[s2]
#                        SW     rs2, label        ;                  R[d] <- mem[R[0] + %lo(label)]
#  0x00,0x10,0x00,0x73:  EBREAK                   ; stop execution
#  0x30,0x10,0x00,0x73:  MRET                     ; return from interrupt
#
###################################################################################################
def instructions(mode: str):
    ID_ADD = RType("ADD", 0x33, 0x0, 0x0, lambda rs1, rs2: rs1 + rs2)
    ID_SUB = RType("SUB", 0x33, 0x0, 0x20, lambda rs1, rs2: rs1 - rs2)
    ID_AND = RType("AND", 0x33, 0x7, 0x0, lambda rs1, rs2: rs1 & rs2)
    ID_OR = RType("OR",  0x33, 0x6, 0x0, lambda rs1, rs2: rs1 | rs2)
    ID_XOR = RType("XOR", 0x33, 0x4, 0x0, lambda rs1, rs2: rs1 ^ rs2)
    ID_SRA = RType("SRA", 0x33, 0x5, 0x20, lambda rs1, rs2: rs1 >> rs2)
    ID_SRL = RType("SRL", 0x33, 0x5, 0x0, lambda rs1, rs2: BitVec(rs1, 32).n >> rs2)
    ID_SLL = RType("SLL", 0x33, 0x1, 0x0, lambda rs1, rs2: rs1 << rs2)

    ID_LW = LoadType("LW", 0x03, 0x2, impl_lw)
    ID_SW = SType("SW", 0x23, 0x2, impl_sw)

    ID_BEQ = BType("BEQ", 0x63, 0x0, lambda rs1, rs2: rs1 == rs2)
    ID_BNE = BType("BNE", 0x63, 0x1, lambda rs1, rs2: rs1 != rs2)
    ID_BLT = BType("BLT", 0x63, 0x4, lambda rs1, rs2: rs1 < rs2)
    ID_BGE = BType("BGE", 0x63, 0x5, lambda rs1, rs2: rs1 >= rs2)

    ID_ADDI = ImmType("ADDI", 0x13, 0x0, impl_addi)
    ID_LUI = UType("LUI", 0x37, impl_lui)

    ID_JALR = ImmOffsetType("JALR", 0x67, 0x0, impl_jalr)
    ID_JAL = JType("JAL", 0x6f)

    ID_EBREAK = RawType("EBREAK", 0x00100073, impl_ebreak)
    ID_MRET = RawType("MRET", 0x30000073, impl_mret)

    return [
        ID_ADD, ID_SUB, ID_AND, ID_OR, ID_SRA, ID_SRL, ID_SLL, ID_XOR,
        ID_LW, ID_SW,
        ID_BEQ, ID_BNE, ID_BLT, ID_BGE,
        ID_ADDI, ID_LUI,
        ID_JALR, ID_JAL,
        ID_EBREAK, ID_MRET
    ]
