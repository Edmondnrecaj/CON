import asmlib
from asmlib.Lexing import TokenRule
from asmlib.Parsing import Match, MultiMatch, Opt
from asmlib.Toy import TT_COMMENT, TT_INTEGER, TT_NEWLINE

import argparse
import json
import sys
import traceback
from typing import Any, List, no_type_check, Optional, Tuple
from types import ModuleType

TT_COLON = 'Colon'


# Disable type checking here because of the following bug in typeguard:
# https://github.com/agronholm/typeguard/issues/15
@no_type_check
def cli_parsing(extensions: list = []) -> argparse.Namespace:
    # Setup the actual argument parsing logic.
    parser = argparse.ArgumentParser(
        add_help=False, allow_abbrev=False,
        description='Instruction set simulator for TOY ISA \'binary\' files.')

    parser.add_argument('-e', '--extension', dest='extension', metavar='<python_file>',
                        help=('Extension file for providing custom instructions, peripherals, '
                              'and command line arguments.'))
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help='Show this help message and exit.')
    parser.add_argument('--initial-pc', dest='initial_pc', type=int, default=0x10,
                        metavar='<addr>',
                        help='The address where execution should begin.')
    parser.add_argument('--instructions', dest='instructions', type=int, default=None,
                        metavar='<nr>',
                        help='Maximum number of instructions to simulate.')
    parser.add_argument('--trace', dest='trace', action='store_true', default=False,
                        help='Print every instruction and the processor before it is executed.')
    parser.add_argument('--relaxed', dest='relaxed', action='store_true', default=False,
                        help='Ignore reading of uninitialized registers and memory.')
    parser.add_argument('-v', '--version', action='version', version=asmlib.__version__,
                        help=('Display the tool/library version and exit.'))

    # Let the extensions define command line arguments for the simulator, sort the arguments
    # alphabetically using a dirty hack -.-, and perform the parsing.
    for ext in extensions:
        if hasattr(ext, 'setup_simulator_arguments'):
            ext.setup_simulator_arguments(parser)
    for g in parser._action_groups:
        g._group_actions.sort(key=lambda x: x.dest)
    args = parser.parse_args()

    return args


def load_toy_file(filename: str, max_addr: int = 0xFF):
    lexer_rules = [
        TokenRule(r'[ \t]+'),  # skip whitespacs
        TokenRule(r';[^\n]*', TT_COMMENT),
        TokenRule(r'\r?\n', TT_NEWLINE),
        TokenRule(r':', TT_COLON),
        TokenRule(r'[0-9a-fA-F]+', TT_INTEGER, lambda str: int(str, 16))
    ]
    lexer_ctx = asmlib.Lexing.Context(lexer_rules, filename)
    line_parser = Match(TT_INTEGER, name='addr') + \
        Match(TT_COLON) + \
        Match(TT_INTEGER, name='value') + \
        Opt(Match(TT_COMMENT)) + \
        MultiMatch([TT_NEWLINE, lexer_ctx.EOF_Type])

    data = {}
    it = asmlib.Parsing.TokenIterator(lexer_ctx)
    while it:
        res = line_parser(it)
        if not res:
            raise res.error
        it = res.next_pos
        addr_token = res.annotations['addr']
        value_token = res.annotations['value']
        if addr_token.value > max_addr:
            raise asmlib.Assembler.AssemblerTypeError(
                "Address {0} (0x{0:x}) is not in the valid range [{1},{2}]!".format(
                    addr_token.value, 0, max_addr), lexer_ctx, addr_token)
        if value_token.value > 0xFFFF:
            raise asmlib.Assembler.AssemblerTypeError(
                "Value {0} (0x{0:x}) is not in the valid range [{1},{2}]!".format(
                    value_token.value, 0, 0xFFFF), lexer_ctx, value_token)
        data[addr_token.value] = asmlib.Simulation.sign_extend(value_token.value, 16)
    return data


class RamWithProgramExtension:
    @staticmethod
    def trace_memory_cb(write: bool, addr: int, data: List[int]):
        if write:
            print("  RAM write: mem[{:02x}] <- {}".format(
                addr, asmlib.Simulation.format_value_list(data, 16, False)[0]))
        else:
            print("  RAM read:  mem[{:02x}] == {}".format(
                addr, asmlib.Simulation.format_value_list(data, 16, False)[0]))

    @staticmethod
    def setup_simulator_arguments(parser: argparse.ArgumentParser):
        parser.add_argument('input', metavar='<src_file>',
                            help='The toy \'binary\' file that should be simulated.')
        parser.add_argument('--trace-ram', dest='trace_ram', action='store_true', default=False,
                            help='Print each access to the RAM.')

    @staticmethod
    def update_simulator_devices(arbiter: asmlib.Simulation.MemoryArbiter,
                                 sim: asmlib.Simulation.Simulator,
                                 args: argparse.Namespace):
        # Load the toy file and store it into a RAM.
        data = [None]*256
        if args.relaxed:
            data = [0] * 256
        for addr, value in load_toy_file(args.input).items():
            data[addr] = value
        trace_cb = None
        if args.trace_ram:
            trace_cb = RamWithProgramExtension.trace_memory_cb
        ram = asmlib.Simulation.SimpleRAM(sim, 0, data, 16, trace_cb=trace_cb)
        arbiter.devices.insert(0, ram)
        sim.add_peripheral(ram)


def load_toy_stdin_file(filename: str) -> List[int]:
    lexer_rules = [
        TokenRule(r'[ \t]+'),  # skip whitespacs
        TokenRule(r'\r?\n'),  # skip newlines
        TokenRule(r'[0-9a-fA-F]+', TT_INTEGER, lambda str: int(str, 16))
    ]
    lexer_ctx = asmlib.Lexing.Context(lexer_rules, filename)
    data = []
    it = asmlib.Parsing.TokenIterator(lexer_ctx)
    while it:
        token = it.peek()
        error = it.consume([TT_INTEGER])
        if error is not None:
            raise error

        if token.value > 0xFFFF:
            raise asmlib.Assembler.AssemblerTypeError(
                "Value {0} (0x{0:x}) is not in the valid range [{1},{2}]!".format(
                    token.value, 0, 0xFFFF), lexer_ctx, token)
        data.append(token.value)
    return data


class ToyStdIO(asmlib.Simulation.MemorySubsystem, asmlib.Simulation.PeripheralDevice):
    def __init__(self, simulator: Optional[asmlib.Simulation.Simulator],
                 address: int, input_file_name: Optional[str],
                 output_file_name: Optional[str] = None,
                 name: str = "ToyStdIO",
                 handshake: bool = False):
        super().__init__(simulator)
        self._address = address
        self._input = []
        self._output = []
        if input_file_name is not None:
            self._input = load_toy_stdin_file(input_file_name)
        self._output_file_name = output_file_name
        self._name = name
        self._handshake = handshake

    def bounds(self) -> Tuple[int, int]:
        if self._handshake:
            return (self._address, self._address+1)
        return (self._address, self._address)

    def read(self, addr: int, size: int = 1) -> List[int]:
        assert size == 1
        if self._handshake and addr == self._address:
            if len(self._input) != 0:
                return [1]
            return [0]

        if len(self._input) < size:
            raise asmlib.Simulation.SimulationError("Reading uninitialized data from stdin.",
                                                    self.simulator)
        if self._handshake:
            return [self._input[0]]
        return [self._input.pop(0)]

    def write(self, addr: int, data: List[int]):
        assert len(data) == 1
        if self._handshake and addr == self._address:
            if data[0] == 0:
                self._input.pop(0)
            return
        self._output.append(data[0])

    def save_output(self, output_file_name: str):
        with open(output_file_name, 'w') as fd:
            for value in self._output:
                print(asmlib.Simulation.format_value(value, 16).lower(), file=fd)

    def format_state(self, skip_none: bool = False) -> List[str]:
        lines = []
        if len(self._input) > 0:
            lines.append('Input:')
            lines += asmlib.Simulation.format_value_list(self._input, 16, False)
        if len(self._output) > 0:
            lines.append('Output:')
            lines += asmlib.Simulation.format_value_list(self._output, 16, False)
        return lines

    def serialize_state(self) -> Any:
        return {"STDIN": self._input, "STDOUT": self._output}

    def end_of_simulation(self):
        if self._output_file_name is not None:
            self.save_output(self._output_file_name)


class SimpleStdIOExtension:
    @staticmethod
    def setup_simulator_arguments(parser: argparse.ArgumentParser):
        ioopts = parser.add_argument_group(
            'IO Options',
            'Customize and configure the IO module at address 0xFF.')
        ioopts.add_argument('--stdin', dest='stdin', metavar='<file>', default=None,
                            help=('File with input values.'))
        ioopts.add_argument('--stdout', dest='stdout', metavar='<file>', default=None,
                            help=('File where the output values should be saved.'))
        ioopts.add_argument('--stdin-handshake', dest='stdin_handshake', action='store_true',
                            default=False,
                            help='Enable stdin handshake support (CR register at 0xFE).')

    @staticmethod
    def update_simulator_devices(arbiter: asmlib.Simulation.MemoryArbiter,
                                 sim: asmlib.Simulation.Simulator,
                                 args: argparse.Namespace):
        if args.stdin_handshake:
            iomodule = ToyStdIO(sim, 0xFE, args.stdin, args.stdout, handshake=True)
        else:
            iomodule = ToyStdIO(sim, 0xFF, args.stdin, args.stdout)
        arbiter.devices.insert(0, iomodule)
        sim.add_peripheral(iomodule)


def trace_callback(pc: int, encoding: int,
                   inst: asmlib.Simulation.Instruction, sim: asmlib.Simulation.Simulator):
    line = "{}: {:}  {}\t{}".format(
        asmlib.Simulation.format_value(pc, sim.state.max_pc.bit_length()),
        asmlib.Simulation.format_value(encoding, 16),
        inst.desc.format(inst),
        sim.state.format_registers(per_line=sim.state.reg_number))
    print(line.expandtabs(30))


def lib_main(extensions: list, args: argparse.Namespace) -> int:
    # Setup an instruction set by querying the extensions.
    isa = []
    for ext in extensions:
        if hasattr(ext, 'update_simulator_isa'):
            ext.update_simulator_isa(isa, args)

    # Build a simulator with for the instruction set and simple memory interconnect.
    reg_value = None
    if args.relaxed:
        reg_value = 0
    init_state = asmlib.Simulation.ZeroR0ExecutionState(16, 16, 0xFF, args.initial_pc,
                                                        initial_value=reg_value)
    sim = asmlib.Simulation.Simulator(init_state, isa)
    device_arbiter = asmlib.Simulation.MemoryArbiter(sim)
    sim.data_mem = device_arbiter
    sim.inst_mem = device_arbiter

    # Define the what bus devices are available via the extensions
    for ext in extensions:
        if hasattr(ext, 'update_simulator_devices'):
            ext.update_simulator_devices(device_arbiter, sim, args)

    # Print the initial state of the simulator
    print()
    print('===============================================================================')
    print('                          Initial Simulation State')
    print('===============================================================================')
    print("\n".join(sim.format_state(include_instructions=False)))

    # Simulate the system.
    print()
    print('===============================================================================')
    print('                            Program Execution')
    print('===============================================================================')
    trace_cb = None
    if args.trace:
        trace_cb = trace_callback
    sim.run(instructions=args.instructions, trace_cb=trace_cb)

    # Print the final state of the simulator
    print()
    print('===============================================================================')
    print('                         Final Simulation State')
    print('===============================================================================')
    print("\n".join(sim.format_state()))

    # Extensions call end of simulation hooks in the extensions
    for ext in extensions:
        if hasattr(ext, 'end_of_simulation'):
            ext.end_of_simulation(sim, args)

    return 0


def main(extensions: list = [asmlib.Toy.IsaSupportExtension,
                             RamWithProgramExtension,
                             SimpleStdIOExtension,
                             asmlib.Simulation.JsonResultExtension],
         args: argparse.Namespace = None):
    if args is None:
        extensions += asmlib.cli_extension_parsing()
        args = cli_parsing(extensions)
    try:
        sys.exit(lib_main(extensions, args))
    except asmlib.AsmlibError as exception:
        print(exception, file=sys.stderr)
    except Exception:
        traceback.print_exc(file=sys.stderr)
    sys.exit(-1)
