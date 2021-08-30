class RootException(Exception):
    def __init__(self, *args, params: dict = None) -> None:
        self.params = params
        super().__init__(*args)

    def __str__(self) -> str:
        return f"""{super().__str__()}, params:  {self.params}"""

    def __repr__(self) -> str:
        return self.__str__()


class PriceOutOfRange(RootException):
    pass


class UnrecognizedQuote(RootException):
    pass


class NotEnoughQuoteBalance(RootException):
    pass


class QuoteAmountTooLow(RootException):
    pass


class OrderFailed(RootException):
    pass


class NotEnoughPerms(RootException):
    pass
