import pdfplumber, io, sys
sys.stdout.reconfigure(encoding="utf-8")
with pdfplumber.open("data/raw/chj/informe_episodio_chj.pdf") as pdf:
    print("pages", len(pdf.pages))
    out = []
    for i, p in enumerate(pdf.pages, 1):
        out.append(f"\n=== PAGE {i} ===\n" + (p.extract_text() or ""))
    open("data/raw/chj/informe_episodio_chj.txt", "w", encoding="utf-8").write("".join(out))
