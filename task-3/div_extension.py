#!/usr/bin/env python3
import argparse
from asmlib import Assembler, Riscv, Simulation
from typing import List, Union

def divide(rs1, rs2):
    if rs1 < 0:
        rs1 += 2**32
    if rs2 < 0:
        rs2 += 2**32
    if rs2 == 0:
        return 2**32-1
    return int(rs1 / rs2)


def update_assembler_isa(isa: List[Union[Assembler.InstDescription, Simulation.InstDescription]],
                         cli_args: argparse.Namespace):
    isa.append(Riscv.RType("DIVU",   0x33, 0x5, 0x1, divide))

update_simulator_isa = update_assembler_isa
