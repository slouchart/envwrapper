from typing import Any, Callable, Mapping, Tuple, Iterable
from .base import EnvWrapper, EnvVar, BoolValuesType
import json


class EnvWrapperDecoder:

    OnProcessedCallbackType = Callable[[str, str, str], None]

    def __init__(self,
                 bool_values: BoolValuesType = EnvVar.DEFAULT_BOOL_VALUES,
                 on_processed: OnProcessedCallbackType = None):
        self.bool_values = bool_values
        self.variables = dict()
        self.on_processed = on_processed or self.process_variable

    def process_variable(self,
                         name: str, value: str, bundle: str = '') -> None:
        if value in self.bool_values:
            convert = bool
        else:
            # best effort to find a suitable type cast for numerical values
            try:
                _ = int(value)
                convert = int
            except ValueError:
                try:
                    _ = float(value)
                    convert = float
                except ValueError:
                    convert = str

        self.variables[name.upper()] = EnvVar(
            default=value,
            convert=convert,
            bundle=bundle.upper()
        )

    def __call__(self, variables: Iterable[Tuple[str, str]],
                 bundles: Iterable[Tuple[str, str, str]]) -> EnvWrapper:
        for var, val in variables:
            self.on_processed(var, val, '')

        for bundle, var, val in bundles:
            self.on_processed(var, val, bundle)

        return EnvWrapper(**self.variables)


class EnvWrapperEncoder:

    OnVariableCallbackType = Callable[[Any, str, EnvVar, Any], None]
    OnBundleCallbackType = Callable[[Any, str, Mapping], None]
    OnBundledVariableCallbackType = Callable[[Any, str, str, EnvVar], None]

    def __init__(self,
                 on_variable_cb: OnVariableCallbackType = None,
                 on_bundle_cb: OnBundleCallbackType = None,
                 on_bundled_variable_cb: OnBundledVariableCallbackType = None,
                 preserve_case: bool = False,
                 bool_values: BoolValuesType = EnvVar.DEFAULT_BOOL_VALUES):

        self._on_variable_callback = on_variable_cb
        self._on_bundle_callback = on_bundle_cb
        self._on_bundled_variable_callback = on_bundled_variable_cb
        self.preserve_case = preserve_case
        self.bool_values = bool_values

    def convert_bool_string(self, var: EnvVar) -> str:
        if var.convert is bool:
            return self.bool_values[int(var.get_value())]
        else:
            return var.get_raw_value()

    def ensure_case(self, name: str) -> str:
        return name if self.preserve_case else name.lower()

    @property
    def on_variable(self) -> OnVariableCallbackType:
        return self._on_variable_callback

    @property
    def on_bundle(self) -> OnBundleCallbackType:
        return self._on_bundle_callback

    @property
    def on_bundled_variable(self) -> OnBundledVariableCallbackType:
        return self._on_bundled_variable_callback

    def __call__(self, source: EnvWrapper, target, *args, **kwargs):

        if callable(target):
            target = target(*args, **kwargs)

        if self.on_variable:
            for name, var in source.vars:
                self.on_variable(target, self.ensure_case(name), var,
                                 self.convert_bool_string(var))

        if self.on_bundle:
            for name, bundle in source.bundles:
                self.on_bundle(target, self.ensure_case(name), bundle)
                if self.on_bundled_variable:
                    for var_name, var in bundle.vars:
                        self.on_bundled_variable(
                            target,
                            self.ensure_case(name),
                            self.ensure_case(var_name),
                            var, self.convert_bool_string(var)
                        )
        return target


class EnvWrapperJSONEncoder(json.JSONEncoder):

    def __init__(self, *, preserve_case: bool = False, **kw):
        super().__init__(**kw)
        self.preserve_case = preserve_case

    def default(self, env):
        if isinstance(env, EnvWrapper):

            def on_variable(d, name, var, val):
                if not var.bundle:
                    d[name] = val

            def on_bundle(d, name, _):
                if name not in d:
                    d[name] = dict()

            def on_bundled_var(d, bundle_name, var_name, _, val):
                d[bundle_name][var_name] = val

            encode = EnvWrapperEncoder(
                on_variable, on_bundle, on_bundled_var,
                preserve_case=self.preserve_case,
                bool_values=EnvVar.DEFAULT_BOOL_VALUES
            )

            return encode(env, target=dict)

        else:  # pragma: nocover
            return super().default(env)
