package gen;

import de.mpg.biochem.mars.object.ObjectArchive;
import de.mpg.biochem.mars.object.MartianObject;
import de.mpg.biochem.mars.image.PeakShape;
import de.mpg.biochem.mars.metadata.MarsOMEMetadata;
import de.mpg.biochem.mars.table.MarsTable;
import org.scijava.table.DoubleColumn;

import java.io.File;

public class GenObjectArchive {
    static final String OUT_DIR = "/private/tmp/claude-501/-Users-karlduderstadt-git-mars-fx/0161c3d7-5955-42d8-a16a-4408bfda2873/scratchpad/smile-fixtures";

    public static void main(String[] args) throws Exception {
        ObjectArchive archive = new ObjectArchive("test_object.yama");

        MarsOMEMetadata meta = new MarsOMEMetadata("ometa1");
        archive.putMetadata(meta);

        MarsTable table = new MarsTable("obj table");
        DoubleColumn t = new DoubleColumn("T");
        for (int i = 0; i < 5; i++) t.add((double) i);
        table.add(t);

        MartianObject obj1 = new MartianObject("obj1", table);
        obj1.setMetadataUID("ometa1");
        obj1.addTag("tracked");
        double[] x0 = {0.0, 1.0, 1.0, 0.0};
        double[] y0 = {0.0, 0.0, 1.0, 1.0};
        obj1.putShape(0, new PeakShape(x0, y0));
        double[] x1 = {0.5, 1.5, 1.5, 0.5, 0.2};
        double[] y1 = {0.5, 0.5, 1.5, 1.5, 1.0};
        obj1.putShape(1, new PeakShape(x1, y1));
        archive.put(obj1);

        // Second object with NO shapes at all, to test the omitted-field path.
        MartianObject obj2 = new MartianObject("obj2");
        obj2.setMetadataUID("ometa1");
        archive.put(obj2);

        archive.saveAs(new File(OUT_DIR, "object_archive.yama"));
        System.out.println("wrote object_archive.yama, objects=" + archive.getNumberOfMolecules());
    }
}
