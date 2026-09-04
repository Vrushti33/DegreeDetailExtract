import json, sys

nb = json.load(open('DegreeDetailExtract_Training.ipynb', encoding='utf-8'))
targets = {'cell-s3-tokens', 'cell-s3-train'}
for i, c in enumerate(nb['cells']):
    if c.get('id','') in targets:
        src = ''.join(c['source'])
        sys.stdout.buffer.write(f'=== Cell {i} ({c["id"]}) ===\n'.encode('utf-8'))
        sys.stdout.buffer.write(src.encode('utf-8'))
        sys.stdout.buffer.write(b'\n\n')
