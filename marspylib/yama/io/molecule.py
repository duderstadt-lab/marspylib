"""Molecule-specific fields, transcribed from AbstractMolecule.createIOMaps
(molecule/AbstractMolecule.java:136-234): table, metadataUID, image, channel,
segmentTables, appended after the shared base record fields.

Two archive types add one further field beyond this common set -- see
`_EXTRA_FIELDS_BY_ARCHIVE_TYPE` below, and object_archive.py/transverseflow.py
for what those fields actually are.
"""

from __future__ import annotations

from ..model import ARCHIVE_TO_MOLECULE_CLASS, ARCHIVE_TO_MOLECULE_TYPE, Molecule
from ..smile.reader import SmileReader, SmileToken
from ..smile.writer import SmileWriter
from . import object_archive, transverseflow
from .fields import FieldSpec, read_record, write_record
from .record import base_record_fields
from .table import read_table, write_table

_EXTRA_FIELDS_BY_ARCHIVE_TYPE: dict[str, list[FieldSpec]] = {
    object_archive.OBJECT_ARCHIVE_TYPE: object_archive.EXTRA_FIELDS,
    transverseflow.TRANSVERSE_FLOW_ARCHIVE_TYPE: transverseflow.EXTRA_FIELDS,
}


def _write_table(writer: SmileWriter, obj: Molecule) -> None:
    if len(obj.table.columns) > 0:
        writer.write_field_name("table")
        write_table(writer, obj.table)


def _read_table(reader: SmileReader, obj: Molecule) -> None:
    obj.table = read_table(reader)


def _write_metadata_uid(writer: SmileWriter, obj: Molecule) -> None:
    if obj.metadata_uid is not None:
        writer.write_field_name("metadataUID")
        writer.write_string(obj.metadata_uid)


def _read_metadata_uid(reader: SmileReader, obj: Molecule) -> None:
    obj.metadata_uid = reader.get_text()


def _write_image(writer: SmileWriter, obj: Molecule) -> None:
    writer.write_field_name("image")
    writer.write_int(obj.image)


def _read_image(reader: SmileReader, obj: Molecule) -> None:
    obj.image = reader.get_int()


def _write_channel(writer: SmileWriter, obj: Molecule) -> None:
    writer.write_field_name("channel")
    writer.write_int(obj.channel)


def _read_channel(reader: SmileReader, obj: Molecule) -> None:
    obj.channel = reader.get_int()


def _write_segment_tables(writer: SmileWriter, obj: Molecule) -> None:
    entries = [item for item in obj.segment_tables.items() if len(item[1].columns) > 0]
    if not entries:
        return
    writer.write_field_name("segmentTables")
    writer.write_start_array()
    for (x_col, y_col, region), df in entries:
        writer.write_start_object()
        writer.write_field_name("xColumn"); writer.write_string(x_col)
        writer.write_field_name("yColumn"); writer.write_string(y_col)
        writer.write_field_name("region"); writer.write_string(region)
        writer.write_field_name("table")
        write_table(writer, df)
        writer.write_end_object()
    writer.write_end_array()


def _read_segment_tables(reader: SmileReader, obj: Molecule) -> None:
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_ARRAY:
            return
        x_col, y_col, region, df = "", "", "", None
        while True:
            tok2 = reader.next_token()
            if tok2 == SmileToken.END_OBJECT:
                break
            field = reader.current_name()
            tok3 = reader.next_token()
            if field == "xColumn":
                x_col = reader.get_text()
            elif field == "yColumn":
                y_col = reader.get_text()
            elif field == "region":
                region = reader.get_text()
            elif field == "table":
                df = read_table(reader)
            else:
                reader.skip_value()
        obj.segment_tables[(x_col, y_col, region)] = df


def molecule_fields(archive_type: str) -> list[FieldSpec]:
    type_fqcn = ARCHIVE_TO_MOLECULE_TYPE[archive_type]
    fields = base_record_fields(type_fqcn) + [
        FieldSpec("table", _write_table, _read_table),
        FieldSpec("metadataUID", _write_metadata_uid, _read_metadata_uid),
        FieldSpec("image", _write_image, _read_image),
        FieldSpec("channel", _write_channel, _read_channel),
        FieldSpec("segmentTables", _write_segment_tables, _read_segment_tables),
    ]
    return fields + _EXTRA_FIELDS_BY_ARCHIVE_TYPE.get(archive_type, [])


def write_molecule(writer: SmileWriter, molecule: Molecule, archive_type: str) -> None:
    write_record(writer, molecule, molecule_fields(archive_type))


def read_molecule(reader: SmileReader, archive_type: str) -> Molecule:
    molecule_class = ARCHIVE_TO_MOLECULE_CLASS[archive_type]
    molecule = molecule_class()
    read_record(reader, molecule, molecule_fields(archive_type))
    return molecule
