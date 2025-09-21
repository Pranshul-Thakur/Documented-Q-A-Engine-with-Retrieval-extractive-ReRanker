import json, pandas as pd
import os
import sys
sys.path.append(os.path.dirname(__file__))

from search import vector_search
from rerank_hybrid import hybrid_rerank
from pathlib import Path

QUEST_PATH = Path(__file__).resolve().parent.parent / 'experiments/questions_8.json'
qset = json.load(open(QUEST_PATH))

rows = []
for q in qset:
    baseline_candidates = vector_search(q['q'], k=30)
    baseline_top = baseline_candidates[:5]
    hybrid_top = hybrid_rerank(q['q'], baseline_candidates, k=5)

    def contains_expected(chunk, keywords):
        txt = (chunk.get('text','') or '').lower()
        return any(k.lower() in txt for k in keywords)

    baseline_hit = any(contains_expected(c, q['expected_keywords']) for c in baseline_top)
    hybrid_hit = any(contains_expected(c, q['expected_keywords']) for c in hybrid_top)

    rows.append({
        'id': q['id'],
        'query': q['q'],
        'baseline_hit': baseline_hit,
        'hybrid_hit': hybrid_hit
    })

df = pd.DataFrame(rows)
print(df)
df.to_csv(Path(__file__).resolve().parent.parent / 'experiments/eval_results.csv', index=False)
