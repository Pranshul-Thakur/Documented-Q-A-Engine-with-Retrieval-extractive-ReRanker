import json
import re
from pathlib import Path
from urllib.parse import urlparse

DATA_DIR = Path(r"C:\Users\LENOVO\Desktop\Temp\data")
SRC_IN = DATA_DIR / "sources.json"
SRC_OUT = DATA_DIR / "sources_fixed.json"
PDF_DIR = DATA_DIR / "pdfs"

def slugify(text, maxlen=80):
    if not text:
        return None
    s = text.strip().lower()
    # replace spaces and many separators with hyphen
    s = re.sub(r"[\s/\\_:\.]+", "-", s)
    # remove characters not alnum or hyphen
    s = re.sub(r"[^a-z0-9\-]", "", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:maxlen]

def basename_from_url(url):
    try:
        p = urlparse(url).path
        name = Path(p).stem
        return name
    except:
        return None

def try_match_pdf(candidates, pdf_names):
    # try to find a pdf filename that contains candidate (or vice versa)
    cand = candidates.lower()
    # exact or partial match
    for pdf in pdf_names:
        stem = pdf.lower()
        if cand == stem or cand in stem or stem in cand:
            return pdf
    return None

def main():
    if not SRC_IN.exists():
        print("ERROR: data/sources.json not found at", SRC_IN)
        return
    raw = json.loads(SRC_IN.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        print("ERROR: sources.json must be a JSON array/list.")
        return

    pdf_files = []
    if PDF_DIR.exists():
        pdf_files = [p.stem for p in sorted(PDF_DIR.iterdir()) if p.suffix.lower() == ".pdf"]
    else:
        print("Warning: data/pdfs/ directory not found. Script will still generate ids from titles.")

    used_ids = set()
    fixed = []
    mapping = []

    for i, entry in enumerate(raw):
        e = dict(entry)  # copy
        # try: if user already supplied id, keep it
        if e.get("id"):
            eid = e["id"]
        else:
            # try to infer from URL basename
            url = e.get("url", "") or ""
            url_basename = basename_from_url(url) or ""
            tslug = slugify(e.get("title", "") or "")
            candidates = [url_basename, tslug]
            found_pdf = None
            for cand in candidates:
                if cand:
                    m = try_match_pdf(cand, pdf_files)
                    if m:
                        found_pdf = m
                        break
            if found_pdf:
                eid = found_pdf
            else:
                # fall back to slug from title or url basename
                if tslug:
                    eid = tslug
                elif url_basename:
                    eid = slugify(url_basename)
                else:
                    eid = f"source-{i+1}"
        # ensure unique
        base = eid
        k = 1
        while eid in used_ids:
            eid = f"{base}-{k}"
            k += 1
        used_ids.add(eid)
        e["id"] = eid
        fixed.append(e)
        mapping.append((i, entry.get("title", "")[:80], eid, entry.get("url", "")[:120]))

    # write output
    SRC_OUT.write_text(json.dumps(fixed, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Wrote", SRC_OUT)
    print("\nPreview of mappings (index, title -> assigned id, url):\n")
    for idx, title, eid, url in mapping:
        print(f"[{idx:02d}] {title!r}  -> id: {eid!s}")
        print(f"     url: {url}")
    print("\nIMPORTANT:")
    print(" - Inspect data/sources_fixed.json carefully.")
    print(" - Ensure each 'id' exactly matches the PDF filename (without .pdf). If not, either rename the PDF or edit the id.")
    print(f"To replace original file (Windows CMD): move /Y \"{SRC_OUT}\" \"{SRC_IN}\"")
    print(f"Or manually replace it in File Explorer after inspection.")
    print("After that re-run: python src\\ingest_chunk.py")

if __name__ == '__main__':
    main()