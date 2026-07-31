package gen;

import com.fasterxml.jackson.dataformat.smile.SmileFactory;
import com.fasterxml.jackson.dataformat.smile.SmileGenerator;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;

public class Gen {
    static SmileFactory factory = new SmileFactory();

    static void write(String name, Writer w) throws Exception {
        File out = new File("/private/tmp/claude-501/-Users-karlduderstadt-git-mars-fx/0161c3d7-5955-42d8-a16a-4408bfda2873/scratchpad/smile-fixtures/" + name + ".bin");
        out.getParentFile().mkdirs();
        try (OutputStream os = new FileOutputStream(out)) {
            SmileGenerator g = factory.createGenerator(os);
            w.write(g);
            g.close();
        }
        System.out.println("wrote " + name);
    }

    interface Writer { void write(SmileGenerator g) throws Exception; }

    public static void main(String[] args) throws Exception {
        write("basic_mixed", g -> {
            g.writeStartObject();
            g.writeStringField("a", "hello");
            g.writeNumberField("b", 1);
            g.writeNumberField("c", 3.14159);
            g.writeBooleanField("d", true);
            g.writeBooleanField("e", false);
            g.writeNullField("f");
            g.writeEndObject();
        });

        write("shared_names_repeat", g -> {
            g.writeStartArray();
            for (int i = 0; i < 50; i++) {
                g.writeStartObject();
                g.writeStringField("uid", "id" + i);
                g.writeArrayFieldStart("tags");
                g.writeString("a");
                g.writeString("b");
                g.writeEndArray();
                g.writeStringField("notes", "n");
                g.writeEndObject();
            }
            g.writeEndArray();
        });

        write("shared_names_wraparound", g -> {
            g.writeStartObject();
            for (int i = 0; i < 1100; i++) {
                g.writeNumberField("field_" + i, i);
            }
            g.writeEndObject();
        });

        write("numbers_all_types", g -> {
            g.writeStartArray();
            int[] ints = {0, 1, -1, 31, -31, 32, -32, 63, 64, 1000000, -1000000, Integer.MAX_VALUE, Integer.MIN_VALUE};
            for (int v : ints) g.writeNumber(v);
            double[] doubles = {0.0, -0.0, 1.0, -1.5, 3.14159265358979, Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY, Double.NaN, Double.MIN_VALUE, Double.MAX_VALUE};
            for (double v : doubles) g.writeNumber(v);
            g.writeEndArray();
        });

        write("strings_all_kinds", g -> {
            g.writeStartArray();
            g.writeString("");
            g.writeString("a");
            g.writeString("ab".repeat(40));  // long ascii, >64 bytes
            g.writeString("unicode: éè中文");
            g.writeString("x".repeat(200));  // very long ascii
            g.writeString("é".repeat(100)); // very long unicode
            g.writeEndArray();
        });

        write("long_field_name", g -> {
            g.writeStartObject();
            g.writeStringField("k".repeat(100), "v");
            g.writeEndObject();
        });

        write("binary_blob", g -> {
            g.writeStartObject();
            byte[] small = new byte[3];
            for (int i = 0; i < small.length; i++) small[i] = (byte) (i * 17 + 1);
            g.writeBinaryField("small", small);
            byte[] exact7 = new byte[7];
            for (int i = 0; i < exact7.length; i++) exact7[i] = (byte) (i * 31 + 3);
            g.writeBinaryField("exact7", exact7);
            byte[] multi = new byte[100];
            for (int i = 0; i < multi.length; i++) multi[i] = (byte) ((i * 37 + 5) % 256);
            g.writeBinaryField("multi", multi);
            g.writeEndObject();
        });

        write("nested_empty", g -> {
            g.writeStartObject();
            g.writeArrayFieldStart("emptyArray");
            g.writeEndArray();
            g.writeObjectFieldStart("emptyObject");
            g.writeEndObject();
            g.writeEndObject();
        });
    }
}
