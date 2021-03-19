from abc import abstractmethod
from typing import Match, TextIO


class EnvParserInterface:

    @property
    @abstractmethod
    def value_chars(self):
        pass  # pragma: no cover

    @property
    @abstractmethod
    def pattern(self):
        pass  # pragma: no cover

    @abstractmethod
    def pre_match(self, line: str):
        pass  # pragma: no cover

    @abstractmethod
    def post_match(self, match: Match):
        pass  # pragma: no cover

    @abstractmethod
    def __call__(self, f: TextIO, *args, **kwargs):
        pass  # pragma: no cover
