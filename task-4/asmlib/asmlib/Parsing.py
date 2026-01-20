
"""Utility module for writing simple recursive descent parsers as required for our tools.

This module provides two different types of classes. The first type are general utility classes like
:class:`.TokenIterator`, :class:`.Result`, and :class:`.ParsingError`. These classes are useful when
writing recursive descent parsers by hand and provide the foundation for writing composable parsers
at an higher abstraction level. The second type of classes in this module are an example of such
high level parsing interface.

In particular, the :class:`.Parser` interface and its derived classes (e.g., :class:`.ConcatParser`,
:class:`.AlternativeParser`, ... ) provide a simple parser combinator library [1]_ that permits to
compose larger parsers from smaller subparsers in a declarative manner. The idea is to define
parsing rules in a DSL similar to a grammer for the respective language.

Note however that our DSL, while entirely sufficient for conveniently parsing comparable simple
expressions as need for our tools, is not well suited for writing arbitrary complex parsers. This is
due to the fact that, besides other shortcomings, the generated parsers are greedy and lack proper
backtracking. If these types of features are needed, fully fledged parser generators (e.g., ANTLR)
should be considered instead.

.. [1] inspired by http://jayconrod.com/posts/38/a-simple-interpreter-from-scratch-in-python-part-2

"""

from asmlib import Lexing
from .Error import AsmlibLexerBasedError

import copy
from operator import attrgetter
from typing import Any, Dict, List, Optional


class ParsingError(AsmlibLexerBasedError):
    """Specialized parser error that pretty prints the error message using location information.

    This error class is used to describe both, type-based and value-based parsing errors. If both
    types of errors are associated with a single object, value errors take precedence over type
    errors and get reported in the error message.
    """

    def __init__(self, position: 'TokenIterator',
                 expected_types: List[Any] = [], expected_values: List[Any] = []):
        """
        :param position: Iterator marking the position in the token stream that triggered the error.
        :param expected_types: List of types that have been expected but where not found.
        :param expected_values: List of values that have been expected but where not found.
        """
        super().__init__('', position.context, position.peek().location,
                         position.peek().expanded_source_length, 'Parsing Error: ')
        self._expected_types = expected_types.copy()
        self._expected_values = expected_values.copy()
        self._position = position.copy()

    def merge_into(self, other: 'ParsingError'):
        """Merges the expected types and values from a second error object into the current one.

        Note that both error objects have to be associated with the same point in the token stream
        to be mergeable, i.e., the position iterator has to be equal.

        :param other: The second error object from which expected types and values are extracted.
        """
        # Ensure that only correct error objects can be merged and that the position of the error
        # is the same.
        assert isinstance(other, ParsingError) and self._position == other._position
        self._expected_types.extend(
            x for x in other._expected_types if x not in self._expected_types)
        self._expected_values.extend(
            x for x in other._expected_values if x not in self._expected_values)

    def _format_sequence(self, list: List[str]) -> str:
        """Pretty prints a list of strings by joining them with commas and an "or".

        :param list: The list of strings that should be joined.
        :returns: The joined string.
        """
        if len(list) < 3:
            return " or ".join(list)
        return ", ".join(list[:-1]) + ", or " + list[-1]

    @property
    def position(self) -> 'TokenIterator':
        """Read only property for the error position.

        :returns: The error position as iterator into the token stream.
        """
        return self._position

    @property
    def message(self) -> str:
        """Read only property that returns the error message.

        :returns: Message that lists the expected and the encountered type(s) or value(s).
        """
        if len(self._expected_values) > 0:
            sequence = self._format_sequence(sorted([repr(t) for t in self._expected_values]))
            return 'Expected {} but found {}!'.format(
                sequence, repr(self._position.peek().source_string))

        assert len(self._expected_types) > 0
        sequence = self._format_sequence(sorted([str(t) for t in self._expected_types]))
        return 'Expected {} but found {} instead!'.format(
            sequence, str(self._position.peek().type))


class TokenIterator:
    """Iterator pointing to a concrete position in the token stream.
    """

    def __init__(self, context: Lexing.Context, token_nr: int = 0):
        """
        :param context: Lexer context that provides the token stream.
        :param token_nr: The index position to which the iterator should point.
        """
        self.context = context
        self.token_nr = token_nr

    def __bool__(self) -> bool:
        """
        :returns: True if the iterator is valid, i.e., points to a token that is not EOF.
        """
        return self.peek() is not self.context.EOF

    def __eq__(self, other: 'TokenIterator') -> bool:
        """Equality comparision operator for two iterators.

        :param other: The second iterator that is compared against.
        :returns: True if both iterators point to the same token stream and token.
        """
        return self.context is other.context and self.token_nr == other.token_nr

    def copy(self) -> 'TokenIterator':
        """Generates a (shallow) copy of the TokenIterator.

        :returns: The cloned iterator object.
        """
        return copy.copy(self)

    def peek(self, offset: int = 0) -> Lexing.Token:
        """Dereferences the iterator taking into account an optional offset.

        :param offset: Index offset for looking ahead from the current token position.
        :returns: The associated token.
        """
        return self.context.get_token(self.token_nr + offset)

    def consume(self, types: Optional[List[Any]] = None,
                values: Optional[List[Any]] = None) -> Optional[ParsingError]:
        """Checks that the current token fulfils certain constraints and forwards the iterator.

        The constraints are verified by checking if the token type or value is equal to one of the
        elements in a list of expected possibilities. Type and value constraints are checked
        independently and the final result is a conjunction (i.e., logical and) of the individual
        test results. When the check succeeds, the iterator is forwarded to the next token,
        otherwise an error is returned.

        :param types: List of expected types. Check is skipped if None is specified.
        :param values: List of expected values. Check is skipped if None is specified.
        :returns: Error object when a check fails or None on success.
        """
        t = self.peek()
        if types is not None and t.type not in types:
            return ParsingError(position=self, expected_types=types)
        if values is not None and t.value not in values:
            return ParsingError(position=self, expected_values=values)
        self.token_nr += 1
        return None


class TokenTypeAlias:
    """Utility class that permits to associate (multiple) real token types with a new name.
    """
    def __init__(self, name: str, real_types: List[Any]):
        """
        :param name: Name of the alias.
        :param real_types: List of token types that are hidden behind the alias.
        """
        self.name = name
        self.real_types = real_types

    def __eq__(self, other: Any) -> bool:
        """Equality comparision operator for arbitrary token types.

        :param other: The other token type that is compared against.
        :returns: True if the other token type is within the list of aliased types.
        """
        return other in self.real_types

    def __str__(self) -> str:
        return self.name


class Result:
    """Parsing result holding either the outcome of a successful parse or an error object.

    This result type is used by our parser combinator library to represent both, successful and
    erroneous parsing attempts. However, it can also easily be used in custom hand written recursive
    descent parsers. For successful parsing invocations, the following three types of data are
    provided as object members:

    * :attr:`next_pos` which is a :class:`.TokenIterator` pointing to the next (not yet parsed)
      token.
    * :attr:`parse_tree` which can be an arbitrary data structure (i.e., typically a tree) that
      provides information about the parsed tokens and in which context they were consumed.
    * :attr:`annotations` which is a dictionary that provides direct access to nodes that have been
      annotated by a parser. (i.e., akin to a filtered :attr:`parse_tree`)

    In case of a failed parse, detectable by casting the result object to a bool, :attr:`next_pos`
    is not initialized and returns None. The :attr:`error` member can be used in such situations to
    retrieve a :class:`.ParsingError` object that contains details about the parsing issue.
    """

    def __init__(self, next_pos: Optional[TokenIterator], parse_tree: Optional[Any] = None,
                 annotations: dict = {}, error: Optional[ParsingError] = None):
        """
        :param next_pos: :class:`.TokenIterator` pointing to the next (not yet parsed) token.
        :param parse_tree: Arbitrary data structure representing result of the parser and its
                           subparsers.
        :param annotations: Dictionary containing parsing results that have been given a name.
        :param error: :class:`.ParsingError` object that provide details about the parsing issue.
        """
        self.error = error
        self.next_pos = next_pos
        self.parse_tree = parse_tree
        self.annotations = annotations

    def __bool__(self) -> bool:
        """
        :returns: True if the result is valid, i.e., the parsing was successful.
        """
        return self.next_pos is not None


def ErrorResult(error: ParsingError) -> Result:
    """Constructor function that generates a result object containing the provided parsing error.

    :param error: :class:`.ParsingError` object that provide details about the parsing issue.
    :returns: :class:`.Result` object that contains the provided error object.
    """
    return Result(None, error=error)


def extract_error(errors: List[ParsingError]) -> ParsingError:
    """Helper function that extracts the hopefully most helpful error from a list of error objects.

    Selects the error objects that occurred the furthest into the parsing. If multiple, errors
    occurred on the same token, all these errors are merged.

    :param errors: List of error objects that have to be condensed into a single error object.
    :returns: The resulting error object.
    """
    errors.sort(key=attrgetter('position.token_nr'), reverse=1)

    # filter errors, combine them into one and return this error as result
    errors = [e for e in errors if e.position == errors[0].position]
    for e in errors[1:]:
        errors[0].merge_into(e)
    return errors[0]


def overwrite_combine_dicts(a: dict, b: dict) -> dict:
    """Helper function that merges two dictionaries into a single dictionary by possibly overwriting
    values.

    :param a: First input dictionary.
    :param b: Second input dictionary. Overwrites entries in the first dictionary with the same key.
    :returns: The resulting combined dictionary.
    """
    if len(b) == 0:
        return a
    if len(a) == 0:
        return b
    a.update(b)
    return a


def list_combine_dicts(dicts: List[dict]) -> dict:
    """Helper function that merges a list of dictionaries into a single dictionary by placing the
    values into lists.

    :param dicts: List of input dictionaries.
    :returns: The resulting combined dictionary where each value is a list.
    """
    res = dicts[0]
    for k, v in res.items():
        res[k] = [v]
    for d in dicts[1:]:
        for k, v in d.items():
            if k in res:
                res[k].append(v)
            else:
                res[k] = [v]
    return res


class Parser:
    """Abstract base class for the parser combinator library.

    All parsers that are part of our small DSL have to derive from this base class in order to be
    nicely composable (e.g., :class:`MatchParser`). The basic idea of each derived parser is that it
    implements its logic into the magic :meth:`__call__` method which takes a
    :class:`.TokenIterator` and returns a :class:`.Result` object. The base class, on the other
    hand, provides magic methods for the concatenation of parsers (i.e., :meth:`__add__`), and for
    trying multiple alternative parsers (i.e., :meth:`__or__`).

    Using the magic methods, writing parsers for simple expessions looks very similar to the grammer
    of such parsers. For example, writing and using a parser that matches either a token sequence
    with two `String` tokens or the sequence of one `String` followed by one `Integer` token looks
    something like the following:

    .. code-block:: python

        lexer_ctx = Lexing.Context(...)
        it = TokenIterator(lexer_ctx)
        parser = Match("String") + ( Match("String") | Match("Integer") )
        result = parser(it)
    """
    # TODO Move this symbol and parser stuff, incl. __str__ implementation, into the ConcatParser
    #      and AlternativeParser. They are the only real users and the current implementation yields
    #      suboptimal sphinx API documentation.
    symbol = ""  # type: str
    parsers = []  # type: List['Parser']

    def __call__(self, it: TokenIterator) -> Result:
        """Apply the parser to the specified token position.

        :param it: Iterator pointing to the start of the sequence that should be parsed.
        :returns: The result object containing either the parsed info or an error.
        """
        raise NotImplementedError

    def __add__(self, other: 'Parser') -> 'Parser':
        """Concatenate the current parser with a second one to form a larger composed parser.

        :param other: The second parser that should be matched after the current one.
        :returns: The resulting composed parser.
        """
        assert isinstance(other, Parser)
        return Concat([self, other])

    def __or__(self, other: 'Parser') -> 'Parser':
        """Use the specified parser as an alternative when the current parser fails.

        :param other: The second parser that should be matched as an alternative.
        :returns: The resulting composed parser.
        """
        assert isinstance(other, Parser)
        return Alternative([self, other])

    def __str__(self) -> str:
        """Serialize the parser (including its subparsers) into a string for debugging.

        :returns: The serialized string for the parser representation.
        """
        lines = []
        for p in self.parsers:
            if len(p.parsers) <= 1:
                lines.append(str(p))
            else:
                lines.append("({})".format(p))
        return self.symbol.join(lines)


# TODO Think about replacing the NopParser with 0 length ConcatParser or similar.
class NopParser(Parser):
    """Dummy parser that matches nothing successfully and are used as sentinel objects.
    """
    def __call__(self, it: TokenIterator) -> Result:
        return Result(it)

    def __str__(self) -> str:
        return "<*>"


class MatchParser(Parser):
    """Simple match parser that absorbs a single token given that the type and value constrains are
    fulfilled.
    """
    def __init__(self, types: List[Any], values: Optional[List[Any]], name: Optional[str]):
        """
        :param types: List of token types that can be matched by this parser.
        :param values: Optional list with values that are expected. Ignored if None is specified.
        :param name: Optional name for annotateing the token when the parsing succeeded.
        """
        self.types = types
        self.values = values
        self.res_name = name

    def __call__(self, it: TokenIterator) -> Result:
        token = it.peek()
        # consume the token if possible
        exception = it.consume(self.types, self.values)
        if exception is not None:
            return ErrorResult(exception)

        # store result if needed
        annotations = {}
        if self.res_name is not None:
            annotations[self.res_name] = token

        return Result(it, token, annotations)

    def __str__(self) -> str:
        name = ""
        if self.res_name is not None:
            name = "#" + self.res_name
        res = "<{}{}>".format("|".join([str(t) for t in self.types]), name)
        if self.values is not None and len(self.values) > 0:
            return "{}[{}]".format(res, "|".join([repr(v) for v in self.values]))
        return res


def Match(type: Any, value: Optional[Any] = None, name: Optional[str] = None) -> Parser:
    """Convenience constructor function that generates a match parser for a single
    token type and a single (optional) value.

    :param type: Token type that can be matched by this parser.
    :param value: Optional value that is expected. Ignored if not specified.
    :param name: Optional name for annotateing the token when the parsing succeeded.
    :returns: The resulting parser object.
    """
    values = None
    if value is not None:
        values = [value]
    return MatchParser([type], values, name)


def MultiMatch(types: List[Any], values: Optional[List[Any]] = None,
               name: Optional[str] = None) -> Parser:
    """Convenience alias for the MatchParser constructor.

    :param types: List of token types that can be matched by this parser.
    :param values: Optional list with values that are expected. Ignored if not specified.
    :param name: Optional name for annotateing the token when the parsing succeeded.
    :returns: The resulting parser object.
    """
    return MatchParser(types, values, name)


class ConcatParser(Parser):
    """Combinator parser that matches a concatenation of other subparsers.
    """

    symbol = " "  # type: str

    def __init__(self, parsers: List[Parser]):
        """
        :param parsers: List of parsers that should be matched consecutively.
        """
        self.parsers = []
        for p in parsers:
            self.__add__(p)

    def __add__(self, other: Parser) -> Parser:
        """Extend the current concatenation parser by adding additional subparsers.

        :param other: The second parser that should be matched after the current one.
        :returns: The resulting composed parser.
        """
        if isinstance(other, NopParser):
            return self
        if isinstance(other, ConcatParser):
            self.parsers.extend(other.parsers)
            return self
        assert isinstance(other, Parser)
        self.parsers.append(other)
        return self

    def __call__(self, it: TokenIterator) -> Result:
        annotations = {}
        parse_tree = []
        error_list = []
        for p in self.parsers:
            res = p(it)
            if res.error is not None:
                # parsers like opt can mute errors but we want to keep track to find the best match
                error_list.append(res.error)
            if not res:
                exception = extract_error(error_list)
                return ErrorResult(exception)
            it = res.next_pos
            parse_tree.append(res.parse_tree)
            annotations = overwrite_combine_dicts(annotations, res.annotations)
        return Result(it, parse_tree, annotations)


def Concat(parsers: List[Parser]) -> Parser:
    """Smart constructor function that generates a concatenation parser from a list of subparsers
    if necessary.

    :param parsers: List of parsers that should be matched consecutively.
    :returns: The resulting parser object.
    """
    parsers = [p for p in parsers if not isinstance(p, NopParser)]
    if len(parsers) == 0:
        return NopParser()
    if len(parsers) == 1:
        return parsers[0]
    return ConcatParser(parsers)


class AlternativeMatchParser(Parser):
    """Specialized combinator parser that is optimized for matching prefix-free languages.

    This parser is a mix of an :class:`.AlternativeParser` where each alternative starts with a
    unique :class:`.MatchParser`. Which concreate alternative subparser is used is decided by
    matching and consuming a signal token. The AlternativeMatchParser behaves similar to a switch
    statement without fallthrough in C where also only a single possibility is evaluated at runtime.
    Subsequently, the parser only dispatches to a single subparser and does not try to match other
    alternatives even when the selected parser fails.
    """

    def __init__(self, types: List[Any], parsers: Dict[Any, Parser],
                 res_name: Optional[str] = None):
        """
        :param types: List of token types that are valid signal tokens.
        :param parsers: Dictionary where each key represents the value of the signal token
                        and the value is the associated parser that follows the token.
        :param res_name: Optional name for annotateing the signal token when the parsing succeeded.
        """
        self.types = types
        self.parsers = parsers
        self.res_name = res_name

    def __call__(self, it: TokenIterator) -> Result:
        token = it.peek()

        # consume the token if possible
        exception = it.consume(self.types, list(self.parsers.keys()))
        if exception is not None:
            return ErrorResult(exception)

        # call the parser that is associated with the matched key
        parser = self.parsers[token.value]
        res = parser(it)
        if not res:
            return res

        # store result if needed, insert the signal token into the parse tree , and return
        if self.res_name is not None:
            res.annotations[self.res_name] = token
        res.parse_tree = [token, res.parse_tree]
        return res

    def __str__(self) -> str:
        name = ""
        if self.res_name is not None:
            name = "#" + self.res_name
        lines = []
        for k, p in self.parsers.items():
            if len(p.parsers) <= 1:
                lines.append("{}:{}".format(repr(k), p))
            else:
                lines.append("{}:({})".format(repr(k), p))
        return "<{}{}>{{{}}}".format("|".join([str(t) for t in self.types]), name, ",".join(lines))


class AlternativeParser(Parser):
    """Combinator parser that exclusively matches one of its subparsers by trying them sequentially
    until one succeeds.
    """

    symbol = "|"  # type: str

    def __init__(self, parsers: List[Parser]):
        """
        :param parsers: List of parsers that are alternatively matched.
        """
        self.parsers = parsers

    def __or__(self, other: Parser) -> Parser:
        """Extend the current alternative parser by adding additional subparsers.

        :param other: The parser that should be matched as an alternative to the current subparsers.
        :returns: The resulting composed parser.
        """
        assert isinstance(other, Parser)
        self.parsers.append(other)
        return self

    def __call__(self, it: TokenIterator) -> Result:
        error_list = []
        for p in self.parsers:
            res = p(it.copy())
            if res:
                # TODO think about returning the best error as well
                return res
            error_list.append(res.error)

        # return the error that matched the most tokens
        if len(error_list) > 0:
            exception = extract_error(error_list)
            return ErrorResult(exception)
        return Result(it)


def Alternative(parsers: List[Parser]) -> Parser:
    """Smart constructor function that generates an alternative parser from a list of subparsers
    if necessary.

    :param parsers: List of parsers that should be matched alternatively.
    :returns: The resulting parser object.
    """
    if len(parsers) == 0:
        return NopParser()
    if len(parsers) == 1:
        return parsers[0]
    return AlternativeParser(parsers)


class RepetitionParser(Parser):
    """Combinator parser that matches its subparser a configurable amount of times.
    """
    def __init__(self, parser: Parser, min_rep: int = 0, max_rep: Optional[int] = None):
        """
        :param parsers: The subparser that should be matched multiple times.
        :param min_rep: The minimum number of repetitions that are needed for a successful parse.
        :param max_rep: The maximum number of repetitions that are needed for a successful parse.
        """
        assert max_rep is None or min_rep <= max_rep
        self.parsers = [parser]
        self.min_rep = min_rep
        self.max_rep = max_rep

    def __call__(self, it: TokenIterator) -> Result:
        results = []
        res = None
        while True:
            res = self.parsers[0](it.copy())
            if res:
                results.append(res)
                it = res.next_pos
                if self.max_rep is not None and len(results) == self.max_rep:
                    break
            else:
                break
        # End of matching reached (either due to failure or because max_rep is reached).
        # Ensure that sufficiently many matches occurred.
        if len(results) < self.min_rep:
            assert not res  # res has to be an error currently given that min <= max
            return res

        # Matching was successful, combine the results.
        if len(results) == 0:
            return Result(it, error=res.error)
        elif len(results) == 1 and self.max_rep == 1:
            results[0].error = res.error
            return results[0]
        parse_tree = [r.parse_tree for r in results]
        annotations = list_combine_dicts([r.annotations for r in results])
        return Result(it, parse_tree, annotations, res.error)

    def __str__(self) -> str:
        if self.min_rep == 0 and self.max_rep == 1:
            return "{}?".format(super().__str__())
        if self.min_rep == self.max_rep:
            return "{}{{{}}}".format(super().__str__(), self.min_rep)
        if self.max_rep is not None:
            return "{}{{{},{}}}".format(super().__str__(), self.min_rep, self.max_rep)
        return "{}{{{},}}".format(super().__str__(), self.min_rep)


def Opt(parser: Parser) -> Parser:
    """Smart constructor function that generates a parser that matches either 0 or 1 times.

    :param parsers: The subparser that should be optionally matched.
    :returns: The resulting parser object.
    """
    if isinstance(parser, NopParser) or \
            (isinstance(parser, RepetitionParser) and parser.min_rep == 0 and parser.max_rep == 1):
        return parser
    return RepetitionParser(parser, max_rep=1)


def Rep(parser: Parser, min: int = 0, max: Optional[int] = None) -> Parser:
    """Convenience alias for the RepetitionParser constructor.

    :param parsers: The subparser that should be matched multiple times.
    :param min_rep: The minimum number of repetitions that are needed for a successful parse.
    :param max_rep: The maximum number of repetitions that are needed for a successful parse.
    :returns: The resulting parser object.
    """
    return RepetitionParser(parser, min, max)
