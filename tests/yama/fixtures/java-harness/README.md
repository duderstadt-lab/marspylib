# Smile codec fixtures

The `.bin` files in `../smile/` are real Smile-binary bytes written by
Jackson's own `SmileGenerator` (not by marspylib), used as ground truth for
`tests/yama/test_smile_codec.py`. `Gen.java` is the generator program that
produced them.

## Reproducing

Requires a JDK and the `jackson-dataformat-smile` 2.18.0 jar (and its
`jackson-core`/`jackson-databind`/`jackson-annotations` dependencies of the
matching version) available locally, e.g. via a local Maven repository.

```bash
CP="$HOME/.m2/repository/com/fasterxml/jackson/dataformat/jackson-dataformat-smile/2.18.0/jackson-dataformat-smile-2.18.0.jar"
CP="$CP:$HOME/.m2/repository/com/fasterxml/jackson/core/jackson-core/2.18.0/jackson-core-2.18.0.jar"
CP="$CP:$HOME/.m2/repository/com/fasterxml/jackson/core/jackson-databind/2.18.0/jackson-databind-2.18.0.jar"
CP="$CP:$HOME/.m2/repository/com/fasterxml/jackson/core/jackson-annotations/2.18.0/jackson-annotations-2.18.0.jar"

mkdir -p out
javac -cp "$CP" -d out Gen.java
java -cp "$CP:out" gen.Gen
```

This writes `basic_mixed.bin`, `shared_names_repeat.bin`,
`shared_names_wraparound.bin`, `numbers_all_types.bin`,
`strings_all_kinds.bin`, `long_field_name.bin`, `binary_blob.bin`, and
`nested_empty.bin` — copy them into `../smile/`.

`pom.xml` is provided for reference/reproducibility (a from-scratch build via
`mvn exec:java` needs network access to fetch the `exec-maven-plugin`; the
`javac`/`java` invocation above avoids that and is what was actually used).

These fixtures only exercise the general-purpose Smile binary codec (no Mars
schema knowledge) — mars-core is not involved.

## MarsTable and full-archive fixtures (`../table/`, `../yama/`)

`GenTable.java` and `GenArchive.java` use real `mars-core` classes
(`MarsTable`, `SingleMoleculeArchive`, `DnaMoleculeArchive`,
`DefaultMoleculeArchive`, `MarsOMEMetadata`, ...) to write genuine
Fiji-compatible fixtures — these are the actual acceptance test for the
Python port, not just the binary codec.

```bash
cd /path/to/mars-core && mvn -q -o dependency:build-classpath -Dmdep.outputFile=/tmp/mars-core-cp.txt
CP="$(cat /tmp/mars-core-cp.txt):/path/to/mars-core/target/classes"

mkdir -p out
javac -cp "$CP" -d out GenTable.java GenArchive.java
java -cp "$CP:out" gen.GenTable    # -> mars_table.bin, mars_table_empty.bin (copy into ../table/)
java -cp "$CP:out" gen.GenArchive  # -> single/dna/default_molecule_archive.yama, empty_archive.yama (copy into ../yama/)
                                    # -> single_molecule_archive.yama.store/ (copy into ../yama_store/)
```

`GenArchive.java`'s `SingleMoleculeArchive` (3 molecules: `mol1`, `mol2`, `mol3`) is saved twice from
the same in-memory archive — once as a single-file `.yama` via `saveAs(File)`, once as a
`.yama.store` virtual directory via `saveAsVirtualStore(File)` — so the single-file and
virtual-store fixtures for `single_molecule_archive` stay in sync with each other.

**Do not open these fixture files in Fiji/Mars Rover to poke at them** — Rover writes a
`.yama.store`-adjacent `.rover` window-state file and can resave the archive on close (this
already happened once and silently added a stray tag to a committed fixture, breaking tests
that assert exact tag/parameter sets). If you need to inspect one, copy it out of the repo first.

`ReadPython.java` (also in this directory) is not a fixture generator — it's
the harness used to confirm real mars-core can read a `.yama` file written
by this port's Python writer (open a fixture with `marspylib.yama`, mutate
it, `archive.save(...)`, then run `java -cp "$CP:out" gen.ReadPython
<path>.yama` and eyeball the printed fields against what Python wrote). This
is the acceptance bar from the original design doc: mars-core reading what
Python writes and getting semantically identical records, not byte-identical
files.

## Extra archive types (`GenObjectArchive.java`, `GenTransverseFlowArchive.java`)

`ObjectArchive`/`MartianObject` (mars-core's `object` package) and
`TransverseFlowArchive`/`TransverseFlowMolecule` (the separate
`mars-transverseflow` module) each add one field beyond plain `Molecule` --
a `PeakShape` polygon and a `ReplicationForkShape`, respectively, both keyed
per timepoint. `GenObjectArchive.java` only needs the same mars-core
classpath as everything else above:

```bash
javac -cp "$CP" -d out GenObjectArchive.java
java -cp "$CP:out" gen.GenObjectArchive   # -> object_archive.yama (copy into ../yama/)
```

`mars-transverseflow` is a separate Maven module (`/path/to/mars-transverseflow`,
depends on a pinned mars-core version) and needs its own classpath:

```bash
cd /path/to/mars-transverseflow && mvn -q -o dependency:build-classpath -Dmdep.outputFile=/tmp/mars-transverseflow-cp.txt
CP_TF="$(cat /tmp/mars-transverseflow-cp.txt):/path/to/mars-transverseflow/target/classes"

javac -cp "$CP_TF" -d out GenTransverseFlowArchive.java
java -cp "$CP_TF:out" gen.GenTransverseFlowArchive   # -> transverseflow_archive.yama (copy into ../yama/)
```

Both generators include one record with an empty shapes map, to exercise
the "field omitted entirely when empty" write guard those two field types
share with several others in this format. Note
`ReplicationForkShape.laggingIntensity` entries are keyed `"y"` while
`parentalIntensity`/`leadingIntensity` use `"x"` -- a real quirk in the Java
source (`ReplicationForkShape.java`), not a typo, and the Python reader/
writer (`marspylib/yama/io/transverseflow.py`) replicates it exactly.
