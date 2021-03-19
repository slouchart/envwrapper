from importlib import import_module
from os import environ as os_env
from ast import literal_eval
from typing import Iterable, Callable, Mapping, Optional, Any, Type, Tuple, \
    Generator, TextIO
import configparser as cfg
import json


from .parser import SimpleParser as EnvSimpleParser


from .exceptions import ConfigurationError
from .exceptions import InclusionError, ExclusionError


class EnvVar:
    """
    Wraps an OS environment variable, processes, casts its value
    """
    NO_PREFIX = ''
    NO_BUNDLE = ''
    NO_PROXY = ''
    EMPTY = ''
    TOKEN_SEP = ' '
    TRUE_STRINGS = ('1', 'true', 'yes', 'on', 'ok', 'y')
    DEFAULT_BOOL_VALUES = ('false', 'true')

    def __init__(self,
                 bundle: str = NO_BUNDLE,
                 convert: Callable = lambda t: t,
                 default: str = EMPTY,
                 include_if: str = None,
                 exclude_if: str = None,
                 prefix: str = NO_PREFIX,
                 postprocessor: Callable = None,
                 preprocessor: Callable = None,
                 proxy: str = NO_PROXY,
                 sub_cast: Callable = None
                 ):
        self._name = None
        self._prefix = prefix
        self._convert = convert
        self._postprocessor = postprocessor
        self._preprocessor = preprocessor
        self._bundle = bundle
        self._default = default
        self._include_if = include_if
        self._exclude_if = exclude_if
        self._proxy = proxy
        self._sub_cast = sub_cast

        if self._exclude_if and self._include_if\
                and self._exclude_if == self._include_if:
            raise ConfigurationError(
                'Cannot set both exclude_if and include_if '
                'to the same name for an EnvVar instance'
            )

        self._pipeline = self._make_pipeline()

    def __str__(self) -> str:
        return self.get_raw_value()

    @property
    def bundle(self):
        return self._bundle

    @property
    def convert(self):
        return self._convert

    @property
    def default(self):
        return self._default

    @property
    def exclude_if(self):
        return self._exclude_if

    @property
    def include_if(self):
        return self._include_if

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name: str):
        assert not self.name, 'EnvVar name is immutable once set'
        assert name.isupper(), 'EnvVar name must be uppercase'
        self._name = name

    @property
    def os_name(self):
        if self.prefix:
            return self.prefix + self.name

        return self.name

    @property
    def prefix(self):
        return self._prefix

    @property
    def preprocessor(self):
        return self._preprocessor

    @property
    def postprocessor(self):
        return self._postprocessor

    @property
    def proxy(self):
        if self._proxy:
            var = EnvVar(default=self.default)
            var.name = self._proxy
            return var
        else:
            return None

    @property
    def sub_cast(self):
        return self._sub_cast

    @property
    def value(self):
        return self.get_value()

    def get_raw_value(self) -> str:
        if self.proxy:
            val = self.proxy.value
        else:
            val = os_env.get(self.os_name, self.default)
        return val

    @property
    def pipeline(self):
        return self._pipeline

    def _make_pipeline(self) -> Callable:
        def init():
            return lambda t: t

        def compose(f, g):
            def h(x):
                return f(g(x))
            return h

        def iter_cast(x):
            if isinstance(x, Iterable):
                if self.convert is tuple:
                    return tuple((self.sub_cast(item) for item in x))
                elif self.convert is dict:
                    assert isinstance(x, Mapping)
                    return {k: self.sub_cast(v) for k, v in x.items()}
                else:
                    return [self.sub_cast(item) for item in x]
            else:  # pragma: nocover
                return x

        p = init()
        if self.preprocessor:
            p = compose(self.preprocessor, p)
        if self.convert:
            p = compose(self._cast, p)
        if self.postprocessor:
            p = compose(self.postprocessor, p)
        if self.sub_cast:
            p = compose(iter_cast, p)

        return p

    def get_value(self):
        return self.pipeline(self.get_raw_value())

    def _cast(self, val):
        if self.convert is bool:
            if val.lower() in self.TRUE_STRINGS:
                return True
            else:
                return False
        elif self.convert in (dict, list, tuple):
            return literal_eval(val)
        else:
            return self.convert(val)

    @staticmethod
    def import_class(fully_qualified_class_name: str):
        parts = fully_qualified_class_name.split('.')
        module_name = '.'.join(parts[:-1])
        class_name = parts[-1]
        try:
            module = import_module(module_name)
            if class_name not in module.__dict__:
                raise ImportError(
                    f"No class named '{class_name}' in module '{module_name}'"
                )

            return module.__dict__[class_name]

        except (ModuleNotFoundError, ImportError) as e:
            raise e

    @staticmethod
    def to_bytes(value) -> bytes:
        return bytes(value, encoding='utf-8')

    @staticmethod
    def tokenize(sep: str = TOKEN_SEP) -> Callable:
        def f(val):
            return val.split(sep)
        return f


class EnvWrapper:
    """In the context of engineering 12-factors applications,
    EnvWrapper is an adapter that provides a way to match two envvars
    interfaces:
    Interface 1: the list of expected envvars from os.environ
    Interface 2: the list of expected envvars by the application

    EnvWrapper allows envvars description at instance initialization,
    is largely immutable and exposes a mapping-like interface

    Thus, accessing envvars individually can be done using the 'get' method
    or by string indexing e.g env['MY_VAR']

    Moreover, each envvar can be accessed as an attribute e.g env.MY_VAR
    """

    encoder = None
    decoder = None
    DEFAULT_JSON_ENCODER = None

    def __init__(self, **env_vars):

        self._vars = {}
        self._bundles = {}

        for var_name, var_settings in env_vars.items():
            if isinstance(var_settings, dict):
                var_settings = EnvVar(var_name, **var_settings)

            assert isinstance(var_settings, EnvVar)
            var_settings.name = var_name
            self._vars[var_name] = var_settings

            if var_settings.bundle:
                self._update_bundle(var_settings)

    @property
    def vars(self):
        return self._vars.items()

    @property
    def bundles(self):
        return self._bundles.items()

    class _EnvBundle:
        def __init__(self, name: str, resolver: Callable[[str], bool]):
            self.name = name
            self._vars = dict()
            self._resolver = resolver

        def __setitem__(self, key: str, value: EnvVar):
            assert isinstance(value, EnvVar)
            self._vars[key] = value

        @property
        def vars(self):
            return self._vars.items()

        @property
        def value(self) -> dict:
            result = dict()
            for name, var in self._vars.items():
                if var.exclude_if and self._resolver(var.exclude_if):
                    continue
                if var.include_if and not self._resolver(var.include_if):
                    continue
                result[name.lower()] = var.value

            return result

    def _update_bundle(self, var: EnvVar):
        assert var.bundle
        if var.bundle not in self._bundles:
            self._bundles[var.bundle] = self._EnvBundle(
                var.bundle,
                self._resolve_include_exclude
            )

        bundle = self._bundles[var.bundle]
        bundle[var.name] = var

    def get(self, item: str, default=None):
        """returns and doesn't fail as dict.get"""
        try:
            return self._get(item, or_raise=KeyError)
        except (ConfigurationError, KeyError):
            return default

    def _build_exception(self, item: str, exc_cls: Type[Exception],
                         default_cls: Callable[[], Exception]) -> Exception:

        if not exc_cls:
            exc_cls = default_cls

        assert exc_cls

        if exc_cls is InclusionError:
            msg = f"Conditions to include variable {item} are not met"
            return exc_cls(msg)
        elif exc_cls is ExclusionError:
            msg = f"Variable {item} is explicitly excluded " \
                  f"from this configuration"
            return exc_cls(msg)
        elif exc_cls is ConfigurationError:
            msg = f"Variable {item} is not declared in this configuration"
            return exc_cls(msg)
        elif exc_cls is KeyError:
            return exc_cls(item)
        elif exc_cls is AttributeError:
            msg = f"'{type(self).__name__}' object has no attribute '{item}'"
            return exc_cls(msg)
        else:  # pragma: nocover
            msg = f"'{type(self).__name__}' raises on '{item}' lookup"
            return exc_cls(msg)

    def _get(self, item: str,
             or_raise: Optional[Type[Exception]] = None) -> Any:
        if item in self._vars:
            var = self._vars[item]
            resolver = self._resolve_include_exclude

            if var.exclude_if is not None and resolver(var.exclude_if):
                raise self._build_exception(item, or_raise, ExclusionError)
            elif var.include_if is not None and not resolver(var.include_if):
                raise self._build_exception(item, or_raise, InclusionError)
            else:
                return var.value

        elif item in self._bundles:
            return self._bundles[item].value
        elif item.isupper():
            raise self._build_exception(item, or_raise, ConfigurationError)
        else:
            raise self._build_exception(item, or_raise, AttributeError)

    def __getitem__(self, item: str) -> Any:
        """Returns or fails as dict.__getitem__"""
        return self._get(item, or_raise=KeyError)

    def __getattr__(self, item: str) -> Any:
        """Returns or fails as if item not in dir(self)"""
        return self._get(item, or_raise=AttributeError)

    def __contains__(self, item: str) -> bool:
        try:
            _ = self._get(item, or_raise=KeyError)
            return True
        except (ConfigurationError, KeyError):
            return False

    def __len__(self) -> int:
        """How many envvars are there?"""
        return len(dir(self))

    def _resolve_include_exclude(self, ref_name: str) -> bool:
        if ref_name not in self._vars:
            raise ConfigurationError(
                f'Variable {ref_name} is referenced but not declared'
            )
        return bool(self._vars[ref_name].get_value())

    def keys(self) -> Iterable[str]:
        """Provided for use by FlaskApp.Config.from_mapping"""
        return (
            k for k in set(self._vars.keys()) | set(self._bundles.keys())
            if k in self
        )

    def items(self) -> Iterable[Tuple[str, Any]]:
        """Provided for use by FlaskApp.Config.from_mapping"""
        return iter(self._items())

    def _items(self) -> Generator:
        for name in self.keys():
            if name in self._bundles:
                obj = self._bundles[name]
            else:
                assert name in self._vars
                obj = self._vars[name]

            yield obj.name, obj.value

    def collect(self) -> dict:
        """Returns a mapping of envvar as exposed by os.env, values
        are raw UTF-8 strings"""
        def on_var(d, _, var, __):
            if not var.proxy:
                d[var.os_name] = str(var)
            else:
                d[var.proxy.name] = str(var)

        serialize = self.encoder(on_var, preserve_case=True)
        return serialize(self, target=dict)

    def __dir__(self) -> Iterable[str]:
        """Provided for use by FlaskApp.Config.from_object"""
        return self.keys()

    def to_config(self, f: TextIO, preserve_case: bool = False,
                  bool_values: Tuple[str, str] = EnvVar.DEFAULT_BOOL_VALUES,
                  cls=cfg.ConfigParser,
                  **kwargs):

        def append_var_to_default_section(parser, var_name, var, val):
            if not var.bundle:
                parser[parser.default_section][var_name] = val

        def append_section(parser, section_name, _):
            if section_name not in parser.sections():
                parser.add_section(section_name)

        def append_var_to_section(parser, section_name, var_name, _, val):
            parser[section_name][var_name] = val

        encode = self.encoder(
            append_var_to_default_section,
            append_section,
            append_var_to_section,
            preserve_case=preserve_case,
            bool_values=bool_values)
        config = encode(self, target=cls, **kwargs)
        config.write(f)

    def to_json(self, f: TextIO, preserve_case: bool = False, **kwargs):
        return json.dump(self, f, cls=self.DEFAULT_JSON_ENCODER,
                         preserve_case=preserve_case, **kwargs)

    def to_source_file(self, f: TextIO, sort_keys: bool = False,
                       space_around_delimiters: bool = False,
                       delimiter: str = '=',
                       value_delimiter: str = '',
                       inline_prefix: str = '',
                       inline_suffix: str = ''):
        items = self.collect()
        keys = sorted(items.keys()) if sort_keys else items.keys()

        def expression_builder(var, value):

            operator = fr' {delimiter} ' \
                       if space_around_delimiters \
                       else delimiter
            value = value_delimiter + value + value_delimiter

            expr = inline_prefix + r' ' + var if inline_prefix else var
            expr += operator
            expr += value
            expr = expr + inline_suffix if inline_suffix else expr
            return expr

        for name in keys:
            f.write(f"{expression_builder(name, items[name])}\n")

    @classmethod
    def from_source_file(
            cls, f: TextIO,
            bool_values: Tuple[str, str] = EnvVar.DEFAULT_BOOL_VALUES,
            parser=None, **kwargs):

        parser = parser or EnvSimpleParser
        parse = parser(**kwargs)
        decode = cls.decoder(bool_values=bool_values)

        return decode(parse(f), ())

    @classmethod
    def from_json(cls, f: TextIO, *,
                  decoder=None, object_hook=None,
                  parse_float=None,
                  parse_int=None,
                  parse_constant=None,
                  object_pairs_hook=None, **kwargs):
        d = json.load(f, cls=decoder, object_hook=object_hook,
                      parse_float=parse_float, parse_int=parse_int,
                      parse_constant=parse_constant,
                      object_pairs_hook=object_pairs_hook, **kwargs)
        decode = cls.decoder(
            bool_values=EnvVar.DEFAULT_BOOL_VALUES)

        variables = ((k, v) for k, v in d.items() if not isinstance(v, dict))

        def bundles():
            for k, v in d.items():
                if isinstance(v, dict):
                    for var, val in v.items():
                        yield k, var, val

        return decode(variables, bundles())

    @classmethod
    def from_config(cls, f: TextIO,
                    bool_values: Tuple[str, str] = EnvVar.DEFAULT_BOOL_VALUES,
                    parser_cls=cfg.ConfigParser, **kwargs):
        parser = parser_cls(**kwargs)
        parser.read_file(f)

        decode = cls.decoder(bool_values=bool_values)

        variables = (
            (var, parser[parser.default_section][var])
            for var in parser[parser.default_section]
        )

        def bundles():
            for section in parser.sections():
                for var in parser[section]:
                    val = parser[section][var]
                    yield section, var, val

        return decode(variables, bundles())
