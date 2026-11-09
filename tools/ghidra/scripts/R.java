// Read raw bytes at a VA (default 32) and optionally show 32-bit words.
// @category L2Dump
// @runtime Java
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.MemoryBlock;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;

public class R extends GhidraScript {
    @Override
    public void run() throws Exception {
        Address a = toAddr(getScriptArgs()[0]);
        int n = getScriptArgs().length > 1 ? Integer.parseInt(getScriptArgs()[1]) : 32;
        byte[] b = new byte[n];
        int got = currentProgram.getMemory().getBytes(a, b);
        StringBuilder sb = new StringBuilder("HEX ");
        for (int i = 0; i < got; i++) sb.append(String.format("%02X ", b[i]));
        println(sb.toString());
        MemoryBlock blk = currentProgram.getMemory().getBlock(a);
        println("BLOCK " + (blk == null ? "none" : blk.getName() + " exec=" + blk.isExecute() + " init=" + blk.isInitialized()));
    }
}
