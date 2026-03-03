import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Tuple, Any, List
MODELS = ['Qwen__Qwen3-VL-4B-Instruct', 'llava-hf__llava-onevision-qwen2-7b-ov-hf', 'OpenGVLab__InternVL3-14B', 'Qwen__Qwen2-VL-7B-Instruct']
_NAN_RE = re.compile('(?<!")\\bNaN\\b(?!")')
_INF_RE = re.compile('(?<!")\\bInfinity\\b(?!")')
_NINF_RE = re.compile('(?<!")\\b-Infinity\\b(?!")')

def load_json_relaxed(p: Path) -> Dict[str, Any]:
    raw = p.read_text(encoding='utf-8', errors='replace')
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raw = _NINF_RE.sub('null', raw)
        raw = _INF_RE.sub('null', raw)
        raw = _NAN_RE.sub('null', raw)
        return json.loads(raw)

def norm(s: str) -> str:
    return re.sub('\\s+', ' ', (s or '').strip().lower())

def contains_ci(hay: str, needle: str) -> bool:
    h = norm(hay)
    n = norm(needle)
    return bool(n) and n in h

def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return ''

def find_slide_jsons(root: Path) -> List[Path]:
    out = []
    for p in root.rglob('*.json'):
        if p.name.lower().startswith('slide') and p.parent.name.lower().startswith('lecture'):
            out.append(p)
    return sorted(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='..\\by_slide (Lecture*/Slide*.json)')
    ap.add_argument('--phase1_out', required=True, help='phase1_out folder with concepts_long.csv and triples_long.csv')
    ap.add_argument('--ocr_cache', required=True, help='phase2_out\\ocr_cache')
    ap.add_argument('--out', default='phase2_out', help='output folder (tables written here)')
    args = ap.parse_args()
    root = Path(args.root)
    phase1_out = Path(args.phase1_out)
    ocr_cache = Path(args.ocr_cache)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = out_dir / 'tables'
    tables_dir.mkdir(parents=True, exist_ok=True)
    slide_meta: Dict[Tuple[str, str], Dict[str, str]] = {}
    for sf in find_slide_jsons(root):
        sj = load_json_relaxed(sf)
        lecture = sj.get('lecture') or sf.parent.name
        slide_id = sj.get('slide_id') or sf.stem
        paths = sj.get('paths') or {}
        txt_path = Path(paths['text']) if isinstance(paths.get('text'), str) else None
        transcript = load_text(txt_path) if txt_path else ''
        ocr_path = ocr_cache / lecture / f'{slide_id}.txt'
        ocr_text = load_text(ocr_path) if ocr_path.exists() else ''
        slide_meta[lecture, slide_id] = {'transcript': transcript, 'ocr': ocr_text}
    concepts_in = phase1_out / 'concepts_long.csv'
    triples_in = phase1_out / 'triples_long.csv'
    concepts_rows = []
    with concepts_in.open('r', encoding='utf-8', errors='replace') as f:
        for r in csv.DictReader(f):
            concepts_rows.append(r)
    triples_rows = []
    with triples_in.open('r', encoding='utf-8', errors='replace') as f:
        for r in csv.DictReader(f):
            triples_rows.append(r)
    concept_ground_rows = []
    triple_entity_ground_rows = []
    agg = {m: defaultdict(int) for m in MODELS}
    for r in concepts_rows:
        lecture, slide_id, model, term = (r['lecture'], r['slide_id'], r['model'], r['term'])
        meta = slide_meta.get((lecture, slide_id), {'transcript': '', 'ocr': ''})
        tr, oc = (meta['transcript'], meta['ocr'])
        in_tr = contains_ci(tr, term)
        in_ocr = contains_ci(oc, term)
        grounded = 'transcript' if in_tr else 'ocr' if in_ocr else 'neither'
        concept_ground_rows.append({'lecture': lecture, 'slide_id': slide_id, 'model': model, 'term': term, 'category': r.get('category', ''), 'grounding': grounded})
        if model in agg:
            agg[model]['concept_total'] += 1
            agg[model][f'concept_{grounded}'] += 1
            if grounded == 'neither':
                agg[model]['hallucinated_items'] += 1
            agg[model]['total_items'] += 1

    def where(in_tr: bool, in_ocr: bool) -> str:
        return 'transcript' if in_tr else 'ocr' if in_ocr else 'neither'
    for r in triples_rows:
        lecture, slide_id, model = (r['lecture'], r['slide_id'], r['model'])
        s, p, o = (r['s'], r['p'], r['o'])
        meta = slide_meta.get((lecture, slide_id), {'transcript': '', 'ocr': ''})
        tr, oc = (meta['transcript'], meta['ocr'])
        s_ground = where(contains_ci(tr, s), contains_ci(oc, s))
        o_ground = where(contains_ci(tr, o), contains_ci(oc, o))
        triple_valid = int(s_ground != 'neither' and o_ground != 'neither')
        triple_entity_ground_rows.append({'lecture': lecture, 'slide_id': slide_id, 'model': model, 's': s, 'p': p, 'o': o, 's_grounding': s_ground, 'o_grounding': o_ground, 'triple_valid': triple_valid, 'predicate_allowed': r.get('predicate_allowed', ''), 'has_image_modality': r.get('has_image_modality', ''), 'confidence': r.get('confidence', '')})
        if model in agg:
            agg[model]['triple_total'] += 1
            agg[model][f'triple_s_{s_ground}'] += 1
            agg[model][f'triple_o_{o_ground}'] += 1
            agg[model]['triple_valid'] += triple_valid
            if triple_valid == 0:
                agg[model]['hallucinated_items'] += 1
            agg[model]['total_items'] += 1

    def write_csv(path: Path, rows):
        if not rows:
            return
        with path.open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    write_csv(tables_dir / 'concept_grounding.csv', concept_ground_rows)
    write_csv(tables_dir / 'triple_entity_grounding.csv', triple_entity_ground_rows)
    model_summary = []
    for m in MODELS:
        total_items = agg[m]['total_items']
        halluc = agg[m]['hallucinated_items']
        hp = halluc / total_items if total_items else 0.0
        model_summary.append({'model': m, 'concept_total': agg[m]['concept_total'], 'concept_transcript': agg[m]['concept_transcript'], 'concept_ocr': agg[m]['concept_ocr'], 'concept_neither': agg[m]['concept_neither'], 'triple_total': agg[m]['triple_total'], 'triple_valid': agg[m]['triple_valid'], 'hallucinated_items': halluc, 'total_items': total_items, 'hallucination_penalty': round(hp, 6)})
    write_csv(tables_dir / 'model_grounding_summary.csv', model_summary)
    md = out_dir / 'phase2_summary.md'
    with md.open('w', encoding='utf-8') as f:
        f.write('# Phase 2 Summary (Grounding + Hallucination)\n\n')
        f.write(f'- Slides: {len(slide_meta)}\n')
        f.write(f'- Concepts rows: {len(concepts_rows)}\n')
        f.write(f'- Triples rows: {len(triples_rows)}\n\n')
        f.write('| Model | concept_neither | triple_total | triple_valid | hallucination_penalty |\n')
        f.write('|---|---:|---:|---:|---:|\n')
        for r in model_summary:
            f.write(f'| {r['model']} | {r['concept_neither']} | {r['triple_total']} | {r['triple_valid']} | {r['hallucination_penalty']} |\n')
    print('[OK] Wrote:')
    print(' -', tables_dir / 'concept_grounding.csv')
    print(' -', tables_dir / 'triple_entity_grounding.csv')
    print(' -', tables_dir / 'model_grounding_summary.csv')
    print(' -', md)
if __name__ == '__main__':
    main()