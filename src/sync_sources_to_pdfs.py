# src/sync_sources_to_pdfs.py
import json
import re
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA = PROJECT_ROOT / "data"
SRC = DATA / "sources.json"
OUT = DATA / "sources_synced.json"
PDF_DIR = DATA / "pdfs"

def url_basename(url):
    try:
        return Path(urlparse(url).path).stem
    except:
        return ""

def slug_tokens(s):
    s = re.sub(r"[^\w\s\-]", " ", (s or "").lower())
    tokens = [t for t in re.split(r"[\s\-]+", s) if len(t) > 2]
    return tokens

def find_best_pdf_for_entry(entry, pdf_stems):
    # 1) exact match by existing id
    cur = (entry.get("id") or "").strip()
    if cur and cur in pdf_stems:
        return cur
    # 2) match by url basename
    ub = url_basename(entry.get("url","")).strip()
    if ub and ub in pdf_stems:
        return ub
    # 3) match by PDF stem contained in title or title token in pdf stem (loose)
    title = (entry.get("title") or "").lower()
    for ps in pdf_stems:
        ps_l = ps.lower()
        if title and (title in ps_l or ps_l in title):
            return ps
    # 4) match by tokens (require at least one token match and prefer those with more)
    tokens = slug_tokens(entry.get("title","")) + slug_tokens(url_basename(entry.get("url","")))
    best = None
    best_score = 0
    for ps in pdf_stems:
        score = sum(1 for t in tokens if t in ps.lower())
        if score > best_score:
            best_score = score
            best = ps
    if best_score >= 1:
        return best
    # 5) fallback: empty string (no match)
    return ""

def main():
    if not SRC.exists():
        print("ERROR: data/sources.json not found at", SRC)
        return
    raw = json.loads(SRC.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        print("ERROR: sources.json must be a JSON array of objects.")
        return
    pdfs = sorted([p.stem for p in (PDF_DIR.glob("*.pdf") if PDF_DIR.exists() else [])])
    print(f"Found {len(pdfs)} PDFs in {PDF_DIR}")
    for p in pdfs[:200]:
        print("  -", p)
    pdf_set = set(pdfs)

    mapping = []
    used = set()
    out_list = []
    for i, entry in enumerate(raw):
        assigned = find_best_pdf_for_entry(entry, pdfs)
        # If assigned is empty, leave existing id if present, else generate slug from title
        if not assigned:
            if entry.get("id"):
                assigned = entry["id"]
            else:
                # generate a fallback slug from title
                fallback = re.sub(r"[^\w\s\-]", "", (entry.get("title") or "").lower())
                fallback = re.sub(r"[\s]+", "-", fallback).strip("-")
                assigned = fallback[:80] if fallback else f"source-{i+1}"
        # ensure uniqueness by appending suffix if needed
        base = assigned
        k = 1
        while assigned in used:
            assigned = f"{base}-{k}"
            k += 1
        used.add(assigned)
        entry["id"] = assigned
        out_list.append(entry)
        mapping.append((i, entry.get("title","")[:80], assigned, entry.get("url","")[:140], ("(pdf exists)" if assigned in pdf_set else "(no pdf match)")))

    OUT.write_text(json.dumps(out_list, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print("WROTE:", OUT)
    print("\nPreview (index, title -> assigned id, note):\n")
    for idx, title, aid, url, note in mapping:
        print(f"[{idx:02d}] {title!r}\n     -> id: {aid} {note}\n     url: {url}\n")

    print("\nIMPORTANT next steps:")
    print("  1) Inspect data/sources_synced.json in an editor (Notepad/VSCode).")
    print("  2) If ids look correct, replace your original sources.json:")
    print(f"       move /Y \"{OUT}\" \"{SRC}\"   (Windows CMD)")
    print("     or replace manually using File Explorer.")
    print("  3) Run the ingest script:")
    print("       python src\\ingest_chunk.py")

if __name__ == '__main__':
    main()
