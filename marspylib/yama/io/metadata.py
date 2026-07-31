"""MarsMetadata fields, transcribed from AbstractMarsMetadata.createIOMaps
(metadata/AbstractMarsMetadata.java:145-224): microscope, sourceDirectory,
log, bdvSources, images, appended after the shared base record fields.
`images` is kept as a schema-opaque generic tree (MarsOMEImage is a large
OME structure and modeling it isn't the point of this port) and, unlike
every other array field here, is written unconditionally even when empty.
"""

from __future__ import annotations

from ..model import METADATA_TYPE_FQCN, MarsBdvSource, MarsMetadata
from ..smile.reader import SmileReader, SmileToken, read_generic_value
from ..smile.writer import SmileWriter, write_generic_value
from .fields import FieldSpec, read_record, write_record
from .record import base_record_fields


def _write_microscope(writer: SmileWriter, obj: MarsMetadata) -> None:
    if obj.microscope is not None:
        writer.write_field_name("microscope")
        writer.write_string(obj.microscope)


def _read_microscope(reader: SmileReader, obj: MarsMetadata) -> None:
    obj.microscope = reader.get_text()


def _write_source_directory(writer: SmileWriter, obj: MarsMetadata) -> None:
    if obj.source_directory is not None:
        writer.write_field_name("sourceDirectory")
        writer.write_string(obj.source_directory)


def _read_source_directory(reader: SmileReader, obj: MarsMetadata) -> None:
    obj.source_directory = reader.get_text()


def _write_log(writer: SmileWriter, obj: MarsMetadata) -> None:
    if obj.log != "":
        writer.write_field_name("log")
        writer.write_string(obj.log)


def _read_log(reader: SmileReader, obj: MarsMetadata) -> None:
    obj.log = reader.get_text()


def write_bdv_source(writer: SmileWriter, source: MarsBdvSource) -> None:
    writer.write_start_object()
    writer.write_field_name("name"); writer.write_string(source.name)
    writer.write_field_name("isN5"); writer.write_bool(source.is_n5)
    writer.write_field_name("driftCorrect"); writer.write_bool(source.drift_correct)
    writer.write_field_name("path"); writer.write_string(source.path)
    writer.write_field_name("dataset"); writer.write_string(source.dataset)
    writer.write_field_name("channel"); writer.write_int(source.channel)
    writer.write_field_name("singleTimePointMode"); writer.write_bool(source.single_time_point_mode)
    writer.write_field_name("singleTimePoint"); writer.write_int(source.single_time_point)
    writer.write_field_name("affineTransform3D")
    writer.write_start_array()
    for v in source.affine_transform:
        writer.write_number(v)
    writer.write_end_array()
    if source.properties:
        writer.write_field_name("properties")
        writer.write_start_object()
        for key, value in source.properties.items():
            writer.write_field_name(key)
            writer.write_string(value)
        writer.write_end_object()
    writer.write_end_object()


def read_bdv_source(reader: SmileReader) -> MarsBdvSource:
    """Assumes the source's START_OBJECT token has already been consumed."""
    source = MarsBdvSource()
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            return source
        name = reader.current_name()
        value_tok = reader.next_token()
        if name == "name":
            source.name = reader.get_text()
        elif name == "isN5":
            source.is_n5 = value_tok == SmileToken.VALUE_TRUE
        elif name == "driftCorrect":
            source.drift_correct = value_tok == SmileToken.VALUE_TRUE
        elif name == "path":
            source.path = reader.get_text()
        elif name == "dataset":
            source.dataset = reader.get_text()
        elif name == "channel":
            source.channel = reader.get_int()
        elif name == "singleTimePointMode":
            source.single_time_point_mode = value_tok == SmileToken.VALUE_TRUE
        elif name == "singleTimePoint":
            source.single_time_point = reader.get_int()
        elif name == "affineTransform3D":
            values = []
            while True:
                tok2 = reader.next_token()
                if tok2 == SmileToken.END_ARRAY:
                    break
                values.append(reader.get_double())
            source.affine_transform = tuple(values)
        elif name == "properties":
            props = {}
            while True:
                tok2 = reader.next_token()
                if tok2 == SmileToken.END_OBJECT:
                    break
                key = reader.current_name()
                reader.next_token()
                props[key] = reader.get_text()
            source.properties = props
        else:
            reader.skip_value()


def _write_bdv_sources(writer: SmileWriter, obj: MarsMetadata) -> None:
    if not obj.bdv_sources:
        return
    writer.write_field_name("bdvSources")
    writer.write_start_array()
    for source in obj.bdv_sources.values():
        write_bdv_source(writer, source)
    writer.write_end_array()


def _read_bdv_sources(reader: SmileReader, obj: MarsMetadata) -> None:
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return
        source = read_bdv_source(reader)
        obj.bdv_sources[source.name] = source


def _write_images(writer: SmileWriter, obj: MarsMetadata) -> None:
    writer.write_field_name("images")
    writer.write_start_array()
    for image in obj.images:
        write_generic_value(writer, image)
    writer.write_end_array()


def _read_images(reader: SmileReader, obj: MarsMetadata) -> None:
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return
        obj.images.append(read_generic_value(reader, tok))


METADATA_FIELDS: list[FieldSpec] = base_record_fields(METADATA_TYPE_FQCN) + [
    FieldSpec("microscope", _write_microscope, _read_microscope),
    FieldSpec("sourceDirectory", _write_source_directory, _read_source_directory),
    FieldSpec("log", _write_log, _read_log),
    FieldSpec("bdvSources", _write_bdv_sources, _read_bdv_sources),
    FieldSpec("images", _write_images, _read_images),
]


def write_metadata(writer: SmileWriter, metadata: MarsMetadata) -> None:
    write_record(writer, metadata, METADATA_FIELDS)


def read_metadata(reader: SmileReader) -> MarsMetadata:
    metadata = MarsMetadata()
    read_record(reader, metadata, METADATA_FIELDS)
    return metadata
