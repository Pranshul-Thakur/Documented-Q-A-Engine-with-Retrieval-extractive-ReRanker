# Document-Grounded Q&A Engine with Hybrid Reranker

This project implements a **mini Q&A engine** over ~20 industrial & machine safety PDFs. It ingests documents, chunks them, builds embeddings for semantic search, and improves retrieval with a **hybrid reranker** (vector + BM25). Answers are **extractive** (taken directly from chunks) and always cite their source.

## 🚀 Pipeline
1. **Ingest** (`ingest_chunk.py`)
   * Splits PDFs into 80–350 word chunks.
   * Stores in `data/chunks.db` (SQLite).
2. **Index Build** (`index_build.py`)
   * Encodes chunks with `all-MiniLM-L6-v2` embeddings.
   * Saves vectors in `faiss.index`.
3. **API** (`api_app.py`)
   * `/ask` endpoint → retrieves top chunks (vector baseline or hybrid reranker).
   * Returns short extract + citation or abstains if evidence is weak.
4. **Evaluation** (`run_eval.py`)
   * Runs 8 test questions.
   * Compares **baseline** vs **hybrid** reranker.
   * Writes results to `experiments/eval_results.csv`.

## ⚙️ Setup
Install dependencies (latest versions are fine):

```
pip install sentence-transformers faiss-cpu torch fastapi uvicorn python-multipart \
            PyPDF2 pycryptodome rank-bm25 tqdm pandas scikit-learn joblib
```

## ▶️ Usage
1. **Ingest PDFs**

```
python src/ingest_chunk.py
```

2. **Build embeddings**

```
python src/index_build.py
```

3. **Start API**

```
uvicorn src.api_app:app --reload --port 8000
```

Open http://127.0.0.1:8000/docs to test.
Example query body:

```
{
  "q": "What is lockout-tagout?",
  "k": 3,
  "mode": "hybrid"
}
```

4. **Evaluate**

```
python src/run_eval.py
```

→ Results in `experiments/eval_results.csv`

## 📊 Results (sample)

| id | query | baseline_hit | hybrid_hit |
|----|-------|--------------|------------|
| q1 | lockout-tagout | ✅ | ✅ |
| q2 | standards | ❌ | ✅ |
| q3 | safe distances (robots) | ✅ | ✅ |
| q8 | guarding requirements | ✅ | ❌ |

## 💡 Learnings
* **Hybrid reranker** helps with precise technical terms (e.g., q2 improved).
* But reranking can also **over-weight wrong matches** (q8 worsened).
* Tunable knobs: α (blend weight), candidate pool size, abstain threshold.
* This is an **extractive Q&A engine** — not full generative RAG (no LLM used).

## 📸 Image Proof

![API Documentation](data/Images/Screenshot%202025-09-21%20202503.png)

![Query Execution](data/Images/Screenshot%202025-09-21%20203749.png)

![API Response](data/Images/Screenshot%202025-09-21%20203756.png)
