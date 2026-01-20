import asmlib
from asmlib.Lexing import TokenRule

import argparse
import sys
import traceback
from typing import List, no_type_check, Optional
from types import ModuleType


class AbiNameLexer(asmlib.Lexing.Context):
    """Specialized Lexer that supports ABI names for registers.
    """
    AbiRegMapping = {'zero': 0, 'ra': 1, 'sp': 2, 'gp': 3, 'tp': 4,
                     't0': 5, 't1': 6, 't2': 7,
                     's0': 8, 'fp': 8, 's1': 9,
                     'a0': 10, 'a1': 11, 'a2': 12, 'a3': 13, 'a4': 14, 'a5': 15, 'a6': 16, 'a7': 17,
                     's2': 18, 's3': 19, 's4': 20, 's5': 21, 's6': 22, 's7': 23, 's8': 24, 's9': 25,
                     's10': 26, 's11': 27,
                     't3': 28, 't4': 29, 't5': 30, 't6': 31}

    def next_token(self) -> asmlib.Lexing.Token:
        """Analyze the next token and return it.

        Post process the token from the lexer and replace word tokens that are actually ABI names
        of registers with register tokens.

        :returns: The new token.
        """
        token = super().next_token()

        if token.type == asmlib.Riscv.TT_WORD:
            nr = AbiNameLexer.AbiRegMapping.get(token.value, None)
            if nr is not None:
                token.type = asmlib.Riscv.TT_REGISTER
                token.value = nr

        return token


def assembler(filename: str, inst_desc: List[asmlib.Assembler.InstDescription],
              file_content: Optional[str] = None,
              cli_arguments: Optional[argparse.Namespace] = None) -> asmlib.Assembler.Context:

    arg_seperator_parser = asmlib.Parsing.Match(asmlib.Riscv.TT_COMMA)

    lexer_rules = [
        TokenRule(r'[ \t]+'),  # skip whitespacs
        TokenRule(r'#[^\n]*', asmlib.Riscv.TT_COMMENT),
        TokenRule(r'\r?\n', asmlib.Riscv.TT_NEWLINE),
        TokenRule(r',', asmlib.Riscv.TT_COMMA),
        TokenRule(r':', asmlib.Riscv.TT_COLON),
        TokenRule(r'\(', asmlib.Riscv.TT_LBRACKET),
        TokenRule(r'\)', asmlib.Riscv.TT_RBRACKET),
        TokenRule(r'(-?0[0-7]*)(?=[ \t#\r\n,:\(\)]|$)',  # special case for octal: 0123 not 0o123
                  asmlib.Riscv.TT_INTEGER, lambda str: int(str, 8)),
        TokenRule(r'(-?(0[bB][01]+|0[xX][0-9a-fA-F]+|[1-9][0-9]*|0))(?=[ \t#\r\n,:\(\)]|$)',
                  asmlib.Riscv.TT_INTEGER, lambda str: int(str, 0)),
        TokenRule(r'x[0-9]+(?=[ \t#\r\n,:\(\)]|$)',
                  asmlib.Riscv.TT_REGISTER, lambda str: int(str[1:], 10)),
        TokenRule(r'[0-9a-zA-Z_\.]\w*', asmlib.Riscv.TT_WORD),
    ]

    directives = [asmlib.Riscv.OrgDirectiveDescription(),
                  asmlib.Riscv.WordDirectiveDescription(),
                  ]

    lexer_ctx = AbiNameLexer(lexer_rules, filename, file_content=file_content)
    asm_ctx = asmlib.Assembler.Context(
        inst_desc + directives,
        lexer_ctx,
        arg_seperator_parser=arg_seperator_parser,
        label_seperator_parser=asmlib.Parsing.Match(asmlib.Riscv.TT_COLON),
        newline_types=[asmlib.Riscv.TT_NEWLINE],
        comment_types=[asmlib.Riscv.TT_COMMENT],
        mnemonics_types=[asmlib.Riscv.TT_MNEMONIC],
        label_types=[asmlib.Riscv.TT_LABEL],
        address_max=0x7ff
        )
    return asm_ctx


# Disable type checking here because of the following bug in typeguard:
# https://github.com/agronholm/typeguard/issues/15
@no_type_check
def cli_parsing(extensions: list = []) -> argparse.Namespace:
    # Setup the actual argument parsing logic.
    parser = argparse.ArgumentParser(
        add_help=False, allow_abbrev=False,
        description='Assembles a RISC-V asm file into a \'binary\' file.')

    parser.add_argument('input', metavar='<src_file>',
                        help='The source file that should be processed.')

    parser.add_argument('-e', '--extension', dest='extension', metavar='<python_file>',
                        help=('Extension file for providing custom instructions '
                              'and command line arguments.'))
    parser.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                        help='Show this help message and exit.')
    parser.add_argument('-o', '--output', dest='output', metavar='<file>',
                        default=argparse.SUPPRESS,
                        help=('The output file that should be written '
                              '(STDOUT is used if no output is specified).'))
    parser.add_argument('-t', dest='tokens', action='store_true', default=False,
                        help=('Print tokens before parsing.'))
    parser.add_argument('-f', '--format', dest='format',
                        default='bytes',
                        choices=['bytes', 'words'],
                        help=('Output format for the assembled code '
                              '("bytes" is used if no format is specified).'))
    parser.add_argument('-v', '--version', action='version', version=asmlib.__version__,
                        help=('Display the tool/library version and exit.'))

    # Let the extensions define command line arguments for the assembler, sort the arguments
    # alphabetically using a dirty hack -.-, and perform the parsing.
    for ext in extensions:
        if hasattr(ext, 'setup_assembler_arguments'):
            ext.setup_assembler_arguments(parser)
    for g in parser._action_groups:
        g._group_actions.sort(key=lambda x: x.dest)
    args = parser.parse_args()

    return args


def lib_main(extensions: list, args: argparse.Namespace) -> int:
    # Setup an instruction set by querying the extensions.
    isa = []
    for ext in extensions:
        if hasattr(ext, 'update_assembler_isa'):
            ext.update_assembler_isa(isa, args)

    # Assemble the input file and report errors if needed.
    asm_ctx = assembler(args.input, isa, cli_arguments=args)
    if args.tokens:
        t = asm_ctx.lexer_context.next_token()
        while t != asm_ctx.lexer_context.EOF:
            print(t)
            t = asm_ctx.lexer_context.next_token()
    asm_ctx.assemble()

    # Format the output and write it to the requested file.
    result_file = sys.stdout
    if hasattr(args, 'output'):
        result_file = open(args.output, 'w')

    # HEX format
    processed_addr = 0
    cur_bytes = bytearray()

    if args.format == 'bytes':
        group_length = 1
    elif args.format == 'words':
        group_length = 4
    else:
        raise ValueError("Illegal value for option --format")

    def flush_hex():
        if len(cur_bytes) > 0:
            value = int.from_bytes(cur_bytes, 'little')
            fmt = "{{:0{}X}}".format(group_length * 2)
            line = fmt.format(value)
            print(line, file=result_file)

        cur_bytes.clear()

    def output_hex(byte):
        cur_bytes.append(byte)

        if len(cur_bytes) == group_length:
            flush_hex()

    for address, encoding in sorted(asm_ctx.encodings.items()):
        # Fill in gaps of instructions with 00 until we reach the next valid byte.
        while processed_addr < address:
            processed_addr += 1
            output_hex(0)

        output_hex(encoding)
        processed_addr += 1

    flush_hex()

    if hasattr(args, 'output'):
        result_file.close()
    return 0


def main(extensions: list = [asmlib.Riscv.IsaSupportExtension],
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
