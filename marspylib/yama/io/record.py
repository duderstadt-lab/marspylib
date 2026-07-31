"""Base record fields shared by every Molecule and MarsMetadata record,
transcribed from AbstractMarsRecord.createIOMaps (molecule/AbstractMarsRecord.java)
in its exact write order: uid, type (write-only), notes, tags, parameters,
regionsOfInterest, positionsOfInterest.
"""

from __future__ import annotations

from ..model import MarsPosition, MarsRegion
from ..smile.reader import SmileReader, SmileToken
from ..smile.writer import SmileWriter
from .fields import FieldSpec


# -- MarsRegion / MarsPosition (util/MarsRegion.java, util/MarsPosition.java) -

def write_region(writer: SmileWriter, region: MarsRegion) -> None:
    writer.write_start_object()
    writer.write_field_name("name"); writer.write_string(region.name)
    writer.write_field_name("column"); writer.write_string(region.column)
    writer.write_field_name("start"); writer.write_number(region.start)
    writer.write_field_name("end"); writer.write_number(region.end)
    writer.write_field_name("color"); writer.write_string(region.color)
    writer.write_field_name("opacity"); writer.write_number(region.opacity)
    writer.write_end_object()


def read_region(reader: SmileReader) -> MarsRegion:
    """Assumes the region's START_OBJECT token has already been consumed."""
    region = MarsRegion()
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            return region
        name = reader.current_name()
        reader.next_token()
        if name == "name":
            region.name = reader.get_text()
        elif name == "column":
            region.column = reader.get_text()
        elif name == "start":
            region.start = reader.get_double()
        elif name == "end":
            region.end = reader.get_double()
        elif name == "color":
            region.color = reader.get_text()
        elif name == "opacity":
            region.opacity = reader.get_double()
        else:
            reader.skip_value()


def write_position(writer: SmileWriter, position: MarsPosition) -> None:
    writer.write_start_object()
    writer.write_field_name("name"); writer.write_string(position.name)
    writer.write_field_name("column"); writer.write_string(position.column)
    writer.write_field_name("position"); writer.write_number(position.position)
    writer.write_field_name("color"); writer.write_string(position.color)
    writer.write_field_name("stroke"); writer.write_number(position.stroke)
    writer.write_end_object()


def read_position(reader: SmileReader) -> MarsPosition:
    """Assumes the position's START_OBJECT token has already been consumed."""
    position = MarsPosition()
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            return position
        name = reader.current_name()
        reader.next_token()
        if name == "name":
            position.name = reader.get_text()
        elif name == "column":
            position.column = reader.get_text()
        elif name == "position":
            position.position = reader.get_double()
        elif name == "color":
            position.color = reader.get_text()
        elif name == "stroke":
            position.stroke = reader.get_double()
        else:
            reader.skip_value()


# -- parameters (typed: number/string/boolean; NaN/Infinity round-trips as a
#    native Smile double token, but the reader also tolerates the JSON-text
#    "NaN"/"Infinity"/"-Infinity" string convention defensively) -------------

def _write_parameters(writer: SmileWriter, obj) -> None:
    if not obj.parameters:
        return
    writer.write_field_name("parameters")
    writer.write_start_array()
    for name, value in obj.parameters.items():
        writer.write_start_object()
        writer.write_field_name("name"); writer.write_string(name)
        if isinstance(value, bool):
            writer.write_field_name("type"); writer.write_string("boolean")
            writer.write_field_name("value"); writer.write_bool(value)
        elif isinstance(value, str):
            writer.write_field_name("type"); writer.write_string("string")
            writer.write_field_name("value"); writer.write_string(value)
        elif isinstance(value, (int, float)):
            writer.write_field_name("type"); writer.write_string("number")
            writer.write_field_name("value"); writer.write_number(float(value))
        else:
            raise TypeError(f"unsupported parameter value type for {name!r}: {type(value)!r}")
        writer.write_end_object()
    writer.write_end_array()


def _read_parameters(reader: SmileReader, obj) -> None:
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return
        name, ptype, value = None, None, None
        while True:
            tok2 = reader.next_token()
            if tok2 == SmileToken.END_OBJECT:
                break
            field = reader.current_name()
            value_tok = reader.next_token()
            if field == "name":
                name = reader.get_text()
            elif field == "type":
                ptype = reader.get_text()
            elif field == "value":
                if ptype == "number":
                    if value_tok == SmileToken.VALUE_STRING:
                        text = reader.get_text()
                        value = {"Infinity": float("inf"), "-Infinity": float("-inf"),
                                 "NaN": float("nan")}.get(text)
                    elif value_tok == SmileToken.VALUE_INT:
                        value = float(reader.get_int())
                    else:
                        value = reader.get_double()
                elif ptype == "string":
                    value = reader.get_text()
                elif ptype == "boolean":
                    value = value_tok == SmileToken.VALUE_TRUE
        if name is not None:
            obj.parameters[name] = value


# -- tags ---------------------------------------------------------------

def _write_tags(writer: SmileWriter, obj) -> None:
    if not obj.tags:
        return
    writer.write_field_name("tags")
    writer.write_start_array()
    for tag in obj.tags:
        writer.write_string(tag)
    writer.write_end_array()


def _read_tags(reader: SmileReader, obj) -> None:
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return
        obj.tags.append(reader.get_text())


# -- regionsOfInterest / positionsOfInterest -----------------------------

def _write_regions(writer: SmileWriter, obj) -> None:
    if not obj.regions:
        return
    writer.write_field_name("regionsOfInterest")
    writer.write_start_array()
    for region in obj.regions.values():
        write_region(writer, region)
    writer.write_end_array()


def _read_regions(reader: SmileReader, obj) -> None:
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return
        region = read_region(reader)
        obj.regions[region.name] = region


def _write_positions(writer: SmileWriter, obj) -> None:
    if not obj.positions:
        return
    writer.write_field_name("positionsOfInterest")
    writer.write_start_array()
    for position in obj.positions.values():
        write_position(writer, position)
    writer.write_end_array()


def _read_positions(reader: SmileReader, obj) -> None:
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return
        position = read_position(reader)
        obj.positions[position.name] = position


# -- base field table ------------------------------------------------------

def _write_uid(writer, obj):
    writer.write_field_name("uid")
    writer.write_string(obj.uid)


def _read_uid(reader, obj):
    obj.uid = reader.get_text()


def _write_notes(writer, obj):
    if obj.notes is not None:
        writer.write_field_name("notes")
        writer.write_string(obj.notes)


def _read_notes(reader, obj):
    obj.notes = reader.get_text()


def make_type_field(type_fqcn: str) -> FieldSpec:
    """The "type" field is write-only in mars-core (never consumed on read --
    the concrete record class is instead determined by which archive/factory
    produced it), so this only needs an encode side."""
    def encode(writer, obj):
        writer.write_field_name("type")
        writer.write_string(type_fqcn)
    return FieldSpec("type", encode, None)


def base_record_fields(type_fqcn: str) -> list[FieldSpec]:
    return [
        FieldSpec("uid", _write_uid, _read_uid),
        make_type_field(type_fqcn),
        FieldSpec("notes", _write_notes, _read_notes),
        FieldSpec("tags", _write_tags, _read_tags),
        FieldSpec("parameters", _write_parameters, _read_parameters),
        FieldSpec("regionsOfInterest", _write_regions, _read_regions),
        FieldSpec("positionsOfInterest", _write_positions, _read_positions),
    ]
