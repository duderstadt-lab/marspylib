**Mars** - **M**olecule **AR**chive **S**uite

Pure-Python library for reading and writing Mars Molecule Archives (`.yama`)
and utility functions for working with them — no JVM, no Fiji install
required. Complete Molecule ARchive Suite (Mars) documentation including a
guide to working with mars data structures in python can be found at
[mars-docs](https://duderstadt-lab.github.io/mars-docs/).

## Installation

```
pip install marspylib
```

This project should soon be available for installation through [conda forge](https://github.com/conda-forge/staged-recipes/pull/18733).

Only dependency requirements are `numpy`, `pandas`, and `matplotlib` — this
package can be installed in any plain Python/conda environment and does not
require Fiji, ImageJ, or a JVM of any kind.

## Usage

```python
import marspylib.yama as yama

archive = yama.open("experiment.yama")
print(archive.properties.number_of_molecules)

for molecule in archive:
    df = molecule.table            # pandas.DataFrame
    if "accepted" in molecule.tags:
        ...

molecule = archive["some-uid"]     # random access by UID

archive.save("experiment_out.yama")
```

### Creating a new archive

You don't need Fiji to build a `.yama` from scratch — construct
`Properties`, a `Molecule` (or one of its subclasses, matching the archive
type — see [Supported archive types](#supported-archive-types)), and
`MarsMetadata`/regions/positions as needed, then `put()` each record into a
fresh `Archive` and save:

```python
import pandas as pd
import marspylib.yama as yama

properties = yama.Properties(archive_type=yama.ARCHIVE_TYPES["SingleMoleculeArchive"])
archive = yama.Archive(properties, metadata={}, molecules={})

metadata = yama.MarsMetadata(microscope="Nikon Ti2", source_directory="/data/2024-01-15")
archive.put_metadata(metadata)

for i in range(3):
    molecule = yama.SingleMolecule(metadata_uid=metadata.uid)
    molecule.add_tag("accepted")
    molecule.parameters["dwell"] = 5.5
    molecule.table = pd.DataFrame({
        "T": [0.0, 1.0, 2.0],
        "Intensity": [10.1 + i, 10.5 + i, 10.9 + i],
    })
    archive.put(molecule)   # molecule.uid was auto-generated -- see below

archive.save("new_experiment.yama")
```

Leaving `uid` unset when constructing a `Molecule`/`MarsMetadata` (as above)
auto-generates one in mars-core's own format — the same Base58 encoding of a
random UUID that Fiji itself uses (`MarsMath.getUUID58()`), so records you
create in Python get UIDs that are unique right alongside ones created in
Fiji, which matters if the two ever get merged into the same archive. You
can also call the generator directly, or supply your own `uid=`:

```python
yama.new_molecule_uid()    # e.g. "8eoHfZ1GdvNBeWGNNDY3hp" -- full-length
yama.new_metadata_uid()    # e.g. "mnAgQYYn63" -- fixed 10 characters, matching mars-core

molecule = yama.SingleMolecule(uid="my-own-id")   # or supply your own
```

`yama.ARCHIVE_TYPES` maps every supported short name (`SingleMoleculeArchive`,
`DnaMoleculeArchive`, `DefaultMoleculeArchive`, `ObjectArchive`,
`TransverseFlowArchive`) to the archive-type string mars-core expects — use
whichever matches the `Molecule` subclass you're building records with.

### Virtual archives (`.yama.store`)

Large archives saved from Fiji as a `.yama.store` directory (rather than a
single `.yama` file) open the same way — `yama.open()` detects it from the
path — but records are loaded lazily, one at a time, instead of all at once:

```python
archive = yama.open("experiment.yama.store")   # nothing loaded yet
print(len(archive), "molecules")

for molecule in archive:                        # each one read from disk as you reach it
    if "accepted" in molecule.tags:
        ...

molecule = archive["some-uid"]                  # read once, then cached for reuse
```

Writing works the same `archive.save(...)` call as single-file archives,
dispatched purely on whether the target path ends in `.yama.store`:

```python
archive["some-uid"].add_tag("reviewed")
archive.save()                          # update the .yama.store in place

archive.save("subset.yama")             # flatten into a single file instead
archive.save("copy.yama.store")         # write out as a separate virtual store
```

A `.yama.store` archive must still exist on disk for as long as you're
reading from it — a molecule you haven't touched yet is only read from its
file the moment you access it, so don't delete, move, or let a temporary
directory holding one go out of scope while you're still using the archive.

Molecules in a `.yama.store` are loaded lazily and LRU-cached (default 128
at a time) — mutating one you already hold a reference to (like
`molecule.add_tag(...)` above) is safe as long as it's still cached when you
call `save()`. If you're touching more distinct molecules than that between
editing one and saving, or want to be certain, use `archive.put(molecule)`
to pin it so it's guaranteed to be written regardless of cache pressure:

```python
molecule = archive["some-uid"]
molecule.add_tag("reviewed")
archive.put(molecule)     # pins it -- guaranteed to persist even if evicted
# ... touch hundreds of other molecules ...
archive.save()
```

`put()`/`put_metadata()` are also how you add a brand-new record (a UID
that wasn't already in the archive) — see the mapping table below.

### Supported archive types

Every `SingleMoleculeArchive`, `DnaMoleculeArchive`, and
`DefaultMoleculeArchive` opened from Fiji gets its own `Molecule` subclass
(`SingleMolecule`, `DnaMolecule`, `DefaultMolecule`) — currently identical
to plain `Molecule`, since in mars-core these three only differ in name, not
in the fields they store today. Every archive type gets a dedicated Python
class uniformly, even when (as here) there's nothing archive-type-specific
about it yet, so a future mars-core field addition to any one of them only
means filling in that one class here, not restructuring anything.

Two other archive types carry one extra field per record, so they get their
own `Molecule` subclasses:

**`ObjectArchive`** (mars-core's `object` package) uses `MartianObject`,
which adds `.shapes`: a `dict[int, PeakShape]` mapping timepoint → tracked
polygon outline.

```python
archive = yama.open("tracked_objects.yama")   # archive_type is ObjectArchive
obj = archive["some-uid"]
shape = obj.shapes[12]        # PeakShape at timepoint 12
shape.x, shape.y              # coordinate arrays (same length)
obj.shapes[13] = yama.PeakShape(x=[...], y=[...])
archive.save()
```

**`TransverseFlowArchive`** (the separate `mars-transverseflow` module) uses
`TransverseFlowMolecule`, which adds `.replication_fork_shapes`: a
`dict[int, ReplicationForkShape]` mapping timepoint → replication fork
geometry (parental/leading/lagging strand outlines, each with an optional
per-channel intensity profile).

```python
archive = yama.open("forks.yama")   # archive_type is TransverseFlowArchive
mol = archive["some-uid"]
shape = mol.replication_fork_shapes[7]
shape.parental_x, shape.parental_y     # not-yet-replicated duplex outline
shape.leading_x, shape.leading_y       # leading-strand daughter outline
shape.lagging_x, shape.lagging_y       # lagging-strand daughter outline
shape.leading_intensity["GFP"][7]      # per-channel intensity, keyed by coordinate
```

## Coming from Java/Fiji: method name mapping

This library's classes cover the same data as mars-core's Java classes, but
follow Python naming conventions (`snake_case`, attributes instead of
getters/setters) rather than mirroring the Java API name-for-name. Where a
Java call was a getter/setter pair, the Python side is usually just a plain
attribute you can read or assign directly.

**`Archive`** (`de.mpg.biochem.mars.molecule.MoleculeArchive`)

| Java | Python |
|---|---|
| `archive.get(uid)` | `archive[uid]` |
| `archive.getMetadata(uid)` | `archive.get_metadata(uid)` |
| `archive.metadataHasTag(uid, tag)` | `archive.metadata_has_tag(uid, tag)` |
| `archive.getNumberOfMolecules()` | `len(archive)` or `archive.properties.number_of_molecules` |
| `archive.getNumberOfMetadatas()` | `len(list(archive.metadata))` |
| `archive.molecules().forEach(...)` | `for molecule in archive: ...` |
| `archive.getMolecules()` iteration | `for molecule in archive: ...` |
| (metadata collection) | `archive.metadata` (iterator) |
| `archive.properties()` | `archive.properties` (attribute) |
| `archive.save()` | `archive.save()` |
| `archive.saveAs(file)` | `archive.save(path)` |
| `archive.saveAsVirtualStore(dir)` | `archive.save(path)` where `path` ends in `.yama.store` |
| `archive.put(molecule)` | `archive.put(molecule)` |
| `archive.putMetadata(m)` | `archive.put_metadata(m)` |

**`Molecule` / `MarsRecord`** (`de.mpg.biochem.mars.molecule.Molecule`, `MarsRecord`)

| Java | Python |
|---|---|
| `molecule.getUID()` | `molecule.uid` |
| `molecule.getNotes()` / `setNotes(s)` | `molecule.notes` |
| `molecule.getTags()` | `molecule.tags` (list) |
| `molecule.addTag(tag)` | `molecule.add_tag(tag)` |
| `molecule.hasTag(tag)` | `molecule.has_tag(tag)` |
| `molecule.getParameter(name)` | `molecule.parameters[name]` |
| `molecule.setParameter(name, v)` | `molecule.parameters[name] = v` |
| `molecule.hasParameter(name)` | `name in molecule.parameters` |
| `molecule.getRegion(name)` / `putRegion(r)` | `molecule.regions[name]` |
| `molecule.hasRegion(name)` | `molecule.has_region(name)` |
| `molecule.getPosition(name)` / `putPosition(p)` | `molecule.positions[name]` |
| `molecule.hasPosition(name)` | `molecule.has_position(name)` |
| `molecule.getTable()` | `molecule.table` (`pandas.DataFrame`) |
| `molecule.getMetadataUID()` / `setMetadataUID(s)` | `molecule.metadata_uid` |
| `molecule.getImage()` / `setImage(i)` | `molecule.image` |
| `molecule.getChannel()` / `setChannel(c)` | `molecule.channel` |
| `molecule.getSegmentsTable(x, y, region)` | `molecule.segment_tables[(x, y, region)]` |

**`MarsMetadata`** (`de.mpg.biochem.mars.metadata.MarsMetadata`)

| Java | Python |
|---|---|
| `metadata.getUID()` | `metadata.uid` |
| `metadata.getMicroscopeName()` / `setMicroscopeName(s)` | `metadata.microscope` |
| `metadata.getSourceDirectory()` / `setSourceDirectory(s)` | `metadata.source_directory` |
| `metadata.getLog()` | `metadata.log` |
| `metadata.hasTag(tag)` | `metadata.has_tag(tag)` |
| `metadata.getBdvSource(name)` | `metadata.bdv_sources[name]` |

**`MarsRegion`** / **`MarsPosition`** (`de.mpg.biochem.mars.util`)

| Java | Python |
|---|---|
| `region.getName()` / `getColumn()` / `getStart()` / `getEnd()` / `getColor()` / `getOpacity()` | `.name` / `.column` / `.start` / `.end` / `.color` / `.opacity` |
| `position.getName()` / `getColumn()` / `getPosition()` / `getColor()` / `getStroke()` | `.name` / `.column` / `.position` / `.color` / `.stroke` |

**`MoleculeArchiveProperties`**

| Java | Python |
|---|---|
| `properties.getSchema()` / `getInputSchema()` | `properties.schema` |
| `properties.getTagSet()` | `properties.tag_set` |
| `properties.getChannelSet()` | `properties.channel_set` |
| `properties.getColumnSet()` | `properties.table_column_set` |
| `properties.getParameterSet()` | `properties.parameter_set` |
| `properties.getRegionSet()` | `properties.region_set` |
| `properties.getPositionSet()` | `properties.position_set` |
| `properties.getSegmentsTableNames()` | `properties.segment_table_names` |
| document access | `properties.documents[name]` |

**Not yet supported:** removing molecules/metadata records from an archive
(there's a `put`, but no `remove`/`delete` yet).

Note `archive.save()` recomputes `properties.tag_set`/`channel_set`/
`parameter_set`/`region_set`/`position_set`/`table_column_set`/
`segment_table_names`/`number_of_molecules`/`number_of_metadata` from the
archive's actual current contents before writing (mirroring mars-core's own
`rebuildIndexes()`), so these always reflect reality after a `put()` even
though nothing updates them incrementally as you go.
