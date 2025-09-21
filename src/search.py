import faiss, sqlite3, json
from sentence_transformers import SentenceTransformer
from pathlib import Path

MODEL_NAME = "all-MiniLM-L6-v2"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "chunks.db"
FAISS_PATH = DATA_DIR / "faiss.index"
SOURCES_PATH = DATA_DIR / "sources.json"

# Load embedding model and FAISS index
model = SentenceTransformer(MODEL_NAME)
index = faiss.read_index(str(FAISS_PATH))
with open(SOURCES_PATH, 'r', encoding='utf-8') as f:
    sources = {s['id']: s for s in json.load(f)}

def vector_search(query, k=5):
    q_emb = model.encode([query], normalize_embeddings=True).astype('float32')
    D, I = index.search(q_emb, k)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    results = []
    for score, pos in zip(D[0].tolist(), I[0].tolist()):
        cur.execute("SELECT id, source_id, title, page, chunk_text FROM chunks WHERE embedding_id=? LIMIT 1", (int(pos),))
        row = cur.fetchone()
        if row:
            cid, sid, title, page, text = row
            results.append({
                "chunk_id": cid,
                "source_id": sid,
                "title": title,
                "page": page,
                "text": text,
                "vector_score": float(score)
            })
    conn.close()
    return results
