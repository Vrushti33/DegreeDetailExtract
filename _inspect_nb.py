import json, sys

nb = json.load(open('DegreeDetailExtract_Training.ipynb', encoding='utf-8'))

for i, c in enumerate(nb['cells']):
    src = ''.join(c.get('source', []))
    if 'GradScaler' in src or 'Seq2SeqTrainingArguments' in src:
        sys.stdout.buffer.write(f'=== Cell {i} (id={c.get("id","")}) ===\n'.encode('utf-8'))
        sys.stdout.buffer.write(src.encode('utf-8'))
        sys.stdout.buffer.write(b'\n\n')

sys.stdout.buffer.write(b'Notebook JSON valid.\n')
