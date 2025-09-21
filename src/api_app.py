from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import sqlite3, json

import sys
import os

sys.path.append(os.path.dirname(__file__))
from search import vector_search
from rerank_hybrid import hybrid_rerank
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "chunks.db"
SOURCES_PATH = DATA_DIR / "sources.json"

with open(SOURCES_PATH, 'r', encoding='utf-8') as f:
    sources = {s['id']: s for s in json.load(f)}

app = FastAPI()

class AskReq(BaseModel):
    q: str
    k: Optional[int] = 5
    mode: Optional[str] = 'hybrid'

def fetch_chunk_metadata(chunk_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT source_id, title, page, chunk_text FROM chunks WHERE id=?", (chunk_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {
            "source_id": row[0],
            "title": row[1],
            "page": row[2],
            "text": row[3],
            "source": sources.get(row[0])
        }
    return None

@app.post('/ask')
def ask(req: AskReq):
    baseline = vector_search(req.q, k=max(req.k, 30))
    if req.mode == 'baseline':
        chosen = baseline[:req.k]
        reranker_used = 'none'
    else:
        chosen = hybrid_rerank(req.q, baseline, k=req.k)
        reranker_used = 'hybrid'

    contexts = []
    for c in chosen:
        meta = fetch_chunk_metadata(c['chunk_id'])
        citation = meta['source']['url'] if meta and meta.get('source') else ''
        contexts.append({
            'chunk_id': c['chunk_id'],
            'text': meta['text'] if meta else c.get('text'),
            'title': meta['title'] if meta else c.get('title'),
            'page': meta['page'] if meta else c.get('page'),
            'url': citation,
            'vector_score': c.get('vector_score'),
            'bm25_score': c.get('bm25_score'),
            'final_score': c.get('final_score', None)
        })

    best_score = contexts[0].get('final_score', contexts[0].get('vector_score', 0)) if contexts else 0
    ABSTAIN_THRESHOLD = 0.15
    answer = None
    if best_score >= ABSTAIN_THRESHOLD and contexts:
        top_text = contexts[0]['text']
        sents = top_text.split('. ')
        answer = {'text': '. '.join(sents[:2]), 'citation': contexts[0]['url']}
    return {'answer': answer, 'contexts': contexts, 'reranker_used': reranker_used}
