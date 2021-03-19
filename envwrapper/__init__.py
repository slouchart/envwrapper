from .base import EnvWrapper
from .base import EnvVar  # noqa: F401
from .codecs import EnvWrapperJSONEncoder
from .codecs import EnvWrapperEncoder, EnvWrapperDecoder
from .exceptions import ConfigurationError  # noqa: F401


EnvWrapper.encoder = EnvWrapperEncoder
EnvWrapper.decoder = EnvWrapperDecoder
EnvWrapper.DEFAULT_JSON_ENCODER = EnvWrapperJSONEncoder
