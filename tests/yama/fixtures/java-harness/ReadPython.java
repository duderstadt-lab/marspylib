package gen;

import de.mpg.biochem.mars.molecule.SingleMoleculeArchive;
import de.mpg.biochem.mars.molecule.SingleMolecule;
import de.mpg.biochem.mars.metadata.MarsOMEMetadata;
import java.io.File;

public class ReadPython {
    public static void main(String[] args) throws Exception {
        File f = new File(args[0]);
        SingleMoleculeArchive archive = new SingleMoleculeArchive(f);
        System.out.println("numberOfMolecules=" + archive.getNumberOfMolecules());
        System.out.println("numberOfMetadata=" + archive.getNumberOfMetadatas());

        SingleMolecule mol1 = archive.get("mol1");
        System.out.println("mol1.tags=" + mol1.getTags());
        System.out.println("mol1.notes=" + mol1.getNotes());
        System.out.println("mol1.channel=" + mol1.getChannel());
        System.out.println("mol1.image=" + mol1.getImage());
        System.out.println("mol1.metadataUID=" + mol1.getMetadataUID());
        System.out.println("mol1.param(dwell)=" + mol1.getParameter("dwell"));
        System.out.println("mol1.param(new_param)=" + mol1.getParameter("new_param"));
        System.out.println("mol1.param(nan_val)=" + mol1.getParameter("nan_val"));
        System.out.println("mol1.param(inf_val)=" + mol1.getParameter("inf_val"));
        System.out.println("mol1.param(label)=" + mol1.getStringParameter("label"));
        System.out.println("mol1.param(flag)=" + mol1.getBooleanParameter("flag"));
        System.out.println("mol1.table.rowCount=" + mol1.getTable().getRowCount());
        System.out.println("mol1.table.colCount=" + mol1.getTable().getColumnCount());
        System.out.println("mol1.table.col2(3)=" + mol1.getTable().getValue("Intensity", 3));
        System.out.println("mol1.region(r1).start=" + mol1.getRegion("r1").getStart());
        System.out.println("mol1.region(r1).end=" + mol1.getRegion("r1").getEnd());
        System.out.println("mol1.position(p1).position=" + mol1.getPosition("p1").getPosition());

        SingleMolecule mol2 = archive.get("mol2");
        System.out.println("mol2 exists=" + (mol2 != null));

        MarsOMEMetadata meta1 = archive.getMetadata("meta1");
        System.out.println("meta1.microscope=" + meta1.getMicroscopeName());
        System.out.println("meta1.sourceDirectory=" + meta1.getSourceDirectory());
        System.out.println("meta1.tags=" + meta1.getTags());

        System.out.println("ALL CHECKS PRINTED -- verify by eye against Python source values");
    }
}
