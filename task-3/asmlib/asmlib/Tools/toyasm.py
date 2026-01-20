import asmlib
from asmlib.Lexing import TokenRule

import argparse
import sys
import traceback
from typing import List, no_type_check, Optional
from types import ModuleType


def assembler(filename: str, inst_desc: List[asmlib.Assembler.InstDescription],
              file_content: Optional[str] = None,
              cli_arguments: Optional[argparse.Namespace] = None) -> asmlib.Assembler.Context:
    relaxed = False
    auto_org = False

    # fetch arguments if they are provided
    if cli_arguments is not None:
        if hasattr(cli_arguments, 'toy_relaxed'):
            relaxed = cli_arguments.toy_relaxed
        if hasattr(cli_arguments, 'toy_auto_org'):
            auto_org = cli_arguments.toy_auto_org

    arg_seperator_parser = None
    if relaxed:
        arg_seperator_parser = asmlib.Parsing.Opt(asmlib.Parsing.Match(asmlib.Toy.TT_COMMA))

    lexer_rules = [
        TokenRule(r'[ \t]+'),  # skip whitespacs
        TokenRule(r';[^\n]*', asmlib.Toy.TT_COMMENT),
        TokenRule(r'\r?\n', asmlib.Toy.TT_NEWLINE),
        TokenRule(r',', asmlib.Toy.TT_COMMA),
        TokenRule(r'(0[bB][01]+|0[oO][0-7]+|0[xX][0-9a-fA-F]+|[0-9]+)(?=[, \t\n;]|$)',
                  asmlib.Toy.TT_INTEGER, lambda str: int(str, 0)),
        TokenRule(r'R[0-9a-fA-F]+(?=[, \t\n;]|$)',
                  asmlib.Toy.TT_REGISTER, lambda str: int(str[1:], 16)),
        TokenRule(r'[a-zA-Z_]\w*', asmlib.Toy.TT_WORD),
    ]

    directives = [asmlib.Toy.OrgDescription(),
                  asmlib.Toy.DupDescription(),
                  asmlib.Toy.DwDescription(arg_seperator_parser=arg_seperator_parser),
                  ]

    lexer_ctx = asmlib.Lexing.Context(lexer_rules, filename, file_content=file_content)
    asm_ctx = asmlib.Assembler.Context(
        inst_desc + directives,
        lexer_ctx,
        arg_seperator_parser=arg_seperator_parser,
        newline_types=[asmlib.Toy.TT_NEWLINE],
        comment_types=[asmlib.Toy.TT_COMMENT],
        mnemonics_types=[asmlib.Toy.TT_MNEMONIC],
        label_types=[asmlib.Toy.TT_LABEL],
        )
    asm_ctx._auto_org = auto_org
    return asm_ctx


class AsmOptExtension:
    @staticmethod
    def setup_assembler_arguments(parser: argparse.ArgumentParser):
        options = parser.add_argument_group(
            'Assembler options', 'Customize the assembler behavior.')

        options.add_argument('--auto-org', dest='toy_auto_org', action='store_true', default=False,
                             help=('When no ORG directive has been used before it, place the first '
                                   'instruction automatically at 0x10 if possible.'))
        options.add_argument('--relaxed', dest='toy_relaxed', action='store_true', default=False,
                             help='Accept commas between the arguments of instructions.')


# Disable type checking here because of the following bug in typeguard:
# https://github.com/agronholm/typeguard/issues/15
@no_type_check
def cli_parsing(extensions: list = []) -> argparse.Namespace:
    # Setup the actual argument parsing logic.
    parser = argparse.ArgumentParser(
        add_help=False, allow_abbrev=False,
        description='Assembles a TOY asm file into a TOY \'binary\' file.')

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
    parser.add_argument('-f', '--format', dest='format',
                        default='toy',
                        choices=['toy', 'hex'],
                        help=('Output format for the assembled code '
                              '("toy" is used if no format is specified).'))
    p = parser.add_argument('-p', dest='print', action='store_true', default=False,
                            help=('Print assembly code next to the machine code. '
                                  'Only supported with the "toy" output format.'))
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

    # sanitize the combination of arguments
    if args.print and args.format != "toy":
        raise argparse.ArgumentError(p, "only allowed when using toy as output format")

    return args


def lib_main(extensions: list, args: argparse.Namespace) -> int:
    # Setup an instruction set by querying the extensions.
    isa = []
    for ext in extensions:
        if hasattr(ext, 'update_assembler_isa'):
            ext.update_assembler_isa(isa, args)

    # Assemble the input file and report errors if needed.
    asm_ctx = assembler(args.input, isa, cli_arguments=args)
    lexer_context = asm_ctx.lexer_context
    # t = asm_ctx.lexer_context.next_token()
    # while t != asm_ctx.lexer_context.EOF:
    #     print(t)
    #     t = asm_ctx.lexer_context.next_token()
    asm_ctx.assemble()

    # Format the output and write it to the requested file.
    result_file = sys.stdout
    if hasattr(args, 'output'):
        result_file = open(args.output, 'w')

    if args.format == 'toy':
        for address in sorted(asm_ctx.encodings):
            line = "{:02X}: {:04X}".format(address, asm_ctx.encodings[address])
            if args.print and address in asm_ctx.instructions:
                inst = asm_ctx.instructions[address]
                src_line = lexer_context.get_content_line(inst.mnemonic_token.location.line).rstrip()
                line = "{} ; {}".format(line, src_line)
            print(line, file=result_file)
    else:
        assert args.format == 'hex'
        processed_addr = 0
        for address in sorted(asm_ctx.encodings):
            # Fill in gaps of instructions with 0000 (HLT) until we reach
            # the next instruction.
            while processed_addr < address:
                processed_addr += 1
                print("0000", file=result_file)

            line = "{:04X}".format(asm_ctx.encodings[address])
            print(line, file=result_file)
            processed_addr += 1

    if hasattr(args, 'output'):
        result_file.close()
    return 0


def main(extensions: list = [AsmOptExtension, asmlib.Toy.IsaSupportExtension],
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
