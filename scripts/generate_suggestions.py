#!/usr/bin/env python
"""
Generate similarity-based suggestions from closed tickets.
Outputs:
 - data/closed_cases.json  (list of closed case summaries)
 - data/suggestions.json   (mapping ticket_id -> top 5 similar closed cases with resolution and score)
"""
import os
import json
import sys
import math
from pathlib import Path

try:
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.neighbors import NearestNeighbors
except Exception as e:
    print('Missing dependencies:', e)
    raise

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / 'data' / 'customer_support_tickets.csv'
OUT_DIR = ROOT / 'data'
OUT_DIR.mkdir(parents=True, exist_ok=True)

print('Reading CSV:', CSV)
df = pd.read_csv(CSV, dtype=str).fillna('')
print('Rows total:', len(df))

# Normalize column names
cols = {c.strip(): c for c in df.columns}
# expected columns from the CSV header
SUBJECT = cols.get('Ticket Subject')
DESC = cols.get('Ticket Description')
STATUS = cols.get('Ticket Status')
RESOLUTION = cols.get('Resolution')
TICKET_ID = cols.get('Ticket ID')

if not (SUBJECT and DESC and STATUS and RESOLUTION and TICKET_ID):
    print('Missing expected columns. Found:', list(df.columns))
    sys.exit(1)

# Filter closed cases (case-insensitive contains 'closed')
closed_mask = df[STATUS].str.strip().str.lower().isin(['closed', 'resolved', 'closed - resolved', 'closed - duplicate']) | df[STATUS].str.strip().str.lower().str.contains('closed')
closed_df = df[closed_mask].copy()
print('Closed rows:', len(closed_df))

# Compose text
closed_df['text'] = (closed_df[SUBJECT].astype(str) + '\n' + closed_df[DESC].astype(str)).str.strip()

# If too many empty texts, drop
closed_df = closed_df[closed_df['text'].str.strip()!='']
print('Closed rows with non-empty text:', len(closed_df))

texts = closed_df['text'].tolist()
ids = closed_df[TICKET_ID].tolist()
resolutions = closed_df[RESOLUTION].tolist()
subjects = closed_df[SUBJECT].tolist()

if len(texts) == 0:
    print('No closed-texts to index.')
    sys.exit(1)

print('Vectorizing texts with TF-IDF...')
vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1,2), stop_words='english')
X = vectorizer.fit_transform(texts)

print('Fitting nearest neighbors (cosine)...')
nn = NearestNeighbors(n_neighbors=6, metric='cosine', n_jobs=-1)
nn.fit(X)

dists, idxs = nn.kneighbors(X)

# Build suggestions mapping for each closed ticket - top 5 neighbors excluding itself
suggestions = {}
for i, ticket_id in enumerate(ids):
    neighbors = []
    for dist, j in zip(dists[i], idxs[i]):
        if j == i:
            continue
        score = 1 - float(dist)  # convert cosine distance to similarity
        neighbors.append({
            'ticket_id': ids[j],
            'subject': subjects[j],
            'resolution': resolutions[j],
            'similarity': round(score, 4)
        })
    suggestions[ticket_id] = neighbors[:5]

# Save closed cases summary for client lookup
closed_cases = []
for i, ticket_id in enumerate(ids):
    closed_cases.append({
        'ticket_id': ticket_id,
        'subject': subjects[i],
        'resolution': resolutions[i],
        'text_snippet': texts[i][:1000]
    })

with open(OUT_DIR / 'closed_cases.json', 'w', encoding='utf-8') as f:
    json.dump(closed_cases, f, ensure_ascii=False, indent=2)

with open(OUT_DIR / 'suggestions.json', 'w', encoding='utf-8') as f:
    json.dump(suggestions, f, ensure_ascii=False)

print('Wrote closed_cases.json and suggestions.json to', OUT_DIR)
