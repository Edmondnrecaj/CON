"""Utility module for writing simple assemblers.

This module provides an abstract implementation of a simple assembler in the :class:`.Context`
class. This assembler supports the parsing of labels, programmatically defined instructions (see
:class:`InstDescription`), and line comments. Furthermore, a symbol table is generated from the
labels and actual binary generation is performed with the help of the instruction set description.
"""

from asmlib import Lexing, Parsing
from asmlib.Parsing import Alternative, Match, MultiMatch, Opt
from .Error import AsmlibLexerBasedError

from typing import Any, Dict, List, Optional, Tuple, Union


class AssemblerTypeError(AsmlibLexerBasedError):
    """Specialized assembler error that pretty prints the error message using location information.

    This error class is primarily used to describe semantically errors that can occur during
    assembling and code generation. Examples for such semantical errors are the redefinition of
    labels, range errors when resolving branches/jumps, and out-of-range operands for specific
    instructions.
    """
    def __init__(self, message: str, lexer_context: Lexing.Context, token: Lexing.Token):
        """
        :param message: Message describing the error cause.
        :param lexer_context: Lexer context for pretty printing message with location information.
        :param token: The token on which the error was discovered.
        """
        super().__init__(message, lexer_context, token.location, token.expanded_source_length,
                         'Type Error: ')
        self._token = token

    @property
    def token(self) -> Lexing.Token:
        """Read only property that returns the lexer token.

        :returns: The token which is associated with the error.
        """
        return self._token


class Instruction:
    """Class for describing a specific instance of an instruction which is parsed by the assembler.

    Each instance of this class simply stores information about one particular instance of a
    instruction. Subsequently, by default, one class:`Instruction` object is generated for every
    assembler instruction in an assembled file.

    Note that instances of this class, as generated with the provided constructor, only link the
    instruction description with the respective tokens in the source. However, the very same objects
    can also be used for easily storing information about the resolved (i.e., type checked)
    instruction by monkeypatching new members into them. Alternatively, instruction type specific
    variants could be derived.
    """

    def __init__(self, desc: 'InstDescription', address: int,
                 mnemonic_token: Lexing.Token,
                 arg_tokens: Dict[str, Union[Lexing.Token, List[Lexing.Token]]] = {}):
        """
        :param desc: Link to the instruction description which details the type and provides the
                     implementation of its behavior.
        :param address: The start address at which the instruction is located.
        :param mnemonic_token: Link to the start of the instruction in the assembled token stream.
        :param arg_tokens: Link to the individual named instruction arguments in the token stream.
        """
        self.address = address
        self.mnemonic_token = mnemonic_token
        self.desc = desc
        self.tokens = arg_tokens


class InstDescription:
    """Base class for describing instruction types that are recognized by the assembler.

    Each instance derived from this class describes a specific instruction type including how it is
    parsed (i.e., the mnemonic and the arguments) and how the binary encoding for it is generated.
    Subsequently, one object deriving from `InstDescription` is required for each instruction that
    the assembler supports.
    """

    def __init__(self, mnemonic: str, arg_parsers: List[Parsing.Parser]):
        """
        :param mnemonic: The mnemonic that uniquely identifies the instruction type.
        :param arg_parsers: List of parsers for the arguments, i.e., one for each argument.
        """
        self.mnemonic = mnemonic
        self.arg_parsers = arg_parsers

    def construct(self, addr: int, mnemonic_token: Lexing.Token,
                  arg_tokens: Dict[str, Union[Lexing.Token, List[Lexing.Token]]],
                  asm_ctx: 'Context') -> Tuple[int, Optional[Instruction]]:
        """Hook for constructing a :class:`Instruction` object of the respective type.

        :param addr: The start address at which the instruction is located.
        :param mnemonic_token: Link to the start of the instruction in the token stream.
        :param arg_tokens: Link to the individual named instruction arguments in the token stream.
        :param asm_ctx: The assembler context that parsed the instruction and wants to construct
                        the instruction object.
        :returns: Tuple in which the first element is the address after the instruction
                  (i.e., the start address of the next sequential instruction), and the second
                  element is the constructed instruction object or None when no code generation is
                  required.
        """
        inst = Instruction(self, addr, mnemonic_token, arg_tokens)
        return (addr + self.size(inst, asm_ctx), inst)

    def size(self, inst: Instruction, asm_ctx: 'Context') -> int:
        """Hook to query the size of a specific instruction.

        :param inst: The instruction object for the specific instruction of which the size should
                     be determined.
        :param asm_ctx: The assembler context that is associated with the request.
        :returns: The size of the specific instruction in addressable units (e.g., number of bytes
                  when the memory is byte-wise addressable).
        """
        return 1

    def resolve(self, inst: Instruction, asm_ctx: 'Context'):
        """Hook to resolve and type check an instruction object.

        :param inst: The instruction object that should be resolved.
        :param asm_ctx: The assembler context that is associated with the request.
        """
        pass

    def encode(self, inst: Instruction, asm_ctx: 'Context') -> List[int]:
        """Hook to encode an instruction object into its binary representation.

        :param inst: The instruction object that should be encoded.
        :param asm_ctx: The assembler context that is associated with the request.
        :returns: List with :meth:`size` many elements containing the binary value for each
                  addressable memory cell which is part of the instruction encoding.
        """
        raise NotImplementedError


# TODO: Think about replacing the LineParser with a custom derived parser class for better error
#       reporting. Currently, when the label and mnemonic type is equal, incorrect instructions
#       always get matched as valid label and the first argument is reported as type error. However,
#       since labels are definitely not as common as ordinary lines, defaulting to report an
#       mnemonic value error seems more sensible. (i.e., use the error from the label line only if
#       it occurred more than one token into the parse)
def LineParser(descriptions: List[InstDescription],
               arg_seperator_parser: Optional[Parsing.Parser] = None,
               label_seperator_parser: Optional[Parsing.Parser] = None,
               comment_types: Optional[List[Any]] = None,
               newline_types: List[Any] = ['NEWLINE'],
               label_types: List[Any] = ['LABEL'],
               mnemonics_types: List[Any] = ['MNEMONIC']) -> Parsing.Parser:
    """Factory function that returns a simple parser for one line of textual assembler.

    :param descriptions: List of instruction descriptions that should be supported by the parser.
    :param arg_seperator_parser: An optional parser that should be intertwined into the argument
                                 parsing code of the instructions. Specifying, for example, a parser
                                 that matches comma enforces that all instruction arguments have to
                                 be comma separated.
    :param label_seperator_parser: An optional parser that should be matched between the label and
                                   the mnemonic.
    :param comment_types: List of token types that are potentially comments.
    :param newline_types: List of token types that are potentially newlines.
    :param label_types: List of token types that are potentially labels.
    :param mnemonics_types: List of token types that are potentially instruction mnemonics.
    :returns: The resulting parser for matching a single line of textual assembler code.
    """

    def join(arg_parsers: List[Parsing.Parser]):
        if arg_seperator_parser is not None:
            fillers = [arg_seperator_parser] * (len(arg_parsers) * 2 - 1)
            fillers[0::2] = arg_parsers
            arg_parsers = fillers
        return Parsing.Concat(arg_parsers)

    # generate the argument parser for each instruction
    # FIXME: The currently used Alternative parser linearly scans each possibility. Given that
    #        the mnemonics are known and clearly distinguish the following instruction, a faster
    #        lookuptable based Alternative match parser should be used here.
    #        (see AlternativeMatchParser)
    desc_dict = {d.mnemonic: join(d.arg_parsers) for d in descriptions}
    instruction_parser = Alternative([
        MultiMatch(mnemonics_types, [k], name='_mnemonic') + p for k, p in desc_dict.items()
    ])

    # Each line is expected to have the following token sequence:
    #   Grammer: (<label>? <mnemonic> <argument>*)? <comment>? (<newline>|<EOF>)
    #
    # Unfortunately we can not simply write this grammer as is with the used parsing library because
    # of the way repetition/alternative parsers are implemented currently (i.e., they are greedy and
    # no proper backtracking is performed once a possible solution has been matched).
    #
    # We, therefore, implement this grammer by distinguishing the three major cases:
    # 1. Empty line with support for comments:
    #   Grammer: <comment>? (<newline>|<EOF>)
    empty_line = MultiMatch([*newline_types, Lexing.Context.EOF_Type])
    if comment_types is not None:
        empty_line = Opt(MultiMatch(comment_types)) + empty_line

    # 2. Line with instruction and optional comment
    #   Grammer: <mnemonic> <argument>* <comment>? (<newline>|<EOF>)
    without_label = instruction_parser + empty_line

    # 3. Line with label, instruction, and optional comment
    #   Grammer: <label> <mnemonic> <argument>* <comment>? (<newline>|<EOF>)
    with_label = MultiMatch(label_types, name='_label')
    if label_seperator_parser:
        with_label += label_seperator_parser
    with_label += without_label

    # The final parser is the combination of the three parsers
    parser = empty_line | without_label | with_label

    # If there is a label seperator, also allow lines containing only a label
    if label_seperator_parser:
        # 4. Line with label and optional comment
        #   Grammar: <label> <comment>? (<newline>|<EOF>)
        label_only = MultiMatch(label_types, name='_label') + \
            label_seperator_parser + empty_line

        parser |= label_only

    return parser


class Symbol:
    """Represents a symbol by associating a label lexer token with an address.
    """

    def __init__(self, symbol_token: Lexing.Token, address: int):
        """
        :param symbol_token: Link to the label token in the assembled token stream.
        :param address: The address which is associated with the symbol.
        """
        self.token = symbol_token
        self.address = address


class Context:
    """Generic implementation of a simple line-based assembler.

    The assembler provides support for parsing labels, line comments, and programmatically defined
    instructions. Furthermore, a symbol table is generated from the labels and actual binary
    generation is performed with the help of the instruction set description.

    In terms of complexity, a two pass assembling approach is implemented. In the first pass, lazy
    lexical analysis is performed on the input, instructions and labels are parsed line-by-line,
    instruction objects are generated with their final address, and a symbol table is generated from
    the labels. In the second pass, type checking for all instructions is performed, jump/branch
    offsets/targets are resolved, and the binary encoding for the instructions is generated.
    """

    def __init__(self, descriptions: List[InstDescription], lexer_context: Lexing.Context,
                 arg_seperator_parser: Optional[Parsing.Parser] = None,
                 label_seperator_parser: Optional[Parsing.Parser] = None,
                 comment_types: Optional[List[Any]] = None,
                 newline_types: List[Any] = ['NEWLINE'],
                 label_types: List[Any] = ['LABEL'],
                 mnemonics_types: List[Any] = ['MNEMONIC'],
                 initial_pc: int = 0,
                 address_min: int = 0,
                 address_max: int = 255):
        """
        :param descriptions: List of instruction descriptions that should be supported.
        :param arg_seperator_parser: An optional parser that should be intertwined into the argument
                                     parsing code of the instructions. Specifying, for example, a
                                     parser that matches comma enforces that all instruction
                                     arguments have to be comma separated.
        :param label_seperator_parser: An optional parser that should be matched between the label
                                       and the mnemonic.
        :param comment_types: List of token types that are potentially comments.
        :param newline_types: List of token types that are potentially newlines.
        :param label_types: List of token types that are potentially labels.
        :param mnemonics_types: List of token types that are potentially instruction mnemonics.
        :param initial_pc: The address at which the first instruction is layouted.
        :param address_min: The lower bound of the address space, used for range checks.
        :param address_max: The upper bound of the address space, used for range checks.
        """
        self._lexer_context = lexer_context
        self._descriptions = {d.mnemonic: d for d in descriptions}
        self._current_pc = initial_pc
        self._address_min = address_min
        self._address_max = address_max
        self._instructions = None
        self._symbol_table = None
        self._encodings = None
        self._line_parser = LineParser(descriptions,
                                       arg_seperator_parser=arg_seperator_parser,
                                       label_seperator_parser=label_seperator_parser,
                                       comment_types=comment_types,
                                       newline_types=newline_types,
                                       label_types=label_types,
                                       mnemonics_types=mnemonics_types)

    def resolve_integer(self, token: Lexing.Token, min: int, max: int,
                        name: str = 'Integer value', alignment: int = 1) -> int:
        """Helper to perform a range check on a token with an integer value.

        :param token: The token that holds the value which should be range checked.
        :param min: The smallest accepted value in the valid integer range.
        :param max: The highest accepted value in the valid integer range.
        :param name: Semantic name of the integer for the exception message. (e.g., "Register")
        :param alignment: Alignment constraint for the integer in bytes (only powers of 2).
        :returns: The checked integer if it is in range, otherwise an exception is raised.
        """
        result = token.value
        if result < min or result > max:
            raise AssemblerTypeError(("{0} {1} is not in the valid range "
                                      "[{2},{3}]!").format(name, result, min, max),
                                     self._lexer_context, token)
        if (result & (alignment - 1)) != 0:
            raise AssemblerTypeError(
                "{} {} is incorrectly aligned (mod {} != 0)!".format(name, result, alignment),
                self._lexer_context, token)
        return result

    def resolve_label(self, token: Lexing.Token, min: int, max: int, alignment: int = 1) -> int:
        """Helper to resolve a label token into an address and perform a range check.

        :param token: The token that holds the label which should be resolved and range checked.
        :param min: The smallest accepted value in the valid address range.
        :param max: The highest accepted value in the valid address range.
        :param alignment: Alignment constraint for the address in bytes (only powers of 2).
        :returns: The resolved address if it is in range, otherwise an exception is raised.
        """
        label_str = token.source_string
        if label_str not in self._symbol_table:
            raise AssemblerTypeError(
                "Label {} is not defined!".format(repr(label_str)),
                self._lexer_context, token)
        address = self._symbol_table[label_str].address
        if address < min or address > max:
            raise AssemblerTypeError(
                "Label {} at address {} is out of range [{},{}]!".format(repr(label_str),
                                                                         address, min, max),
                self._lexer_context, token)
        if (address & (alignment - 1)) != 0:
            raise AssemblerTypeError(
                ("Label {} at address {} is incorrectly aligned "
                 "(mod {} != 0)!").format(repr(label_str), address, alignment),
                self._lexer_context, token)
        return address

    def resolve_label_offset(self, inst: Instruction, token: Lexing.Token, min: int, max: int,
                             alignment: int = 1) -> int:
        """Helper to resolve a label token into a relative offset and perform a range check.

        :param inst: The instruction to which the relative offset should be resolved.
        :param token: The token that holds the label which should be resolved and range checked.
        :param min: The smallest accepted offset value.
        :param max: The highest accepted offset value.
        :param alignment: Alignment constraint for the relative offset in bytes (only powers of 2).
        :returns: The resolved relative offset if it is in range, otherwise an exception is raised.
        """
        label_str = token.source_string
        if label_str not in self._symbol_table:
            raise AssemblerTypeError(
                "Label {} is not defined!".format(repr(label_str)),
                self._lexer_context, token)
        label_address = self._symbol_table[label_str].address
        offset = label_address - inst.address
        if offset < min or offset > max:
            raise AssemblerTypeError(
                "Relative offset ({}) to the label {} is out of range [{},{}]!".format(
                    offset, repr(label_str), min, max), self._lexer_context, token)
        if (offset & (alignment - 1)) != 0:
            raise AssemblerTypeError(
                "Relative offset ({}) to the label {} is incorrectly aligned (mod {} != 0)!".format(
                    offset, repr(label_str), alignment), self._lexer_context, token)
        return offset

    def assemble(self):
        """Eagerly assemble the input stream and cache the results in object members.
        """
        it = Parsing.TokenIterator(self._lexer_context)

        # first pass over the input
        self._instructions = {}
        self._symbol_table = {}
        while it:
            # parse one line
            res = self._line_parser(it.copy())
            if not res:
                raise res.error
            it = res.next_pos

            # construct symbols if a label was parsed
            if '_label' in res.annotations:
                label_token = res.annotations['_label']
                label_str = label_token.source_string
                if label_str in self._symbol_table:
                    # TODO Improve the error message by providing information about the
                    #      previous declaration.
                    raise AssemblerTypeError(
                        "Redefinition of label {}!".format(repr(label_str)),
                        self._lexer_context, label_token)
                self._symbol_table[label_str] = Symbol(label_token, self._current_pc)

            # construct a instruction object if an instruction was parsed
            if '_mnemonic' in res.annotations:
                mnemonic_token = res.annotations['_mnemonic']
                arguments = {k: v for k, v in res.annotations.items() if not k.startswith('_')}
                desc = self._descriptions[mnemonic_token.source_string]
                self._current_pc, inst = desc.construct(self._current_pc, mnemonic_token,
                                                        arguments, self)
                if inst is not None:
                    if inst.address < self._address_min or \
                            inst.address + inst.desc.size(inst, self) - 1 > self._address_max:
                        raise AssemblerTypeError(
                            ("Address space [{1},{2}] overflow! Instruction can not be placed at "
                             "address {0} (0x{0:x}).").format(inst.address, self._address_min,
                                                              self._address_max),
                            self._lexer_context,
                            inst.mnemonic_token)
                    self._instructions[inst.address] = inst

        # second (indirect) pass over the input by traversing the instruction object list
        # type check and encode all instructions
        self._encodings = {}
        for _, inst in self._instructions.items():
            inst.desc.resolve(inst, self)
            data = inst.desc.encode(inst, self)
            assert len(data) == inst.desc.size(inst, self)
            for address, word in enumerate(data, inst.address):
                assert address not in self._encodings
                self._encodings[address] = word

    @property
    def lexer_context(self) -> Lexing.Context:
        """Read only property that returns the lexer context.

        :returns: The lexer context which is associated with the assembler context.
        """
        return self._lexer_context

    @property
    def instructions(self) -> Dict[int, Instruction]:
        """Read only property that returns the parsed and resolved instruction objects.

        :returns: Dictionary which maps instruction addresses to resolved instruction objects.
        """
        if self._instructions is None:
            self.assemble()
        return self._instructions

    @property
    def encodings(self) -> Dict[int, int]:
        """Read only property that returns the encodings associated with their respective addresses.

        :returns: Dictionary which maps instruction addresses to encoded instructions.
        """
        if self._encodings is None:
            self.assemble()
        return self._encodings

    @property
    def symbol_table(self) -> Dict[str, Symbol]:
        """Read only property that returns the symbol table.

        :returns: Dictionary which maps symbol names to symbol objects.
        """
        if self._symbol_table is None:
            self.assemble()
        return self._symbol_table
