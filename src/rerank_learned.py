# Tiny learned reranker example (requires labeled data)
import joblib, numpy as np
from sklearn.linear_model import LogisticRegression

def train(X, y, out_path='../data/learned_reranker.joblib'):
    clf = LogisticRegression(class_weight='balanced', max_iter=1000, random_state=0)
    clf.fit(X, y)
    joblib.dump(clf, out_path)

def load_model(path='../data/learned_reranker.joblib'):
    return joblib.load(path)

def score_model(clf, feats):
    import numpy as np
    X = np.array(feats)
    return clf.predict_proba(X)[:,1]
