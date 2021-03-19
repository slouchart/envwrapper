from abc import abstractmethod


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
    def post_match(self, match):
        pass  # pragma: no cover

    @abstractmethod
    def __call__(self, f, *args, **kwargs):
        pass  # pragma: no cover
