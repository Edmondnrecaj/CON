"""Utility module for writing simple instruction set simulators.

This module provides, besides the generic simulation logic of a simulator, helper functions as well
as abstractions that are useful when writing simple instruction set simulators. These abstractions
help with dealing with the simulation state (e.g., general purpose registers), the supported
instruction set (i.e., software defined like in the assembler), and the memory subsystem (e.g., RAM,
ROM, memory mapped peripherals).
"""
from .Error import AsmlibError

import argparse
import json
import math
import shutil
from typing import Any, Callable, Dict, List, Optional, Tuple


class SimulationError(AsmlibError):
    """Specialized error type for communicating errors that are encountered during simulation time.
    """
    def __init__(self, message: str, simulator: Optional['Simulator'] = None):
        """
        :param message: Message describing the exception cause.
        :param simulator: Link to the simulator which encountered the error.
        """
        self.message = message
        self.simulator = simulator

    def __str__(self) -> str:
        lines = ['']
        lines.append('Simulation Error: {}'.format(self.message))
        lines.append('')
        if self.simulator is not None:
            lines.append('=' * 79)
            lines.append('                        Simulation Error State')
            lines.append('=' * 79)
            lines += self.simulator.format_state()
        return '\n'.join(lines)


class JsonResultExtension:
    @staticmethod
    def setup_simulator_arguments(parser: argparse.ArgumentParser):
        parser.add_argument('--json', dest='json', metavar='<file>', default=None,
                            help=('File where the final simulation state should be saved in '
                                  'json format.'))

    @staticmethod
    def end_of_simulation(sim: 'Simulator',
                          args: argparse.Namespace):
        if args.json:
            with open(args.json, 'w') as file:
                data = sim.serialize_state()
                file.write(json.dumps(data, sort_keys=True, indent=4))


# from https://stackoverflow.com/a/32031543
def sign_extend(value: int, bits: int) -> int:
    """Sign extend an unsigned integer into a python signed integer.

    :param value: The value that should be sign extended.
    :param bits: The number of bits in the input integer.
    """
    sign_bit = 1 << (bits - 1)
    return (value & (sign_bit - 1)) - (value & sign_bit)


###################################################################################################
#                               Formatting Helper Functions
###################################################################################################
def format_value(value: Optional[int], bits: int) -> str:
    """Formats an integer into a hex string with a specified length in bits.

    :param value: The integer that should be formatted. If None then 'X' is printed for all nibbles.
    :param bits: The width of the integer in bits.
    :returns: The formatted string.
    """
    digits = math.ceil(bits / 4)
    if value is not None:
        value = value % 2**bits
        return "{val:0{digits}X}".format(digits=digits, val=value)
    return "{val}".format(val='X' * digits)


def format_value_list(list: List[Optional[int]], value_bit: int,
                      add_element_labels: bool,
                      labels: Dict[int, str] = {},
                      per_line: Optional[int] = None,
                      col_alignment: Optional[int] = None) -> List[str]:
    """Formats a list of integers in a two dimensionally grid.

    This function can be used to format memory dumps as well as to print registers in a regular and
    easily comprehendable structure.

    :param list: The list with the integers that should be formatted. None -> XXXX
    :param value_bit: The width of the individual integer values in bits.
    :param add_element_labels: Add a ':' seperated label to every entry. By default, every entry is
                               simply prefixed with its index. However, this default label can be
                               overwritten via the labels dict.
    :param labels: Dictionary that associates indices with specific label strings.
    :param per_line: Number of elements printed per line. Automatically detected if None.
    :param col_alignment: The width of a layouted element. Automatically detected in None.
    :returns: List of formatted strings where each entry corresponds to one line.
    """
    if len(list) == 0:
        return []
    if add_element_labels:
        label_bits = (len(list) - 1).bit_length()
        if len(labels) > 0:
            label_bits = max(label_bits, *[len(v)*4 for v in labels.values()])
    formatted = []
    for idx, value in enumerate(list):
        if add_element_labels:
            label = labels.get(idx, format_value(idx, label_bits))
            formatted.append("{}:{}".format(label,
                                            format_value(value, value_bit)))
        else:
            formatted.append(format_value(value, value_bit))

    if col_alignment is None:
        col_alignment = len(formatted[0]) + 1
    if per_line is None:
        per_line = shutil.get_terminal_size((80, 10)).columns // col_alignment

    line = []
    lines = []
    for idx, value in enumerate(formatted):
        if idx > 0 and idx % per_line == 0:
            lines.append("\t".join(line).expandtabs(col_alignment))
            line = []
        line.append(value)
    if len(line) > 0:
        lines.append("\t".join(line).expandtabs(col_alignment))
    return lines


###################################################################################################
#                             Instruction Descriptions and Objects
###################################################################################################
class Instruction:
    """Class for describing a specific instance of a disassembled instruction.

    Note that instances of this class, as generated with the provided constructor, only link the
    instruction description with the address. However, the very same objects can also be used for
    easily storing information about decoded instruction (e.g., arguments like target and source
    registers) by monkeypatching new members into them. Alternatively, instruction type specific
    variants could be derived.
    """

    def __init__(self, desc: 'InstDescription', address: int):
        """
        :param desc: Link to the instruction description which details the type and provides the
                     implementation of its behavior.
        :param address: The start address at which the instruction is located.
        """
        self.desc = desc
        self.address = address


class InstDescription:
    """Base class for describing instruction types that are recognized by the simulator.

    Each instance derived from this class describes a specific instruction type including how it is
    matched (i.e., via a mask and a pattern), decoded into a suitable instruction object, pretty
    printed in textual assembler syntax, and executed in our simulator. Subsequently, one object
    deriving from `InstDescription` is required for each instruction that the simulator supports.
    """

    def patterns(self) -> Tuple[int, int]:
        """Returns a the mask and match patterns for this instruction type.

        :returns: Tuple where the first element is the mask and the second element is the match
                  pattern for this particular instruction type.
        """
        raise NotImplementedError

    def decode(self, address: int, encoding: int,
               state: Optional['ExecutionState'] = None) -> Instruction:
        """Decodes the binary instruction.

        :returns: An instruction object representing the decoded instruction.
        """
        raise NotImplementedError

    def format(self, inst: Instruction, **kwargs:int) -> str:
        """Format the instruction in assembler syntax without ABI representation.

        :param inst: The instruction that should be pretty printed as textual assembly.
        :param kwargs['abi']: Use ABI representation of registers.
        :returns: The formatted string.
        """
        return NotImplementedError

    def execute(self, inst: Instruction, state: 'ExecutionState',
                data_interface: 'MemorySubsystem'):
        """Forward the simulation by executing the instruction specified in the instruction object.

        In terms of processor execution state, the implementation of this method has to directly
        update the state that is provided as an argument. This update not only has to include the
        obvious effects on general purpose registers but also implicit side effects like the
        increment of the program counter.

        :param inst: The instruction that should be pretty printed.
        :param data_interface: The interface for accessing the memory subsystem.
        """
        raise NotImplementedError


###################################################################################################
#                               Processor Execution State
###################################################################################################
class ExecutionState():
    def __init__(self, registers: List[Optional[int]], reg_bits: int, max_pc: int, initial_pc: int, old_pc: int):
        self.simulator = None
        self.end_of_execution = False
        self._pc = initial_pc
        self._old_pc = old_pc
        self._registers = registers
        self.max_pc = max_pc
        self.reg_bits = reg_bits
        self._reg_mask = (1 << (reg_bits - 1))-1

    @property
    def reg_number(self):
        return len(self._registers)

    @property
    def pc(self):
        return self._pc

    @pc.setter
    def pc(self, value: int):
        value = value & self._reg_mask
        if value > self.max_pc:
            raise SimulationError("Setting PC to {0} (0x{0:x}) is invalid.".format(value),
                                  self.simulator)
        self._pc = value

    @property
    def old_pc(self):
        return self._old_pc

    @old_pc.setter
    def old_pc(self, value: int):
        value = value & self._reg_mask
        if value > self.max_pc:
            raise SimulationError("Setting Old PC to {0} (0x{0:x}) is invalid.".format(value),
                                  self.simulator)
        self._old_pc= value

    def __getitem__(self, nr: int) -> int:
        value = self._registers[nr]
        if value is None:
            raise SimulationError(("Reading uninitialized register {0} at address "
                                   "{1} (0x{1:x}).").format(nr, self.pc), self.simulator)
        return value

    def __setitem__(self, nr: int, value: int):
        self._registers[nr] = sign_extend(value, self.reg_bits)

    # Hack: Should not reside here as this is RISC-V specific
    def abi_register_name(self, register):
        assert 0 <= register <= 31
        abi_names = [
            'zero', 'ra', 'sp', 'gp', 'tp', 't0', 't1', 't2',
            'fp', 's1', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5',
            'a6', 'a7',  's2', 's3', 's4', 's5', 's6', 's7',
            's8', 's9', 's10', 's11', 't3', 't4', 't5', 't6'
        ]
        return abi_names[register]

    def format_registers(self, per_line: Optional[int] = None,
                         col_alignment: Optional[int] = None,
                         skip_none: bool = False,
                         abi: bool = False) -> str:
        labels = {}
        regs = self._registers
        if skip_none:
            bits = (len(regs) - 1).bit_length()
            if abi:
                labels = [self.abi_register_name(idx) for idx, v in enumerate(regs) if v is not None]
            else:
                labels = [format_value(idx, bits) for idx, v in enumerate(regs) if v is not None]

            labels = {idx: v for idx, v in enumerate(labels)}
            regs = [v for v in regs if v is not None]
        lines = format_value_list(regs, self.reg_bits, True, labels=labels,
                                  per_line=per_line,
                                  col_alignment=col_alignment)
        return "\n".join(lines)

    def format(self, per_line: Optional[int] = None,
               col_alignment: Optional[int] = None,
               abi: bool = False) -> List[str]:
        lines = ['PC: {}'.format(format_value(self.pc, self.reg_bits))]
        lines += [self.format_registers(per_line=per_line,
                                        col_alignment=col_alignment,
                                        skip_none=True,
                                        abi=abi)]
        return lines

    def serialize_state(self) -> Dict[str, Any]:
        registers = {idx: value for idx, value in enumerate(self._registers) if value is not None}
        return {'pc': self.pc, 'registers': registers}


class ZeroR0ExecutionState(ExecutionState):
    def __init__(self, reg_nr: int, reg_bit: int, max_pc: int, initial_pc: int,
                 initial_value: Optional[int] = None, old_pc: Optional[int] = 0x00):
        super().__init__([0] + [initial_value] * (reg_nr - 1), reg_bit, max_pc, initial_pc, old_pc)

    def __setitem__(self, nr: int, value: int):
        if nr == 0:
            return
        super().__setitem__(nr, value)


###################################################################################################
#                               Memory Interface and Components
###################################################################################################
class PeripheralDevice:
    def __init__(self):
        self._name = "???"

    @property
    def name(self):
        return self._name

    def tick(self, simulator: Optional['Simulator']):
        raise NotImplementedError

    def end_of_simulation(self):
        return

    def serialize_state(self) -> Any:
        return None

    def format_state(self, skip_none: bool = False) -> List[str]:
        return []

    def raise_interrupt(self, simulator: Optional['Simulator']) -> bool:
        return False


class MemorySubsystem:
    def __init__(self, simulator: Optional['Simulator']):
        self._simulator = simulator

    @property
    def simulator(self):
        return self._simulator

    def bounds(self) -> Tuple[int, int]:
        """Returns a the start and end address for this memory interface as tuple.
        """
        raise NotImplementedError

    def read(self, addr: int, size: int) -> List[int]:
        raise NotImplementedError

    def write(self, addr: int, data: List[int]):
        raise NotImplementedError

    def __getitem__(self, addr: int) -> int:
        return self.read(addr, 1)[0]

    def __setitem__(self, addr: int, value: int):
        return self.write(addr, [value])


class MemoryArbiter(MemorySubsystem):
    def __init__(self, simulator: Optional['Simulator']):
        super().__init__(simulator)
        self.devices = []

    def arbitrate(self, address) -> MemorySubsystem:
        for d in self.devices:
            start, end = d.bounds()
            if start <= address <= end:
                return d
        raise SimulationError(("Invalid memory access at "
                               "address {0} (0x{0:x})!").format(address),
                              self.simulator)

    def read(self, addr: int, size: int) -> List[int]:
        return self.arbitrate(addr).read(addr, size)

    def write(self, addr: int, data: List[int]):
        self.arbitrate(addr).write(addr, data)

    @property
    def simulator(self):
        return self._simulator


class SimpleRAM(MemorySubsystem, PeripheralDevice):
    def __init__(self, simulator: Optional['Simulator'],
                 base_address: int, content: List[Optional[int]], element_bits: int,
                 trace_cb: Optional[Callable[[bool, int, List[int]], None]] = None,
                 name: str = "RAM"):
        super().__init__(simulator)
        self._name = name
        self._content = content
        self._base_address = base_address
        self._element_bits = element_bits
        self._max_addr = base_address + len(self._content)
        self._trace_cb = trace_cb

    def bounds(self) -> Tuple[int, int]:
        return (self._base_address, self._max_addr-1)

    def read(self, addr: int, size: int = 1) -> List[int]:
        end_addr = addr + size
        if addr < self._base_address or end_addr > self._max_addr or size < 1:
            raise SimulationError(("Invalid memory read access [0x{:x}:0x{:x})! "
                                   "Expected accesses in range [0x{:x},0x{:x}).").format(
                                       addr, end_addr, self._base_address, self._max_addr),
                                  self.simulator)
        result = self._content[addr-self._base_address:end_addr-self._base_address]
        if None in result:
            raise SimulationError(("Reading uninitialized memory at "
                                   "address {0} (0x{0:x})!").format(result.index(None) + addr),
                                  self.simulator)
        if self._trace_cb is not None:
            self._trace_cb(False, addr, result)
        return result

    def write(self, addr: int, data: List[int]):
        end_addr = addr + len(data)
        if addr < self._base_address or end_addr > self._max_addr or len(data) < 1:
            raise SimulationError(("Invalid memory write access [0x{:x}:0x{:x})! "
                                   "Expected accesses in range [0x{:x}:0x{:x}).").format(
                                       addr, end_addr, self._base_address, self._max_addr),
                                  self.simulator)
        if self._trace_cb is not None:
            self._trace_cb(True, addr, data)
        for eaddr, e in enumerate(data, addr-self._base_address):
            self._content[eaddr] = e

    def format_state(self, skip_none: bool = False) -> List[str]:
        content = self._content
        if skip_none:
            end = len(content)
            while content[end-1] is None:
                end = end - 1
            content = content[0:end]
        return format_value_list(content, self._element_bits, False, per_line=16)

    def serialize_state(self) -> Any:
        return {idx: value for idx, value in enumerate(self._content) if value is not None}


###################################################################################################
#                               Simulation Logic
###################################################################################################
def decode(descriptions: List[InstDescription], address: int, encoding: int,
           state: Optional['ExecutionState'] = None) -> Instruction:
    # TODO Given that we currently only have a few instructions a linear scan is ok for now.
    #      However, a more sophisticated decoder should be implemented in the future.
    # TODO Extract the decoder into a dedicated module. It is also useful for writing
    #      a disassembler.
    for desc in descriptions:
        mask, match = desc.patterns()
        if encoding & mask != match:
            continue
        return desc.decode(address, encoding, state)

    raise SimulationError(("Data {0} (0x{0:x}) at address {1} (0x{1:x}) "
                           "could not be decoded.").format(encoding, address),
                          state.simulator)


class Simulator:
    def __init__(self, initial_state: ExecutionState, descriptions: List[InstDescription],
                 fetch_size: int = 1):
        self.state = initial_state
        self.descriptions = descriptions
        self.instruction = 0
        self.data_mem = None  # need to be defined after construction
        self.inst_mem = None  # need to be defined after construction
        self._devices = []          # List[PeripheralDevice]
        self._clocked_devices = []  # List[PeripheralDevice]
        self._fetch_size = fetch_size

        self.state.simulator = self

    def add_peripheral(self, device: PeripheralDevice, clocked: bool = False):
        self._devices.append(device)
        if clocked:
            self._clocked_devices.append(device)

    @property
    def devices(self):
        return self._devices

    def run(self, instructions: Optional[int] = None,
            trace_cb: Optional[Callable[[int, int, Instruction, 'Simulator'], None]] = None):
        while not self.state.end_of_execution:
            if instructions is not None and self.instruction >= instructions:
                raise SimulationError("Simulation limit of {} instructions reached.".format(
                    instructions), self)

            pc = self.state.pc
            encoding = self.inst_mem.read(pc, self._fetch_size)
            if self._fetch_size == 1:
                encoding = encoding[0]
            else:
                encoding = int.from_bytes(encoding, 'little')
            if encoding is None:
                raise SimulationError(("Reading uninitialized data at address {0} (0x{0:x}) "
                                       "as instruction.").format(pc), self)
            inst = decode(self.descriptions, self.state.pc, encoding, self.state)
            if trace_cb is not None:
                trace_cb(pc, encoding, inst, self)
            inst.desc.execute(inst, self.state, self.data_mem)
            for device in self._clocked_devices:
                device.tick(self)
                if(device.raise_interrupt(self)):
                    self.state.old_pc = pc
                    self.state.pc = 0x00
            self.instruction += 1

        for device in self._devices:
            device.end_of_simulation()

    def format_state(self, include_instructions: bool = True, skip_none: bool = False, abi: bool = False) -> List[str]:
        lines = []
        lines.append('Processor State (e.g., Registers)')
        lines.append('---------------------------------')
        lines += self.state.format(per_line=8, col_alignment=None, abi=abi)
        for device in self.devices:
            device_state = device.format_state(skip_none=skip_none)
            if len(device_state) > 0:
                lines.append('')
                lines.append(device.name)
                lines.append('-' * len(device.name))
                lines += device_state
        if include_instructions:
            lines.append('')
            lines.append('{} instructions simulated.'.format(self.instruction))
        return lines

    def serialize_state(self) -> Dict[str, Any]:
        result = self.state.serialize_state()
        result['instructions'] = self.instruction
        result['devices'] = {}
        for device in self.devices:
            device_state = device.serialize_state()
            if device_state is not None:
                result['devices'][device.name] = device_state
        return result
