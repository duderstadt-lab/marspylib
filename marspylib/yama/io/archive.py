"""Top-level single-file .yama document assembly, transcribed from
AbstractMoleculeArchive.createIOMaps (molecule/AbstractMoleculeArchive.java:636-698):
a root object with "properties" (always present), then "metadata" and
"molecules" arrays (each entirely omitted when empty).
"""

from __future__ import annotations

from ..errors import YamaFormatError
from ..model import ARCHIVE_TO_MOLECULE_TYPE, Archive
from ..smile.reader import SmileReader, SmileToken
from ..smile.writer import SmileWriter
from .metadata import read_metadata, write_metadata
from .molecule import read_molecule, write_molecule
from .properties import read_properties, write_properties


def write_archive_document(writer: SmileWriter, archive: Archive) -> None:
    writer.write_start_object()

    writer.write_field_name("properties")
    write_properties(writer, archive.properties)

    metadata = list(archive.metadata)
    if metadata:
        writer.write_field_name("metadata")
        writer.write_start_array()
        for meta in metadata:
            write_metadata(writer, meta)
        writer.write_end_array()

    if len(archive) > 0:
        writer.write_field_name("molecules")
        writer.write_start_array()
        for molecule in archive:
            write_molecule(writer, molecule, archive.archive_type)
        writer.write_end_array()

    writer.write_end_object()


def read_archive_document(reader: SmileReader) -> Archive:
    tok = reader.next_token()
    if tok != SmileToken.START_OBJECT:
        raise YamaFormatError(f"expected top-level START_OBJECT, got {tok}")

    properties = None
    metadata: dict = {}
    molecules: dict = {}

    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            break
        if tok != SmileToken.FIELD_NAME:
            raise YamaFormatError(f"expected FIELD_NAME or END_OBJECT, got {tok}")
        name = reader.current_name()
        reader.next_token()  # advance onto the field's value token

        if name == "properties":
            properties = read_properties(reader)
            if properties.archive_type not in ARCHIVE_TO_MOLECULE_TYPE:
                raise YamaFormatError(
                    f"unsupported archiveType {properties.archive_type!r}; "
                    f"expected one of {sorted(ARCHIVE_TO_MOLECULE_TYPE)}"
                )
        elif name == "metadata":
            if properties is None:
                raise YamaFormatError("'metadata' array encountered before 'properties'")
            while True:
                item_tok = reader.next_token()
                if item_tok == SmileToken.END_ARRAY:
                    break
                meta = read_metadata(reader)
                metadata[meta.uid] = meta
        elif name == "molecules":
            if properties is None:
                raise YamaFormatError("'molecules' array encountered before 'properties'")
            while True:
                item_tok = reader.next_token()
                if item_tok == SmileToken.END_ARRAY:
                    break
                molecule = read_molecule(reader, properties.archive_type)
                molecules[molecule.uid] = molecule
        else:
            reader.skip_value()

    if properties is None:
        raise YamaFormatError("archive document is missing 'properties'")

    return Archive(properties, metadata, molecules)
