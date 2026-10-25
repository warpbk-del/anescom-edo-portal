import sqlite3,json,collections as C
cn=sqlite3.connect(r"file:D:\anescom_edo\data\analytics.sqlite3?mode=ro",uri=True)
SP=[json.loads(r[0]) for r in cn.execute("select row from an_audit where source='avtokomp' and section like 'av_spec_rows%'")]
MT=[json.loads(r[0]) for r in cn.execute("select row from an_audit where source='avtokomp' and section='av_spec_meta'")]
print("rows",len(SP),"meta",len(MT))
c=C.Counter((r["doc"][:14],r["ts"][:22]) for r in SP)
for k,v in c.most_common(12):print(v,k)
print("SPEC",[m.get("Н","")[:25] for m in MT if m["kind"]=="spec"][:8])
print("CALC",[m.get("Н","")[:20] for m in MT if m["kind"]=="calc"][:12])
print("DEP",C.Counter(r["dep"][:25] for r in SP).most_common(8))
