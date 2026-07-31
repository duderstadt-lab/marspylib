package gen;

import de.mpg.biochem.mars.molecule.SingleMoleculeArchive;
import de.mpg.biochem.mars.molecule.SingleMolecule;
import de.mpg.biochem.mars.molecule.DnaMoleculeArchive;
import de.mpg.biochem.mars.molecule.DnaMolecule;
import de.mpg.biochem.mars.molecule.DefaultMoleculeArchive;
import de.mpg.biochem.mars.molecule.DefaultMolecule;
import de.mpg.biochem.mars.metadata.MarsOMEMetadata;
import de.mpg.biochem.mars.table.MarsTable;
import de.mpg.biochem.mars.util.MarsPosition;
import de.mpg.biochem.mars.util.MarsRegion;
import org.scijava.table.DoubleColumn;
import org.scijava.table.GenericColumn;

import java.io.File;

public class GenArchive {
    static final String OUT_DIR = "/private/tmp/claude-501/-Users-karlduderstadt-git-mars-fx/0161c3d7-5955-42d8-a16a-4408bfda2873/scratchpad/smile-fixtures";

    static void deleteRecursively(File f) {
        if (f.isDirectory()) {
            File[] children = f.listFiles();
            if (children != null) for (File c : children) deleteRecursively(c);
        }
        f.delete();
    }

    static MarsTable buildTable() {
        MarsTable table = new MarsTable("mol table");
        DoubleColumn t = new DoubleColumn("T");
        DoubleColumn i = new DoubleColumn("Intensity");
        GenericColumn lab = new GenericColumn("label");
        for (int k = 0; k < 10; k++) {
            t.add((double) k);
            i.add(Math.cos(k) * 50.0 + (k == 3 ? Double.NaN : 0));
            lab.add("f" + k);
        }
        table.add(t);
        table.add(i);
        table.add(lab);
        return table;
    }

    public static void main(String[] args) throws Exception {
        // ---- SingleMoleculeArchive ----
        SingleMoleculeArchive archive = new SingleMoleculeArchive("test_single.yama");

        MarsOMEMetadata meta1 = new MarsOMEMetadata("meta1");
        meta1.setMicroscopeName("TestScope");
        meta1.setSourceDirectory("/data/exp1");
        meta1.addTag("imported");
        archive.putMetadata(meta1);

        SingleMolecule mol1 = new SingleMolecule("mol1", buildTable());
        mol1.setMetadataUID("meta1");
        mol1.addTag("accepted");
        mol1.setParameter("dwell", 5.5);
        mol1.setParameter("label", "high");
        mol1.setParameter("flag", true);
        mol1.setParameter("nan_val", Double.NaN);
        mol1.setParameter("inf_val", Double.POSITIVE_INFINITY);
        mol1.putRegion(new MarsRegion("r1", "T", 1.0, 5.0, "#ff0000ff", 0.3));
        mol1.putPosition(new MarsPosition("p1", "T", 2.0, "#00ff00ff", 3.5));
        mol1.setNotes("test notes");
        mol1.setChannel(1);
        mol1.setImage(0);
        archive.put(mol1);

        SingleMolecule mol2 = new SingleMolecule("mol2");
        mol2.setMetadataUID("meta1");
        archive.put(mol2);

        SingleMolecule mol3 = new SingleMolecule("mol3", buildTable());
        mol3.setMetadataUID("meta1");
        mol3.addTag("accepted");
        mol3.addTag("reviewed");
        mol3.setChannel(2);
        mol3.setParameter("dwell", 9.25);
        archive.put(mol3);

        archive.saveAs(new File(OUT_DIR, "single_molecule_archive.yama"));
        System.out.println("wrote single_molecule_archive.yama, molecules=" + archive.getNumberOfMolecules());

        // ---- Virtual store (.yama.store), same in-memory archive ----
        File storeDir = new File(OUT_DIR, "single_molecule_archive.yama.store");
        deleteRecursively(storeDir);
        archive.saveAsVirtualStore(storeDir);
        System.out.println("wrote single_molecule_archive.yama.store");

        // ---- DnaMoleculeArchive ----
        DnaMoleculeArchive dnaArchive = new DnaMoleculeArchive("test_dna.yama");
        MarsOMEMetadata dnaMeta = new MarsOMEMetadata("dmeta1");
        dnaArchive.putMetadata(dnaMeta);
        DnaMolecule dnaMol = new DnaMolecule("dmol1", buildTable());
        dnaMol.setMetadataUID("dmeta1");
        dnaArchive.put(dnaMol);
        dnaArchive.saveAs(new File(OUT_DIR, "dna_molecule_archive.yama"));
        System.out.println("wrote dna_molecule_archive.yama");

        // ---- DefaultMoleculeArchive ----
        DefaultMoleculeArchive defArchive = new DefaultMoleculeArchive("test_default.yama");
        MarsOMEMetadata defMeta = new MarsOMEMetadata("xmeta1");
        defArchive.putMetadata(defMeta);
        DefaultMolecule defMol = new DefaultMolecule("xmol1", buildTable());
        defMol.setMetadataUID("xmeta1");
        defArchive.put(defMol);
        defArchive.saveAs(new File(OUT_DIR, "default_molecule_archive.yama"));
        System.out.println("wrote default_molecule_archive.yama");

        // ---- Empty archive ----
        SingleMoleculeArchive emptyArchive = new SingleMoleculeArchive("empty.yama");
        emptyArchive.saveAs(new File(OUT_DIR, "empty_archive.yama"));
        System.out.println("wrote empty_archive.yama");
    }
}
