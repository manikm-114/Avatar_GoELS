import argparse, csv, json
from pathlib import Path
MODELS = ['Qwen__Qwen3-VL-4B-Instruct', 'llava-hf__llava-onevision-qwen2-7b-ov-hf', 'OpenGVLab__InternVL3-14B', 'Qwen__Qwen2-VL-7B-Instruct']

def norm(s: str) -> str:
    return ' '.join((s or '').strip().lower().split())

def read_csv(p: Path):
    with p.open('r', encoding='utf-8', errors='replace') as f:
        return list(csv.DictReader(f))

def write_csv(p: Path, rows):
    if not rows:
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

def load_json(p: Path):
    with p.open('r', encoding='utf-8', errors='replace') as f:
        return json.load(f)

def to_concept_list(parsed):
    if not parsed:
        return []
    if isinstance(parsed, dict) and 'concepts' in parsed and isinstance(parsed['concepts'], list):
        out = []
        for c in parsed['concepts']:
            if isinstance(c, dict):
                t = c.get('term')
                cat = c.get('category')
                if t:
                    out.append((t, cat or ''))
        return out
    if isinstance(parsed, dict) and parsed.get('term'):
        return [(parsed.get('term'), parsed.get('category', ''))]
    return []

def to_triple_list(parsed):
    if not parsed:
        return []
    if isinstance(parsed, dict) and 'triples' in parsed and isinstance(parsed['triples'], list):
        out = []
        for t in parsed['triples']:
            if isinstance(t, dict) and t.get('s') and t.get('p') and t.get('o'):
                out.append((t['s'], t['p'], t['o'], t.get('confidence', ''), t.get('modalities', ''), t.get('evidence', '')))
        return out
    if isinstance(parsed, dict) and parsed.get('s') and parsed.get('p') and parsed.get('o'):
        return [(parsed['s'], parsed['p'], parsed['o'], parsed.get('confidence', ''), parsed.get('modalities', ''), parsed.get('evidence', ''))]
    return []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='by_slide root')
    ap.add_argument('--phase2_out', required=True)
    ap.add_argument('--slides', required=True, help='Comma list like "Lecture 4:Slide28,Lecture 21:Slide42"')
    ap.add_argument('--out', default='phase4_out')
    args = ap.parse_args()
    root = Path(args.root)
    phase2 = Path(args.phase2_out)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cg = read_csv(phase2 / 'tables' / 'concept_grounding.csv')
    tg = read_csv(phase2 / 'tables' / 'triple_entity_grounding.csv')
    concept_ground = {}
    for r in cg:
        concept_ground[r['lecture'], r['slide_id'], r['model'], norm(r['term'])] = r['grounding']
    triple_valid = {}
    for r in tg:
        triple_valid[r['lecture'], r['slide_id'], r['model'], norm(r['s']), norm(r['p']), norm(r['o'])] = int(r['triple_valid'])
    targets = []
    for item in args.slides.split(','):
        item = item.strip()
        if not item:
            continue
        lec, sid = item.split(':')
        targets.append((lec.strip(), sid.strip()))
    rows = []
    for lec, sid in targets:
        jpath = root / lec / f'{sid}.json'
        payload = load_json(jpath)
        for m in MODELS:
            mp = payload.get('models', {}).get(m, {})
            c_parsed = (mp.get('concepts') or {}).get('parsed') if isinstance(mp.get('concepts'), dict) else None
            t_parsed = (mp.get('triples') or {}).get('parsed') if isinstance(mp.get('triples'), dict) else None
            for term, cat in to_concept_list(c_parsed):
                g = concept_ground.get((lec, sid, m, norm(term)), 'unknown')
                rows.append({'lecture': lec, 'slide_id': sid, 'model': m, 'type': 'concept', 'term': term, 'category': cat, 'grounding': g, 's': '', 'p': '', 'o': '', 'triple_valid': '', 'confidence': '', 'modalities': '', 'evidence': ''})
            for s, p, o, conf, mods, ev in to_triple_list(t_parsed):
                tv = triple_valid.get((lec, sid, m, norm(s), norm(p), norm(o)), 0)
                rows.append({'lecture': lec, 'slide_id': sid, 'model': m, 'type': 'triple', 'term': '', 'category': '', 'grounding': '', 's': s, 'p': p, 'o': o, 'triple_valid': tv, 'confidence': conf, 'modalities': str(mods), 'evidence': str(ev)})
    write_csv(out / 'qual_evidence_cards.csv', rows)
    print('[OK] Wrote:', out / 'qual_evidence_cards.csv')
if __name__ == '__main__':
    main()