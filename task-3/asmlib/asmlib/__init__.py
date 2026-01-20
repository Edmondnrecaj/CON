"""
Tooling package for the computer architecture course (aka Rechnerorganisation) at
`Graz University of Technology <https://www.tugraz.at>`_.
"""
from .Assembler import *
from .Lexing import *
from .Parsing import *
from .Riscv import *
from .Simulation import *
from .Toy import *
from .Version import __version__

import importlib.util
import errno
import os

if 'ASMLIB_ENABLE_TYPEGUARD' in os.environ:
    from typeguard import TypeChecker
    checker = TypeChecker('asmlib')
    checker.start()


def cli_extension_parsing() -> list:
    # Make a first pass over the command line arguments to determine if additional extensions
    # should be loaded. Import them if some have been found.
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument('-e', '--extension', action='append', dest='extensions')
    args, _ = parser.parse_known_args()
    extensions = []
    if args.extensions is not None:
        for extpath in set(args.extensions):
            if not os.path.isfile(extpath):
                raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), extpath)
            name = os.path.splitext(os.path.basename(extpath))[0]
            spec = importlib.util.spec_from_file_location(name, extpath)
            ext = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ext)
            extensions.append(ext)
    return extensions
