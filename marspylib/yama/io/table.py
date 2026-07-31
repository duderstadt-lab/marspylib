"""MarsTable <-> pandas.DataFrame, transcribed from
de.mpg.biochem.mars.table.MarsTable's toJSON/fromJSON (Smile-generator path
only -- writeDataAsGzippedBlocks / readDataBlockAndStringArrays; the
plain-JSON row-object-array fallback is never produced by a Smile writer and
is out of scope for this pure-Smile reader).
"""

from __future__ import annotations

import gzip

import numpy as np
import pandas as pd

from ..errors import YamaFormatError
from ..smile.reader import SmileReader, SmileToken
from ..smile.writer import SmileWriter

_BLOCK_PREFIX = "DoubleBlock,GZIP,dims=["


def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def write_table(writer: SmileWriter, df: pd.DataFrame) -> None:
    writer.write_start_object()
    if len(df.columns) > 0:
        _write_schema(writer, df)
        _write_data(writer, df)
    writer.write_end_object()


def _write_schema(writer: SmileWriter, df: pd.DataFrame) -> None:
    writer.write_field_name("schema")
    writer.write_start_object()
    writer.write_field_name("fields")
    writer.write_start_array()
    for col in df.columns:
        writer.write_start_object()
        writer.write_field_name("name")
        writer.write_string(str(col))
        writer.write_field_name("type")
        writer.write_string("number" if _is_numeric(df[col]) else "string")
        writer.write_end_object()
    writer.write_end_array()
    writer.write_end_object()


def _write_data(writer: SmileWriter, df: pd.DataFrame) -> None:
    writer.write_field_name("data")
    writer.write_start_object()

    double_cols = [c for c in df.columns if _is_numeric(df[c])]
    n_rows = len(df)
    block_name = f"{_BLOCK_PREFIX}{len(double_cols)},{n_rows}]"
    raw = bytearray()
    for c in double_cols:
        raw += df[c].to_numpy(dtype=">f8", copy=False).tobytes()
    writer.write_field_name(block_name)
    writer.write_binary(gzip.compress(bytes(raw)))

    for c in df.columns:
        if not _is_numeric(df[c]):
            writer.write_field_name(str(c))
            writer.write_start_array()
            for v in df[c]:
                writer.write_string("" if pd.isna(v) else str(v))
            writer.write_end_array()

    writer.write_end_object()


def read_table(reader: SmileReader) -> pd.DataFrame:
    """Assumes the table's START_OBJECT token has already been consumed."""
    columns: list[tuple[str, str]] = []
    numeric_data: dict[str, np.ndarray] = {}
    string_data: dict[str, list[str]] = {}

    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            break
        if tok != SmileToken.FIELD_NAME:
            raise YamaFormatError(f"expected FIELD_NAME or END_OBJECT in table, got {tok}")
        name = reader.current_name()
        if name == "schema":
            reader.next_token()  # START_OBJECT
            columns = _read_schema(reader)
        elif name == "data":
            tok2 = reader.next_token()
            if tok2 == SmileToken.START_OBJECT:
                numeric_data, string_data = _read_data_block_and_arrays(reader, columns)
            else:
                raise YamaFormatError(
                    "row-object-array table data (non-Smile JSON fallback) is not supported"
                )
        else:
            reader.skip_value()

    if not columns:
        return pd.DataFrame()

    data = {}
    for col_name, col_type in columns:
        if col_type == "number":
            data[col_name] = numeric_data.get(col_name, np.zeros(0, dtype="float64"))
        else:
            data[col_name] = string_data.get(col_name, [])
    return pd.DataFrame(data, columns=[c for c, _ in columns])


def _read_schema(reader: SmileReader) -> list[tuple[str, str]]:
    columns: list[tuple[str, str]] = []
    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            break
        name = reader.current_name()
        if name == "fields":
            reader.next_token()  # START_ARRAY
            while True:
                tok2 = reader.next_token()
                if tok2 == SmileToken.END_ARRAY:
                    break
                col_name, col_type = None, None
                while True:
                    tok3 = reader.next_token()
                    if tok3 == SmileToken.END_OBJECT:
                        break
                    field_name = reader.current_name()
                    reader.next_token()
                    if field_name == "name":
                        col_name = reader.get_text()
                    elif field_name == "type":
                        col_type = reader.get_text()
                columns.append((col_name, col_type))
        else:
            reader.skip_value()
    return columns


def _read_data_block_and_arrays(
    reader: SmileReader, columns: list[tuple[str, str]]
) -> tuple[dict, dict]:
    """`columns` is the already-parsed schema (name, type) list in original
    table-column order; the DoubleBlock packs only the "number"-typed
    columns, in that same relative order."""
    numeric_data: dict[str, np.ndarray] = {}
    string_data: dict[str, list[str]] = {}
    double_col_names = [name for name, ctype in columns if ctype == "number"]

    while True:
        tok = reader.next_token()
        if tok == SmileToken.END_OBJECT:
            break
        field_name = reader.current_name()
        if field_name.startswith(_BLOCK_PREFIX):
            dims = field_name[len(_BLOCK_PREFIX):-1]
            cols_str, rows_str = dims.split(",")
            cols, n_rows = int(cols_str), int(rows_str)
            reader.next_token()  # VALUE_BINARY
            raw = gzip.decompress(reader.get_binary())
            arr = np.frombuffer(raw, dtype=">f8").reshape(cols, n_rows)
            for i in range(cols):
                numeric_data[double_col_names[i]] = arr[i].astype("float64")
        else:
            reader.next_token()  # START_ARRAY
            values = []
            while True:
                tok2 = reader.next_token()
                if tok2 == SmileToken.END_ARRAY:
                    break
                values.append(reader.get_text())
            string_data[field_name] = values

    return numeric_data, string_data
