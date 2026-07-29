#!/usr/bin/env python
"""
Compute top-5 closed-case suggestions for every ticket.
Outputs:
 - data/all_tickets.json       (array of tickets with key fields)
 - data/suggestions_for_all.json  (mapping ticket_id -> list of similar closed cases)
"""
import json
from pathlib import Path
import sys

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
print('Total rows:', len(df))

cols = {c.strip(): c for c in df.columns}
SUBJECT = cols.get('Ticket Subject')
DESC = cols.get('Ticket Description')
STATUS = cols.get('Ticket Status')
RESOLUTION = cols.get('Resolution')
TICKET_ID = cols.get('Ticket ID')
PRIORITY = cols.get('Ticket Priority')
PRODUCT = cols.get('Product Purchased')
CHANNEL = cols.get('Ticket Channel')

if not (SUBJECT and DESC and STATUS and RESOLUTION and TICKET_ID):
    print('Missing expected columns. Found:', list(df.columns))
    sys.exit(1)

# Compose text and prepare ticket objects
df['text'] = (df[SUBJECT].astype(str) + '\n' + df[DESC].astype(str)).str.strip()

tickets = []
for _, r in df.iterrows():
    tickets.append({
        'ticket_id': str(r[TICKET_ID]),
        'subject': r[SUBJECT] or '',
        'description': r[DESC] or '',
        'status': r[STATUS] or '',
        'resolution': r[RESOLUTION] or '',
        'priority': r[PRIORITY] or '',
        'product': r[PRODUCT] or '',
        'channel': r[CHANNEL] or '',
        'text': r['text'] or ''
    })

# closed cases only
closed_mask = df[STATUS].astype(str).str.strip().str.lower().str.contains('closed|resolved')
closed_df = df[closed_mask].copy()
closed_df['text'] = (closed_df[SUBJECT].astype(str) + '\n' + closed_df[DESC].astype(str)).str.strip()
closed_df = closed_df[closed_df['text'].str.strip()!='']
print('Closed rows indexed:', len(closed_df))

if len(closed_df) == 0:
    print('No closed cases to use as index. Exiting.')
    sys.exit(1)

closed_texts = closed_df['text'].tolist()
closed_ids = closed_df[TICKET_ID].astype(str).tolist()
closed_subjects = closed_df[SUBJECT].tolist()
closed_resolutions = closed_df[RESOLUTION].tolist()

print('Vectorizing closed texts (TF-IDF)')
vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1,2), stop_words='english')
X_closed = vectorizer.fit_transform(closed_texts)

print('Fitting NearestNeighbors')
nn = NearestNeighbors(n_neighbors=6, metric='cosine', n_jobs=-1)
nn.fit(X_closed)

# Transform all tickets and query against closed index
all_texts = [t['text'] for t in tickets]
X_all = vectorizer.transform(all_texts)
print('Querying nearest closed neighbors for all tickets...')
dists, idxs = nn.kneighbors(X_all, return_distance=True)

suggestions = {}
for i, t in enumerate(tickets):
    neigh = []
    for dist, j in zip(dists[i], idxs[i]):
        score = round(1 - float(dist), 4)
        neigh.append({
            'ticket_id': str(closed_ids[j]),
            'subject': closed_subjects[j],
            'resolution': closed_resolutions[j],
            'similarity': score
        })
    # exclude empty resolution results
    suggestions[str(t['ticket_id'])] = [n for n in neigh if n.get('resolution')]

# Save all_tickets.json without full text (trim to 2000 chars for safety)
for t in tickets:
    if len(t['description']) > 2000:
        t['description'] = t['description'][:2000]
    t.pop('text', None)

with open(OUT_DIR / 'all_tickets.json', 'w', encoding='utf-8') as f:
    json.dump(tickets, f, ensure_ascii=False)
with open(OUT_DIR / 'suggestions_for_all.json', 'w', encoding='utf-8') as f:
    json.dump(suggestions, f, ensure_ascii=False)

print('Wrote all_tickets.json and suggestions_for_all.json to', OUT_DIR)
