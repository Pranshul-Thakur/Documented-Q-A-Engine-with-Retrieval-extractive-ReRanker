import re, sqlite3, json
from pathlib import Path
from PyPDF2 import PdfReader

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PDF_DIR = DATA_DIR / "pdfs"
SOURCES = DATA_DIR / "sources.json"
DB_PATH = DATA_DIR / "chunks.db"

MIN_WORDS = 80
MAX_WORDS = 350

def load_sources():
    with open(SOURCES, "r", encoding="utf-8") as f:
        return {s["id"]: s for s in json.load(f)}

def extract_text_from_pdf(path):
    txt = []
    reader = PdfReader(path)
    for pnum, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text:
            text = re.sub(r'\s+', ' ', text).strip()
            txt.append((pnum+1, text))
    return txt

def chunk_text(text, min_words=MIN_WORDS, max_words=MAX_WORDS):
    words = text.split()
    if len(words) <= max_words:
        return [" ".join(words)]
    chunks = []
    i = 0
    while i < len(words):
        j = min(len(words), i + max_words)
        chunk = " ".join(words[i:j])
        chunks.append(chunk)
        i = j
    return chunks

def store_chunks(chunks):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT,
        title TEXT,
        page INTEGER,
        chunk_text TEXT,
        chunk_len INTEGER,
        embedding_id INTEGER
    )
    """)
    for src_id, title, page, ctext in chunks:
        cur.execute("INSERT INTO chunks (source_id, title, page, chunk_text, chunk_len) VALUES (?, ?, ?, ?, ?)",
                    (src_id, title, page, ctext, len(ctext.split())))
    conn.commit()
    conn.close()

def main():
    sources_map = load_sources()
    all_chunks = []
    for sid, src in sources_map.items():
        pdf_path = PDF_DIR / f"{sid}.pdf"
        if not pdf_path.exists():
            print("Missing:", pdf_path)
            continue
        pages = extract_text_from_pdf(pdf_path)
        for pnum, ptext in pages:
            for c in chunk_text(ptext):
                all_chunks.append((sid, src.get('title', ''), pnum, c))
    print(f"Storing {len(all_chunks)} chunks into {DB_PATH}")
    store_chunks(all_chunks)

import importlib, sys, subprocess

def ensure_package(pkg_name, import_name=None):
    import_name = import_name or pkg_name
    try:
        importlib.import_module(import_name)
        return True
    except Exception:
        try:
            print(f"Package '{pkg_name}' missing — installing now. This may take a minute...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])
            # try import again
            importlib.import_module(import_name)
            print(f"Package '{pkg_name}' installed successfully.")
            return True
        except Exception as e:
            print(f"Automatic install of '{pkg_name}' failed: {e}")
            return False

# Ensure pycryptodome is present (module name is Crypto)
if not ensure_package("pycryptodome", "Crypto"):
    print("Please install 'pycryptodome' manually in your environment and re-run the script.")
    
if __name__ == '__main__':
    main()
