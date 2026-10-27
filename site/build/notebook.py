"""Bundle site/notes/*.md into site/data/notebook.js for the Writer's notebook page.
Run after any page's notes change:  python site/build/notebook.py"""
import json
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
ORDER = ['index', 'scale', 'geography', 'sectors', 'ownership', 'markets', 'startups', 'time', 'context']
TITLES = {
    'index': 'Overview', 'scale': 'Scale', 'geography': 'Geography', 'sectors': 'Sectors',
    'ownership': 'Ownership', 'markets': 'Stock markets', 'startups': 'Startups & AI',
    'time': 'Change over time', 'context': 'Big picture',
}

notes = []
files = {p.stem: p for p in (SITE / 'notes').glob('*.md')}
for key in ORDER + sorted(set(files) - set(ORDER)):
    if key in files:
        notes.append({'key': key, 'title': TITLES.get(key, key.title()), 'page': f'{key}.html',
                      'md': files[key].read_text(encoding='utf-8')})

out = SITE / 'data' / 'notebook.js'
out.write_text('window.ATLAS.notebook = ' + json.dumps({'notes': notes}, ensure_ascii=False) + ';\n', encoding='utf-8')
print(f'{len(notes)} notes -> {out}')
