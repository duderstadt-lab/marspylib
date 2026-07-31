package gen;

import de.mpg.biochem.mars.util.MarsMath;
import com.chrylis.codec.base58.Base58UUID;
import java.util.UUID;
import java.util.Random;

public class GenUID {
    public static void main(String[] args) throws Exception {
        Base58UUID codec = new Base58UUID();

        // Edge cases with controlled bit patterns
        UUID[] edgeCases = {
            new UUID(0L, 0L),                              // all zero -> should encode to "1"
            new UUID(0L, 1L),
            new UUID(0x00FFFFFFFFFFFFFFL, 0xFFFFFFFFFFFFFFFFL), // leading zero byte
            new UUID(0xFFFFFFFFFFFFFFFFL, 0xFFFFFFFFFFFFFFFFL), // all ones, top bit set (sign-byte-needed case)
            new UUID(0x8000000000000000L, 0x0000000000000000L), // top bit set only
            UUID.fromString("00000000-0000-0000-0000-000000000001"),
        };
        for (UUID u : edgeCases) {
            System.out.println(u.toString() + " -> " + codec.encode(u));
        }

        // Random cases, print the raw 16 bytes (hex) alongside the encoded string
        Random rnd = new Random(12345);
        for (int i = 0; i < 20; i++) {
            long msb = rnd.nextLong();
            long lsb = rnd.nextLong();
            UUID u = new UUID(msb, lsb);
            System.out.println(u.toString() + " -> " + codec.encode(u));
        }

        // A few real getUUID58() outputs (random, version-4 UUIDs) for length sanity
        for (int i = 0; i < 5; i++) {
            System.out.println("random getUUID58() -> " + MarsMath.getUUID58());
        }

        // metadata-style truncated
        System.out.println("metadata-style -> " + MarsMath.getUUID58().substring(0, 10));
    }
}
