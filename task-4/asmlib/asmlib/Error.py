class AsmlibError(Exception):
    pass


class AsmlibLexerBasedError(AsmlibError):
    """Base class for all error objects within asmlib that have an associated lexing contest.
       Derived errors override the message property to provide sensible error messages.
    """
    def __init__(self, message, lexer_context, location, length, msg_prefix=""):
        """
        :param str message: Message describing the exception cause.
        :param Lexing.Context lexer_context: Lexer context for pretty printing the message with
                                             location information.
        :param Lexing.Location location: The location of the lexing error.
        :param int length: The length of the annotation starting from location.
        :param str prefix: Prefix for the message. Can be used to disambiguate error texts.
        """
        super().__init__()
        self._message = message
        self._lexer_context = lexer_context
        self._location = location
        self._length = length
        self._msg_prefix = msg_prefix

    @property
    def message(self):
        """Read only property that returns the exception message.

        :rtype: str
        :returns: The exception message describing the error.
        """
        return self._message

    @property
    def lexer_context(self):
        """Read only property that returns the lexer context.

        :rtype: Lexing.Context
        :returns: The lexer context which is associated with the error.
        """
        return self._lexer_context

    @property
    def location(self):
        """Read only property that returns the source location of the error.

        :rtype: Lexing.Location
        :returns: The source location that is associated with the error.
        """
        return self._location

    @property
    def length(self):
        """Read only property that returns the length of the error annotation.

        :rtype: int
        :returns: The length of the error annotation when pretty printing the message.
        """
        return self._length

    def __str__(self):
        """Read only property that returns the pretty printed error message.

        :rtype: str
        :returns: The pretty printed error message.
        """
        return self.lexer_context.format_source_message(self.location,
                                                        self._msg_prefix + self.message,
                                                        length=self.length)

