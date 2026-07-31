package gen;

import de.mpg.biochem.mars.table.MarsTable;
import org.scijava.table.DoubleColumn;
import org.scijava.table.GenericColumn;
import com.fasterxml.jackson.dataformat.smile.SmileFactory;
import com.fasterxml.jackson.dataformat.smile.SmileGenerator;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.io.File;

public class GenTable {
    public static void main(String[] args) throws Exception {
        MarsTable table = new MarsTable("test");
        DoubleColumn t = new DoubleColumn("T");
        DoubleColumn x = new DoubleColumn("x");
        GenericColumn label = new GenericColumn("label");
        int n = 20;
        for (int i = 0; i < n; i++) {
            t.add((double) i);
            x.add(Math.sin(i) * 100.0 + (i == 5 ? Double.NaN : 0));
            label.add("row" + i);
        }
        table.add(t);
        table.add(x);
        table.add(label);

        File out = new File("/private/tmp/claude-501/-Users-karlduderstadt-git-mars-fx/0161c3d7-5955-42d8-a16a-4408bfda2873/scratchpad/smile-fixtures/mars_table.bin");
        out.getParentFile().mkdirs();
        SmileFactory factory = new SmileFactory();
        try (OutputStream os = new FileOutputStream(out)) {
            SmileGenerator g = factory.createGenerator(os);
            table.toJSON(g);
            g.close();
        }
        System.out.println("wrote mars_table.bin, rows=" + table.getRowCount());

        // also an empty table (0 columns) and a numeric-only + string-only table
        MarsTable empty = new MarsTable("empty");
        File outEmpty = new File("/private/tmp/claude-501/-Users-karlduderstadt-git-mars-fx/0161c3d7-5955-42d8-a16a-4408bfda2873/scratchpad/smile-fixtures/mars_table_empty.bin");
        try (OutputStream os = new FileOutputStream(outEmpty)) {
            SmileGenerator g = factory.createGenerator(os);
            empty.toJSON(g);
            g.close();
        }
        System.out.println("wrote mars_table_empty.bin");
    }
}
