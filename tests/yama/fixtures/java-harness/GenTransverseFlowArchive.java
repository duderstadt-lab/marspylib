package gen;

import de.mpg.biochem.mars.transverseflow.TransverseFlowArchive;
import de.mpg.biochem.mars.transverseflow.TransverseFlowMolecule;
import de.mpg.biochem.mars.transverseflow.ReplicationForkShape;
import de.mpg.biochem.mars.metadata.MarsOMEMetadata;
import de.mpg.biochem.mars.table.MarsTable;
import org.scijava.table.DoubleColumn;

import java.io.File;
import java.util.HashMap;
import java.util.Map;

public class GenTransverseFlowArchive {
    static final String OUT_DIR = "/private/tmp/claude-501/-Users-karlduderstadt-git-mars-fx/0161c3d7-5955-42d8-a16a-4408bfda2873/scratchpad/smile-fixtures";

    public static void main(String[] args) throws Exception {
        TransverseFlowArchive archive = new TransverseFlowArchive("test_tf.yama");

        MarsOMEMetadata meta = new MarsOMEMetadata("tfmeta1");
        archive.putMetadata(meta);

        MarsTable table = new MarsTable("tf table");
        DoubleColumn t = new DoubleColumn("T");
        for (int i = 0; i < 5; i++) t.add((double) i);
        table.add(t);

        TransverseFlowMolecule mol1 = new TransverseFlowMolecule("tf1", table);
        mol1.setMetadataUID("tfmeta1");
        mol1.addTag("fork");

        double[] parentalX = {0.0, 1.0, 2.0};
        double[] parentalY = {0.0, 0.1, 0.2};
        double[] leadingX = {2.0, 3.0, 4.0};
        double[] leadingY = {0.2, 0.3, 0.4};
        double[] laggingX = {2.0, 3.0, 4.0};
        double[] laggingY = {0.2, -0.3, -0.4};
        ReplicationForkShape shape = new ReplicationForkShape(parentalX, parentalY, leadingX, leadingY, laggingX, laggingY);

        Map<Integer, Double> parentalGFP = new HashMap<>();
        parentalGFP.put(0, 1.5);
        parentalGFP.put(1, 2.5);
        shape.putParentIntegrationMap("GFP", parentalGFP);

        Map<Integer, Double> leadingRFP = new HashMap<>();
        leadingRFP.put(0, 3.5);
        shape.putLeadingIntegrationMap("RFP", leadingRFP);

        Map<Integer, Double> laggingGFP = new HashMap<>();
        laggingGFP.put(2, 9.9);
        shape.putLaggingIntegrationMap("GFP", laggingGFP);

        mol1.putShape(3, shape);
        archive.put(mol1);

        // Second molecule with NO shapes at all, to test the omitted-field path.
        TransverseFlowMolecule mol2 = new TransverseFlowMolecule("tf2");
        mol2.setMetadataUID("tfmeta1");
        archive.put(mol2);

        archive.saveAs(new File(OUT_DIR, "transverseflow_archive.yama"));
        System.out.println("wrote transverseflow_archive.yama, molecules=" + archive.getNumberOfMolecules());
    }
}
