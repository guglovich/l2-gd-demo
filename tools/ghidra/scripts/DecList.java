// @category L2Dump
// @runtime Java
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.address.Address;
import java.io.PrintWriter;
import java.io.BufferedReader;
import java.io.FileReader;

public class DecList extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String listPath = args[0];
        String out = args[1];
        PrintWriter w = new PrintWriter(out, "UTF-8");
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        try (BufferedReader br = new BufferedReader(new FileReader(listPath))) {
            String s;
            while ((s = br.readLine()) != null) {
                s = s.trim();
                if (s.isEmpty()) continue;
                Address a = toAddr(s);
                Function fn = getFunctionAt(a);
                w.println("=== " + a);
                if (fn == null) {
                    w.println("NOFUNC " + a);
                } else {
                    DecompileResults res = di.decompileFunction(fn, 240, monitor);
                    if (!res.decompileCompleted()) {
                        w.println("FAIL " + fn.getName() + " : " + res.getErrorMessage());
                    } else {
                        w.println(res.getDecompiledFunction().getC());
                    }
                }
                w.println("=== end");
                w.flush();
            }
        } finally {
            w.close();
        }
    }
}
