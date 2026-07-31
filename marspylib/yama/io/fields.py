"""Generic ordered field-table plumbing shared by every record type.

Each Mars record type (Properties, MarsMetadata, Molecule, ...) is described
by an ordered list of FieldSpec entries transcribed 1:1 from the matching
Java `createIOMaps()` method's call order. Both the reader and the writer
consume the *same* list, so field order and presence can never drift between
read and write -- fixing an order bug is a one-line change in one place.

This mirrors Jackson's `setJsonField(name, jGenerator -> ..., jParser -> ...)`
pattern: `encode(writer, obj)` writes the field (and is expected to skip
writing anything at all when the value is empty/default, exactly matching
each Java `if (x.size() > 0) {...}` guard), and `decode(reader, obj)` is
invoked with the reader already positioned at the field's value token (i.e.
the FIELD_NAME token has already been consumed and next_token() has already
been called once to advance onto the value) and mutates `obj` in place.
`decode=None` marks a write-only field (matches Java's `null` input lambda,
e.g. the "type" discriminator fields that are written but never read back).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..errors import YamaFormatError
from ..smile.reader import SmileReader, SmileToken
from ..smile.writer import SmileWriter


@dataclass
class FieldSpec:
    name: str
    encode: Callable[[SmileWriter, Any], None] | None
    decode: Callable[[SmileReader, Any], None] | None


def write_record(writer: SmileWriter, obj: Any, schema: list[FieldSpec]) -> None:
    writer.write_start_object()
    for spec in schema:
        if spec.encode is not None:
            spec.encode(writer, obj)
    writer.write_end_object()


def read_record(reader: SmileReader, obj: Any, schema: list[FieldSpec]) -> None:
    """Reads field/value pairs until END_OBJECT. Assumes the matching
    START_OBJECT token has already been consumed by the caller."""
    by_name = {spec.name: spec for spec in schema if spec.decode is not None}
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            return
        if tok != SmileToken.FIELD_NAME:
            raise YamaFormatError(f"expected FIELD_NAME or END_OBJECT, got {tok}")
        name = reader.current_name()
        reader.next_token()  # advance onto the value token
        spec = by_name.get(name)
        if spec is not None:
            spec.decode(reader, obj)
        else:
            reader.skip_value()
