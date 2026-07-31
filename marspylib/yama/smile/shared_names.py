"""Shared-name (and, generically, shared-string-value) back-reference table.

Field names in a Smile document are shared/back-referenced across the whole
stream: the table starts empty, grows in first-seen order starting at index
0, and once it holds MAX_ENTRIES names the *next* new name resets it and
numbering restarts at 0 (com.fasterxml.jackson.dataformat.smile.SmileParser
/ SmileGenerator, MAX_SHARED_NAMES = 1024). Mars never enables shared string
*values* (CHECK_SHARED_STRING_VALUES=false), but this table is parametrized
by max size so the same class could serve that table too if ever needed.
"""

from __future__ import annotations

from ..errors import SmileFormatError
from .constants import MAX_SHARED_NAMES


class SharedNameTable:
    def __init__(self, max_entries: int = MAX_SHARED_NAMES):
        self._max_entries = max_entries
        self._names: list[str] = []
        self._index: dict[str, int] = {}

    def add(self, name: str) -> None:
        if len(self._names) >= self._max_entries:
            self._names.clear()
            self._index.clear()
        self._index[name] = len(self._names)
        self._names.append(name)

    def index_of(self, name: str) -> int | None:
        return self._index.get(name)

    def get(self, index: int) -> str:
        if index < 0 or index >= len(self._names):
            raise SmileFormatError(
                f"shared-name back-reference index {index} out of range "
                f"(table has {len(self._names)} entries)"
            )
        return self._names[index]

    def __len__(self) -> int:
        return len(self._names)
