# -*- coding: utf-8 -*-
import ast, re
raw = open(r"C:\Users\cc\agent-tools\ed9147ed-ed29-4f0a-aa82-054f802e74c5.txt", encoding="utf-8", errors="replace").read()
idx = raw.find("RESULT: ")
if idx < 0:
    print("no RESULT")
    raise SystemExit(1)
text = raw[idx + len("RESULT: "):].strip()
# result is a python dict printed with repr
data = ast.literal_eval(text)
seen = set()
lines = []
for item in data.get("output", []):
    o = item.get("output", "")
    if "[EG]" not in o:
        continue
    # dedupe trailing \r\n duplicates
    line = o.replace("\r\n", "").replace("\n", "")
    if line in seen:
        continue
    seen.add(line)
    lines.append(line)
outp = r"E:\UE\FarmSim25D\Content\Python\_eg_dump.txt"
open(outp, "w", encoding="utf-8").write("\n".join(lines))
print("wrote", len(lines), "lines")
for L in lines:
    print(L)
