// Find program symbols whose name contains a substring.
// Arg0 = needle, arg1 = limit (default 200).
// @category L2Dump
// @runtime Java
import ghidra.app.script.GhidraScript;
import ghidra.program.model.symbol.Symbol;

public class FindSym extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String needle = args[0];
        int limit = args.length > 1 ? Integer.parseInt(args[1]) : 200;
        int n = 0;
        for (Symbol s : currentProgram.getSymbolTable().getAllSymbols(true)) {
            String nm = s.getName();
            if (nm.contains(needle)) {
                println("SYM " + s.getAddress() + " " + nm);
                if (++n >= limit) break;
            }
        }
        println("SYMCOUNT " + n);
    }
}
