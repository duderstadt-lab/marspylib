"""Top-level MoleculeArchiveProperties fields, transcribed from
AbstractMoleculeArchiveProperties.createIOMaps
(molecule/AbstractMoleculeArchiveProperties.java:120-259), in exact write
order: archiveType, type (both write-only), schema, numberOfMolecules,
numberOfMetadata, moleculeTableColumnSet, moleculeSegmentTableNames,
moleculeTagSet, moleculeChannelSet, moleculeParameterSet, moleculeRegionSet,
moleculePositionSet, documents.

Legacy backward-compatibility aliases (Schema, MoleculeDataTableColumnSet,
MoleculeTagSet, MoleculeParameterSet, numImageMetaData, comments, ...) exist
in mars-core purely to parse pre-2022-04-11-schema archives; per this port's
scoped-out legacy support, they are intentionally not implemented here.
"""

from __future__ import annotations

from ..errors import UnsupportedSchemaError
from ..model import CURRENT_SCHEMA, MarsDocument, Properties
from ..smile.reader import SmileReader, SmileToken
from ..smile.writer import SmileWriter
from .fields import FieldSpec, read_record, write_record


def write_document(writer: SmileWriter, document: MarsDocument) -> None:
    writer.write_start_object()
    writer.write_field_name("name"); writer.write_string(document.name)
    writer.write_field_name("content"); writer.write_string(document.content)
    if document.media:
        writer.write_field_name("media")
        writer.write_start_object()
        for key, value in document.media.items():
            writer.write_field_name(key)
            writer.write_string(value)
        writer.write_end_object()
    if document.media_array:
        writer.write_field_name("mediaArray")
        writer.write_start_object()
        for key, values in document.media_array.items():
            writer.write_field_name("id"); writer.write_string(key)
            writer.write_field_name("value")
            writer.write_start_array()
            for v in values:
                writer.write_string(v)
            writer.write_end_array()
        writer.write_end_object()
    writer.write_end_object()


def read_document(reader: SmileReader) -> MarsDocument:
    """Assumes the document's START_OBJECT token has already been consumed."""
    document = MarsDocument()
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            return document
        name = reader.current_name()
        if name == "name":
            reader.next_token()
            document.name = reader.get_text()
        elif name == "content":
            reader.next_token()
            document.content = reader.get_text()
        elif name == "media":
            reader.next_token()  # START_OBJECT
            while True:
                tok2 = reader.next_token()
                if tok2 == SmileToken.END_OBJECT:
                    break
                key = reader.current_name()
                reader.next_token()
                document.media[key] = reader.get_text()
        elif name == "mediaArray":
            reader.next_token()  # START_OBJECT
            current_id = None
            while True:
                tok2 = reader.next_token()
                if tok2 == SmileToken.END_OBJECT:
                    break
                field_name = reader.current_name()
                if field_name == "id":
                    reader.next_token()
                    current_id = reader.get_text()
                elif field_name == "value":
                    reader.next_token()  # START_ARRAY
                    values = []
                    while True:
                        tok3 = reader.next_token()
                        if tok3 == SmileToken.END_ARRAY:
                            break
                        values.append(reader.get_text())
                    if current_id is not None:
                        document.media_array[current_id] = values
        else:
            reader.next_token()
            reader.skip_value()


def _write_archive_type(writer: SmileWriter, obj: Properties) -> None:
    writer.write_field_name("archiveType")
    writer.write_string(obj.archive_type)


def _read_archive_type(reader: SmileReader, obj: Properties) -> None:
    # mars-core treats this field as write-only -- Fiji determines the
    # concrete archive class via a separate raw pre-scan of the file *before*
    # deserializing, so AbstractMoleculeArchiveProperties never reads it back.
    # This port has no such pre-scan (Molecule/MarsMetadata are unified
    # dataclasses dispatched purely from Properties.archive_type), so this
    # field must actually be read here to know which archive type was opened.
    obj.archive_type = reader.get_text()


def _write_type(writer: SmileWriter, obj: Properties) -> None:
    writer.write_field_name("type")
    writer.write_string(obj.archive_type + "Properties")


def _write_schema(writer: SmileWriter, obj: Properties) -> None:
    writer.write_field_name("schema")
    writer.write_string(CURRENT_SCHEMA)


def _read_schema(reader: SmileReader, obj: Properties) -> None:
    obj.schema = reader.get_text()
    if not obj.schema or obj.schema < CURRENT_SCHEMA:
        raise UnsupportedSchemaError(
            f"archive schema {obj.schema!r} predates {CURRENT_SCHEMA!r}; "
            "opening older (pre-OME-metadata) archives is not supported"
        )


def _write_number_of_molecules(writer: SmileWriter, obj: Properties) -> None:
    writer.write_field_name("numberOfMolecules")
    writer.write_int(obj.number_of_molecules)


def _read_number_of_molecules(reader: SmileReader, obj: Properties) -> None:
    obj.number_of_molecules = reader.get_int()


def _write_number_of_metadata(writer: SmileWriter, obj: Properties) -> None:
    writer.write_field_name("numberOfMetadata")
    writer.write_int(obj.number_of_metadata)


def _read_number_of_metadata(reader: SmileReader, obj: Properties) -> None:
    obj.number_of_metadata = reader.get_int()


def _write_string_set(field_name: str, get_set):
    def encode(writer: SmileWriter, obj: Properties) -> None:
        values = get_set(obj)
        if not values:
            return
        writer.write_field_name(field_name)
        writer.write_start_array()
        for v in values:
            writer.write_string(v)
        writer.write_end_array()
    return encode


def _read_string_set(get_set):
    def decode(reader: SmileReader, obj: Properties) -> None:
        target = get_set(obj)
        while True:
            tok = reader.next_token()
            if tok == SmileToken.END_ARRAY:
                return
            target.add(reader.get_text())
    return decode


def _write_channel_set(writer: SmileWriter, obj: Properties) -> None:
    if not obj.channel_set:
        return
    writer.write_field_name("moleculeChannelSet")
    writer.write_start_array()
    for v in obj.channel_set:
        writer.write_int(v)
    writer.write_end_array()


def _read_channel_set(reader: SmileReader, obj: Properties) -> None:
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return
        obj.channel_set.add(reader.get_int())


def _write_segment_table_names(writer: SmileWriter, obj: Properties) -> None:
    if not obj.segment_table_names:
        return
    writer.write_field_name("moleculeSegmentTableNames")
    writer.write_start_array()
    for x_col, y_col in obj.segment_table_names:
        writer.write_start_object()
        writer.write_field_name("yColumnName"); writer.write_string(y_col)
        writer.write_field_name("xColumnName"); writer.write_string(x_col)
        writer.write_end_object()
    writer.write_end_array()


def _read_segment_table_names(reader: SmileReader, obj: Properties) -> None:
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return
        y_col, x_col = "", ""
        while True:
            tok2 = reader.next_token()
            if tok2 == SmileToken.END_OBJECT:
                break
            field = reader.current_name()
            reader.next_token()
            if field == "yColumnName":
                y_col = reader.get_text()
            elif field == "xColumnName":
                x_col = reader.get_text()
        obj.segment_table_names.add((x_col, y_col))


def _write_documents(writer: SmileWriter, obj: Properties) -> None:
    if not obj.documents:
        return
    writer.write_field_name("documents")
    writer.write_start_array()
    for document in obj.documents.values():
        write_document(writer, document)
    writer.write_end_array()


def _read_documents(reader: SmileReader, obj: Properties) -> None:
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return
        document = read_document(reader)
        obj.documents[document.name] = document


PROPERTIES_FIELDS: list[FieldSpec] = [
    FieldSpec("archiveType", _write_archive_type, _read_archive_type),
    FieldSpec("type", _write_type, None),
    FieldSpec("schema", _write_schema, _read_schema),
    FieldSpec("numberOfMolecules", _write_number_of_molecules, _read_number_of_molecules),
    FieldSpec("numberOfMetadata", _write_number_of_metadata, _read_number_of_metadata),
    FieldSpec("moleculeTableColumnSet",
              _write_string_set("moleculeTableColumnSet", lambda o: o.table_column_set),
              _read_string_set(lambda o: o.table_column_set)),
    FieldSpec("moleculeSegmentTableNames", _write_segment_table_names, _read_segment_table_names),
    FieldSpec("moleculeTagSet",
              _write_string_set("moleculeTagSet", lambda o: o.tag_set),
              _read_string_set(lambda o: o.tag_set)),
    FieldSpec("moleculeChannelSet", _write_channel_set, _read_channel_set),
    FieldSpec("moleculeParameterSet",
              _write_string_set("moleculeParameterSet", lambda o: o.parameter_set),
              _read_string_set(lambda o: o.parameter_set)),
    FieldSpec("moleculeRegionSet",
              _write_string_set("moleculeRegionSet", lambda o: o.region_set),
              _read_string_set(lambda o: o.region_set)),
    FieldSpec("moleculePositionSet",
              _write_string_set("moleculePositionSet", lambda o: o.position_set),
              _read_string_set(lambda o: o.position_set)),
    FieldSpec("documents", _write_documents, _read_documents),
]


def write_properties(writer: SmileWriter, properties: Properties) -> None:
    write_record(writer, properties, PROPERTIES_FIELDS)


def read_properties(reader: SmileReader) -> Properties:
    properties = Properties()
    read_record(reader, properties, PROPERTIES_FIELDS)
    return properties
