# src/rerank_hybrid.py
import re
import sqlite3
import numpy as np
from rank_bm25 import BM25Okapi
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "chunks.db"

def load_all_chunks():
    """
    Load all chunks from the SQLite DB and build a BM25 index.
    Returns (bm25_index, ids_list)
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, chunk_text FROM chunks")
    rows = cur.fetchall()
    conn.close()

    ids = [r[0] for r in rows]
    docs = [r[1] or "" for r in rows]
    tokenized = [re.findall(r"\w+", d.lower()) for d in docs]
    if len(tokenized) == 0:
        # empty fallback
        bm25 = BM25Okapi([[""]])
    else:
        bm25 = BM25Okapi(tokenized)
    return bm25, ids

# Build BM25 and keep ids in memory (done once at import time)
try:
    BM25, ALL_IDS = load_all_chunks()
except Exception:
    # If DB missing or unreadable at import time, create empty placeholders.
    BM25, ALL_IDS = None, []

def bm25_scores_for_query(q):
    """
    Return BM25 scores array aligned with ALL_IDS.
    If BM25 index failed to build at import time, return zeros.
    """
    if BM25 is None:
        return np.zeros(len(ALL_IDS))
    qtok = re.findall(r"\w+", q.lower())
    return BM25.get_scores(qtok)

def hybrid_rerank(query, initial_candidates, k=5, alpha=0.6):
    """
    Re-rank initial_candidates (list of dicts with keys: chunk_id, vector_score) by blending:
      final_score = alpha * normalized_vector_score + (1-alpha) * normalized_bm25_score

    initial_candidates: list of dicts e.g.
      [{"chunk_id": 123, "vector_score": 0.87, "text": "..."} , ...]
    Returns top-k results (same dicts augmented with bm25_score and final_score).
    """
    if not initial_candidates:
        return []

    # Map candidate by chunk_id
    candidate_map = {c['chunk_id']: c for c in initial_candidates}
    cand_ids = list(candidate_map.keys())

    # Vector scores array (original cosine/IP scores)
    v_scores = np.array([candidate_map[c]['vector_score'] for c in cand_ids], dtype=float)
    # Normalize vector scores to [0,1]
    if v_scores.size and (v_scores.max() - v_scores.min()) > 1e-9:
        v_norm = (v_scores - v_scores.min()) / (v_scores.max() - v_scores.min())
    else:
        v_norm = np.ones_like(v_scores)

    # BM25: compute BM25 score for each candidate (using ALL_IDS mapping)
    if BM25 is None or not ALL_IDS:
        b_scores = np.zeros_like(v_scores)
    else:
        bm25_all = bm25_scores_for_query(query)
        id_to_pos = {cid: idx for idx, cid in enumerate(ALL_IDS)}
        # If a candidate id not present in ALL_IDS, give it 0
        b_scores = np.array([bm25_all[id_to_pos[c]] if c in id_to_pos else 0.0 for c in cand_ids], dtype=float)

    # Normalize BM25 scores to [0,1]
    if b_scores.size and (b_scores.max() - b_scores.min()) > 1e-9:
        b_norm = (b_scores - b_scores.min()) / (b_scores.max() - b_scores.min())
    else:
        b_norm = np.zeros_like(b_scores)

    # Blend
    final = alpha * v_norm + (1.0 - alpha) * b_norm

    # Compose result dicts
    results = []
    for cid, f, v, b in zip(cand_ids, final.tolist(), v_scores.tolist(), b_scores.tolist()):
        info = candidate_map[cid].copy()
        info.update({
            "bm25_score": float(b),
            "final_score": float(f),
            "vector_score_orig": float(v)
        })
        results.append(info)

    # Sort descending by final_score
    results = sorted(results, key=lambda x: x.get('final_score', 0.0), reverse=True)
    return results[:k]
