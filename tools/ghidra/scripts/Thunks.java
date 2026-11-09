// Resolve E9 jmp rel32 thunks: for each hex VA argument print the target.
// @category L2Dump
// @runtime Java
import ghidra.app.script.GhidraScript;

public class Thunks extends GhidraScript {
    @Override
    public void run() throws Exception {
        for (String s : getScriptArgs()) {
            long va = 0;
            try {
                va = Long.parseLong(s, 16);
            } catch (NumberFormatException e) {
                println("BAD " + s);
                continue;
            }
            byte[] b = new byte[5];
            currentProgram.getMemory().getBytes(toAddr(va), b);
            // E9 rel32: target = va + 5 + (int32)b[1..5]
            long rel = (b[1] & 0xFF) | ((b[2] & 0xFF) << 8)
                     | ((b[3] & 0xFF) << 16) | ((long) (b[4] & 0xFF) << 24);
            if ((rel & 0x80000000L) != 0) rel -= 0x100000000L;
            long t = va + 5 + rel;
            boolean jmp = (b[0] & 0xFF) == 0xE9;
            println(String.format("THUNK %08X op=%02X -> %08X %s",
                    va, b[0] & 0xFF, t, jmp ? "" : "(not E9)"));
        }
    }
}
