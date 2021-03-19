import re
from .iface import EnvParserInterface


class SimpleParser(EnvParserInterface):
    IDENTIFIER_CHARS = '[A-Za-z0-9_]'
    LINE_ENDS = '\n\r'

    def __init__(self, delimiter='=', value_delimiter='',
                 inline_prefix='', inline_suffix=''):
        self.delimiter = delimiter
        self.value_delimiter = value_delimiter
        self.inline_prefix = inline_prefix
        self.inline_suffix = inline_suffix

        self._regexp = re.compile(self.pattern)

    @property
    def value_chars(self):
        return fr'[^{self.value_delimiter}]' \
            if self.value_delimiter else r'.'

    @property
    def pattern(self):
        return fr"^\s*{self.inline_prefix}\s*" \
               fr"(?P<name>{self.IDENTIFIER_CHARS}+)" \
               fr"\s*{self.delimiter}\s*" \
               fr"{self.value_delimiter}?" \
               fr"(?P<value>{self.value_chars}+)" \
               fr"{self.value_delimiter}?\s*" \
               fr"{self.inline_suffix}\s*$"

    def pre_match(self, line):
        return line.strip(self.LINE_ENDS)

    def post_match(self, match):
        name, value = match['name'], match['value']
        return (name.strip(), value.strip()) \
            if not self.value_delimiter \
            else (name, value)

    def __call__(self, f, *_, **__):
        for line in f:
            m = self._regexp.match(self.pre_match(line))
            if m:
                yield self.post_match(m)
