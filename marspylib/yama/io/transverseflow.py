"""TransverseFlowMolecule's extra "replicationForkShapes" field (a
ReplicationForkShape per timepoint), used by TransverseFlowArchive (the
separate mars-transverseflow module, not mars-core itself). Transcribed
from TransverseFlowMolecule.java:99-134 and ReplicationForkShape.java:184-395.
"""

from __future__ import annotations

from ..model import ReplicationForkShape
from ..smile.reader import SmileReader, SmileToken
from ..smile.writer import SmileWriter
from .fields import FieldSpec

TRANSVERSE_FLOW_ARCHIVE_TYPE = "de.mpg.biochem.mars.transverseflow.TransverseFlowArchive"


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


def _write_intensity_map(writer: SmileWriter, field_name: str,
                          intensity: dict[str, dict[int, float]], coord_field: str) -> None:
    if not intensity:
        return
    writer.write_field_name(field_name)
    writer.write_start_array()
    for source, coords in intensity.items():
        for coord, value in coords.items():
            writer.write_start_object()
            writer.write_field_name("source")
            writer.write_string(source)
            writer.write_field_name(coord_field)
            writer.write_int(coord)
            writer.write_field_name("intensity")
            writer.write_number(value)
            writer.write_end_object()
    writer.write_end_array()


def _read_intensity_map(reader: SmileReader, coord_field: str) -> dict[str, dict[int, float]]:
    result: dict[str, dict[int, float]] = {}
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return result
        source, coord, value = None, None, None
        while True:
            tok2 = reader.next_token()
            if tok2 == SmileToken.END_OBJECT:
                break
            field_name = reader.current_name()
            reader.next_token()
            if field_name == "source":
                source = reader.get_text()
            elif field_name == coord_field:
                coord = reader.get_int()
            elif field_name == "intensity":
                value = reader.get_double()
            else:
                reader.skip_value()
        if source is not None and coord is not None and value is not None:
            result.setdefault(source, {})[coord] = value


def write_replication_fork_shape(writer: SmileWriter, shape: ReplicationForkShape) -> None:
    writer.write_start_object()

    writer.write_field_name("parentalPoints")
    writer.write_int(len(shape.parental_x))
    writer.write_field_name("parentalX")
    _write_double_array(writer, shape.parental_x)
    writer.write_field_name("parentalY")
    _write_double_array(writer, shape.parental_y)
    _write_intensity_map(writer, "parentalIntensity", shape.parental_intensity, "x")

    writer.write_field_name("leadingPoints")
    writer.write_int(len(shape.leading_x))
    writer.write_field_name("leadingX")
    _write_double_array(writer, shape.leading_x)
    writer.write_field_name("leadingY")
    _write_double_array(writer, shape.leading_y)
    _write_intensity_map(writer, "leadingIntensity", shape.leading_intensity, "x")

    writer.write_field_name("laggingPoints")
    writer.write_int(len(shape.lagging_x))
    writer.write_field_name("laggingX")
    _write_double_array(writer, shape.lagging_x)
    writer.write_field_name("laggingY")
    _write_double_array(writer, shape.lagging_y)
    # Real Java quirk, not a bug: lagging (unlike parental/leading) keys its
    # intensity samples by "y" rather than "x" -- replicated exactly.
    _write_intensity_map(writer, "laggingIntensity", shape.lagging_intensity, "y")

    writer.write_end_object()


def read_replication_fork_shape(reader: SmileReader) -> ReplicationForkShape:
    """Assumes the shape's START_OBJECT token has already been consumed."""
    shape = ReplicationForkShape()
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            return shape
        name = reader.current_name()
        reader.next_token()
        if name == "parentalX":
            shape.parental_x = _read_double_array(reader)
        elif name == "parentalY":
            shape.parental_y = _read_double_array(reader)
        elif name == "parentalIntensity":
            shape.parental_intensity = _read_intensity_map(reader, "x")
        elif name == "leadingX":
            shape.leading_x = _read_double_array(reader)
        elif name == "leadingY":
            shape.leading_y = _read_double_array(reader)
        elif name == "leadingIntensity":
            shape.leading_intensity = _read_intensity_map(reader, "x")
        elif name == "laggingX":
            shape.lagging_x = _read_double_array(reader)
        elif name == "laggingY":
            shape.lagging_y = _read_double_array(reader)
        elif name == "laggingIntensity":
            shape.lagging_intensity = _read_intensity_map(reader, "y")
        else:
            # "parentalPoints"/"leadingPoints"/"laggingPoints" are just
            # len(x)/len(y), redundant once the arrays themselves are read.
            reader.skip_value()


def _write_shapes(writer: SmileWriter, obj) -> None:
    if not obj.replication_fork_shapes:
        return
    writer.write_field_name("replicationForkShapes")
    writer.write_start_array()
    for t, shape in obj.replication_fork_shapes.items():
        writer.write_start_object()
        writer.write_field_name("t")
        writer.write_int(t)
        writer.write_field_name("replicationForkShape")
        write_replication_fork_shape(writer, shape)
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
            elif field_name == "replicationForkShape":
                shape = read_replication_fork_shape(reader)
            else:
                reader.skip_value()
        if t is not None and shape is not None:
            obj.replication_fork_shapes[t] = shape


REPLICATION_FORK_SHAPES_FIELD = FieldSpec("replicationForkShapes", _write_shapes, _read_shapes)
EXTRA_FIELDS = [REPLICATION_FORK_SHAPES_FIELD]
