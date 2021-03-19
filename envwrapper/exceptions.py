class ConfigurationError(Exception):
    pass


class ExclusionError(ConfigurationError):
    pass


class InclusionError(ConfigurationError):
    pass
