import sqlite3
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path

MODEL_NAME = "all-MiniLM-L6-v2"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "chunks.db"
FAISS_PATH = DATA_DIR / "faiss.index"

def load_chunks():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, chunk_text FROM chunks ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows

def save_embeddings_to_sqlite(id_to_index):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for cid, emb_id in id_to_index.items():
        cur.execute("UPDATE chunks SET embedding_id=? WHERE id=?", (int(emb_id), int(cid)))
    conn.commit()
    conn.close()

def main():
    model = SentenceTransformer(MODEL_NAME)
    rows = load_chunks()
    if not rows:
        print("No chunks found. Run ingest_chunk.py first.")
        return
    ids = [r[0] for r in rows]
    texts = [r[1] for r in rows]

    print(f"Embedding {len(texts)} chunks...")
    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True
    )
    embeddings = np.array(embeddings).astype('float32')

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # cosine similarity
    index.add(embeddings)

    faiss.write_index(index, str(FAISS_PATH))
    id_to_index = {cid: i for i, cid in enumerate(ids)}
    save_embeddings_to_sqlite(id_to_index)

    print("✅ Saved faiss.index and updated chunks.db with embedding_id")

if __name__ == '__main__':
    main()