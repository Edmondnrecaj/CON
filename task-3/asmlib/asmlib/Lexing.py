"""Utility module for writing simple lexical analysis as required for programming an assembler.

Inspired from the following resources:

- http://jayconrod.com/posts/37/a-simple-interpreter-from-scratch-in-python--part-1
- https://docs.python.org/3/library/re.html#writing-a-tokenizer

"""
from .Error import AsmlibLexerBasedError

import copy
import re
from typing import Any, Callable, Generator, no_type_check, List, Optional


class LexingError(AsmlibLexerBasedError):
    """Specialized lexer error that pretty prints the error message using location information.
    """

    def __init__(self, message: str, lexer_context: 'Context', location: 'Location',
                 annotation_length: int = 1):
        """
        :param message: Message describing the error cause.
        :param lexer_context: Lexer context for pretty printing message with location information.
        :param location: The location of the lexing error.
        :param annotation_length: The length of the annotation starting from location.
        """
        super().__init__(message, lexer_context, location, annotation_length, 'Lexing Error: ')


class Location:
    """Associates an offset into the source buffer with line and column information.
    """

    def __init__(self, offset: int, line: int, column: int):
        """
        :param offset: The offset into the memory buffer.
        :param line: The current line associated with the offset.
        :param column: The current column within the line.
        """
        self.offset = offset
        self.line = line
        self.column = column

    def copy(self) -> 'Location':
        """Generates a copy of the Location.

        :returns: The cloned location object.
        """
        return copy.copy(self)

    def forward(self, input: str, tab_width: int = 4):
        """Forwards the current location by parsing the provided `input` string.

        :param input: The string that should be parsed.
        :param tab_width: The width of a tab in spaces. Required for correct column counting.
        """
        for c in input:
            if c == '\n':
                self.line += 1
                self.column = 1
            elif c == '\t':
                self.column += tab_width - ((self.column - 1) % tab_width)
            else:
                self.column += 1
            self.offset += 1

    def __str__(self) -> str:
        return "@{}[{}:{}]".format(self.offset, self.line, self.column)


class Token:
    """Resulting token from the lexical analysis.
    """

    def __init__(self, context: 'Context', location: Location, length: int, type: Any,
                 value: Optional[Any] = None):
        """
        :param context: The lexing context which is associated with the token.
        :param location: The source location where the token starts.
        :param length: The length of the token in characters.
        :param type: The (arbitrary) type of the token.
        :param value: The (arbitrary) analyzed value of the token.
        """
        self.context = context
        self.location = location
        self.length = length
        self.type = type
        self._value = value

    @property
    def value(self) -> Any:
        """Getter method for the value property. If no analyzed value is available
        then the source string for the token is returned.

        :returns: The analyzed value if available, otherwise the associated source string.
        """
        if self._value is not None:
            return self._value
        return self.source_string

    @value.setter
    def value(self, value: Any):
        """Setter method for the value property.

        :param value: The (arbitrary) analyzed value of the token.
        """
        self._value = value

    @property
    def source_string(self) -> str:
        """Getter for the input string that is represented by this token.

        :returns: The raw source string for the token.
        """
        start = self.location.offset
        end = self.location.offset + self.length
        return self.context.content()[start:end]

    @property
    def expanded_source_length(self) -> int:
        """Getter for the length of the source string after tab expansion.

        :returns: The length of the token in terminal window columns.
        """
        shift = self.location.column-1
        extended_string = ' ' * shift + self.source_string
        return len(extended_string.expandtabs(self.context.tab_width)) - shift

    def __str__(self) -> str:
        return "{}+{}<{}> {}".format(self.location, self.length, self.type, repr(self.value))


class TokenRule:
    """Matching rule which associates a regular expession and an analysis function with a token
    type. TokenRule objects are used as token factories by matchin them against an input buffer.
    """

    def __init__(self, regex_str: str, type: Optional[Any] = None,
                 conversion_func: Optional[Callable[[str], Any]] = None):
        """
        :param regex_str: The regular expressen that describes a token.
        :param type: The (arbitrary) type of the token.
        :param conversion_func: The function or lambda that analysis the source string and returns
                                the token value.
        """
        self.regex = re.compile(regex_str)
        self.type = type
        self.conversion_func = conversion_func

    def match(self, context: 'Context', position: Location)-> Optional[Token]:
        """Match the rule against an input buffer within the context and return the resulting token.

        :param context: The lexing context that provides the input buffer.
        :param position: The source location within the input buffer that should be matched.
        :returns: The generated token if the rule matched, otherwise None.
        """
        match = self.regex.match(context.content(), position.offset)
        if match is not None:
            token = Token(context, position, match.end(0) - position.offset, self.type)
            if self.conversion_func is not None:
                token.value = self.conversion_func(token.source_string)
            return token
        return None


class Context:
    """Central state for the lexical analysis. This object holds the source buffer, the
    TokenRules which are applied during lexing, the resulting tokens, and the lexer itself.
    """

    EOF_Type = "EOF"

    def __init__(self, rules: List[TokenRule], file_name: str, file_content: Optional[str] = None,
                 tab_width: int = 4):
        """
        :param rules: List of TokenRules that get sequentially matched during lexing. Subsequently,
                      the sequence of the rules within the list is important and more specific rules
                      have to be placed earlier than relaxed rules. Note further that tokens with
                      ``None`` as type are dropped directly after generation and never get returned
                      from the lexer.
        :param file_name: The path the input file. Required for error reporting or for loading the
                          source if it is not directly provided via the file_content argument.
        :param file_content: The input buffer that should be tokenized.
        :param tab_width: The width of a tab in spaces. Required for correct column counting.
        """
        self.EOF = Token(self, Location(0, 1, 1), 1, self.EOF_Type)

        self._rules = rules
        self._file_name = file_name
        self._file_content = file_content
        self._line_offsets = [0]
        self.tokens = []
        self.tab_width = tab_width

        if file_content is None:
            with open(file_name, 'r') as f:
                self._file_content = f.read()

        self._lexer = self._lexer_generator()

    def content(self) -> str:
        """Getter for the raw input buffer.

        :returns: The full content of source file that is currently analyzed without modification.
        """
        return self._file_content

    def get_content_line(self, line_nr: int) -> str:
        """Getter for a specific line of the input buffer. Note that only lines that have
        already been visited by the lexical analysis can be retrieved using this method.

        :param line_nr: 1-based line number that should be retrieved.
        :returns: The raw content of the specific line incl. terminating newline if present.
        """
        line_nr -= 1  # fix numbering to be 0 based
        assert line_nr < len(self._line_offsets)
        start = self._line_offsets[line_nr]
        if line_nr + 1 < len(self._line_offsets):
            end = self._line_offsets[line_nr + 1]
            return self._file_content[start:end]

        for idx, c in enumerate(self._file_content[start:], start):
            if c == '\n':
                return self._file_content[start:idx + 1]

        return self._file_content[start:]

    def format_source_message(self, location: Location, message: str,
                              length: int = 1) -> str:
        """Formats a source specific message that includes the respective input source line and
        highlights the columns of the warning or error.

        :param location: The source location which is associated with the message.
        :param message: The message itself which should be displayed.
        :param length: The width of the annotation (e.g., token.expanded_source_length).
        :returns: The formatted message string.
        """
        msg_header = "{}:{}:{}: ".format(self._file_name, location.line, location.column)
        indent = " " * len(msg_header)
        line = repr(self.get_content_line(location.line).expandtabs(self.tab_width))
        content = []
        content += ["{}{}".format(msg_header, line)]
        content += ["{}{}{}{}".format(indent,
                                      "-" * location.column,
                                      "^" * length,
                                      "-" * (len(line) - location.column - length))]
        content += ["{}{}".format(indent, message)]
        return "\n".join(content)

    def get_token(self, token_nr: Optional[int] = None) -> Token:
        """Getter method for a specific token based the token number. Querying a number that
        has not been analyzed yet automatically forwards the lexical analysis until the token
        can be provided or until the end of the input file, marked via the EOF token, is reached.

        :param token_nr: The number of the token or the last analyzed token when None is specified.
        :returns: The token with the specified number.
        """
        if token_nr is None:
            token_nr = len(self.tokens) - 1
        while len(self.tokens) == 0 or len(self.tokens) <= token_nr:
            if self.next_token() == self.EOF:
                return self.EOF
        return self.tokens[token_nr]

    def next_token(self) -> Token:
        """Analyze the next token and return it.

        :returns: The new token.
        """
        return next(self._lexer)

    # Disable type checking here because of the following bug in typeguard:
    # https://github.com/agronholm/typeguard/issues/15
    @no_type_check
    def _lexer_generator(self) -> Generator[Token, None, None]:
        """Generator function that implements the actual lexer.

        :returns: A new token on every call and the EOF token when finished.
        """
        pos = Location(0, 1, 1)
        while pos.offset < len(self._file_content):
            token = None
            # apply lexer rules
            for rule in self._rules:
                token = rule.match(self, pos.copy())
                if token is not None:
                    # scan the token for new lines and update the location
                    for offset, c in enumerate(token.source_string, pos.offset):
                        if c == '\n' and offset + 1 < len(self._file_content):
                            self._line_offsets.append(offset + 1)
                    pos.forward(token.source_string, self.tab_width)
                    # return the token if there is a type
                    if token.type is not None:
                        self.tokens.append(token)
                        yield token
                    # abort rule matching and start parsing the next token
                    break
            # no rule matched -> report an error
            if token is None:
                message = 'Illegal character {} encountered!'.format(
                    repr(self._file_content[pos.offset]))
                raise LexingError(message, self, pos)

        self.EOF.location = pos
        while True:
            yield self.EOF
