// @category L2Dump
// @runtime Java
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.address.Address;
import java.io.PrintWriter;

public class Decomp extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Address addr = toAddr(args[0]);
        String out = args.length > 1 ? args[1] : null;
        Function fn = getFunctionAt(addr);
        String text;
        if (fn == null) {
            text = "NOFUNC " + addr;
        } else {
            DecompInterface di = new DecompInterface();
            di.openProgram(currentProgram);
            DecompileResults res = di.decompileFunction(fn, 120, monitor);
            if (!res.decompileCompleted()) {
                text = "FAIL " + fn.getName() + " : " + res.getErrorMessage();
            } else {
                text = "NAME " + fn.getName() + "\n" + res.getDecompiledFunction().getC();
            }
        }
        if (out != null) {
            PrintWriter w = new PrintWriter(out);
            w.println(text);
            w.close();
        } else {
            println(text);
        }
    }
}
