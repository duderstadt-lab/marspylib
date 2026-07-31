class YamaFormatError(Exception):
    """Raised when a .yama/Smile byte stream cannot be parsed as expected."""


class SmileFormatError(YamaFormatError):
    """Raised for malformed or unsupported Smile binary encoding."""


class UnsupportedSchemaError(YamaFormatError):
    """Raised when an archive's properties.schema predates what this reader supports."""
