"""MartianObject's extra "shapes" field (a PeakShape polygon per timepoint),
used by ObjectArchive (mars-core's `object` package). Transcribed from
object/MartianObject.java:100-135 and image/PeakShape.java:227-255.
"""

from __future__ import annotations

from ..model import PeakShape
from ..smile.reader import SmileReader, SmileToken
from ..smile.writer import SmileWriter
from .fields import FieldSpec

OBJECT_ARCHIVE_TYPE = "de.mpg.biochem.mars.object.ObjectArchive"


def _write_double_array(writer: SmileWriter, values: list[float]) -> None:
    writer.write_start_array()
    for v in values:
        writer.write_number(v)
    writer.write_end_array()


def _read_double_array(reader: SmileReader) -> list[float]:
    values = []
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return values
        values.append(reader.get_double())


def write_peak_shape(writer: SmileWriter, shape: PeakShape) -> None:
    writer.write_start_object()
    writer.write_field_name("vertices")
    writer.write_int(len(shape.x))
    writer.write_field_name("x")
    _write_double_array(writer, shape.x)
    writer.write_field_name("y")
    _write_double_array(writer, shape.y)
    writer.write_end_object()


def read_peak_shape(reader: SmileReader) -> PeakShape:
    """Assumes the shape's START_OBJECT token has already been consumed."""
    shape = PeakShape()
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            return shape
        name = reader.current_name()
        reader.next_token()
        if name == "x":
            shape.x = _read_double_array(reader)
        elif name == "y":
            shape.y = _read_double_array(reader)
        else:
            # "vertices" is just len(x)/len(y), redundant once both arrays
            # are read -- and anything else is passed through generically.
            reader.skip_value()


def _write_shapes(writer: SmileWriter, obj) -> None:
    if not obj.shapes:
        return
    writer.write_field_name("shapes")
    writer.write_start_array()
    for t, shape in obj.shapes.items():
        writer.write_start_object()
        writer.write_field_name("t")
        writer.write_int(t)
        writer.write_field_name("shape")
        write_peak_shape(writer, shape)
        writer.write_end_object()
    writer.write_end_array()


def _read_shapes(reader: SmileReader, obj) -> None:
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return
        t, shape = None, None
        while True:
            tok2 = reader.next_token()
            if tok2 == SmileToken.END_OBJECT:
                break
            field_name = reader.current_name()
            reader.next_token()
            if field_name == "t":
                t = reader.get_int()
            elif field_name == "shape":
                shape = read_peak_shape(reader)
            else:
                reader.skip_value()
        if t is not None and shape is not None:
            obj.shapes[t] = shape


SHAPES_FIELD = FieldSpec("shapes", _write_shapes, _read_shapes)
EXTRA_FIELDS = [SHAPES_FIELD]
