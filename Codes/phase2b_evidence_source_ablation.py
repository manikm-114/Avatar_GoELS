import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Tuple, Any, List
MODELS = ['Qwen__Qwen3-VL-4B-Instruct', 'llava-hf__llava-onevision-qwen2-7b-ov-hf', 'OpenGVLab__InternVL3-14B', 'Qwen__Qwen2-VL-7B-Instruct']
EVIDENCE_MODES = ['transcript_only', 'ocr_only', 'both']
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
    out: List[Path] = []
    for p in root.rglob('*.json'):
        if p.name.lower().startswith('slide') and p.parent.name.lower().startswith('lecture'):
            out.append(p)
    return sorted(out)

def read_csv_dicts(p: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with p.open('r', encoding='utf-8', errors='replace', newline='') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

def select_evidence(meta: Dict[str, str], mode: str) -> Tuple[str, str]:
    tr = meta.get('transcript', '') or ''
    oc = meta.get('ocr', '') or ''
    if mode == 'transcript_only':
        oc = ''
    elif mode == 'ocr_only':
        tr = ''
    elif mode == 'both':
        pass
    else:
        raise ValueError(f'Unknown evidence mode: {mode}')
    return (tr, oc)

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
    slides_total = len(slide_meta)
    slides_with_transcript = sum((1 for v in slide_meta.values() if norm(v.get('transcript', ''))))
    slides_with_ocr = sum((1 for v in slide_meta.values() if norm(v.get('ocr', ''))))
    concepts_rows = read_csv_dicts(phase1_out / 'concepts_long.csv')
    triples_rows = read_csv_dicts(phase1_out / 'triples_long.csv')
    agg: Dict[str, Dict[str, defaultdict]] = {mode: {m: defaultdict(int) for m in MODELS} for mode in EVIDENCE_MODES}

    def where(in_tr: bool, in_ocr: bool) -> str:
        return 'transcript' if in_tr else 'ocr' if in_ocr else 'neither'
    for mode in EVIDENCE_MODES:
        for r in concepts_rows:
            lecture, slide_id, model, term = (r['lecture'], r['slide_id'], r['model'], r['term'])
            if model not in MODELS:
                continue
            meta = slide_meta.get((lecture, slide_id), {'transcript': '', 'ocr': ''})
            tr, oc = select_evidence(meta, mode)
            in_tr = contains_ci(tr, term)
            in_ocr = contains_ci(oc, term)
            grounded = where(in_tr, in_ocr)
            agg[mode][model]['concept_total'] += 1
            if grounded == 'neither':
                agg[mode][model]['concept_ungrounded'] += 1
                agg[mode][model]['hallucinated_items'] += 1
            else:
                agg[mode][model]['concept_grounded'] += 1
            agg[mode][model]['total_items'] += 1
        for r in triples_rows:
            lecture, slide_id, model = (r['lecture'], r['slide_id'], r['model'])
            if model not in MODELS:
                continue
            s, o = (r.get('s', ''), r.get('o', ''))
            meta = slide_meta.get((lecture, slide_id), {'transcript': '', 'ocr': ''})
            tr, oc = select_evidence(meta, mode)
            s_ground = where(contains_ci(tr, s), contains_ci(oc, s))
            o_ground = where(contains_ci(tr, o), contains_ci(oc, o))
            triple_valid = int(s_ground != 'neither' and o_ground != 'neither')
            agg[mode][model]['triple_total'] += 1
            agg[mode][model]['triple_valid'] += triple_valid
            if triple_valid == 0:
                agg[mode][model]['triple_invalid'] += 1
                agg[mode][model]['hallucinated_items'] += 1
            agg[mode][model]['total_items'] += 1
    by_model_rows: List[Dict[str, Any]] = []
    for mode in EVIDENCE_MODES:
        for m in MODELS:
            total_items = int(agg[mode][m]['total_items'])
            halluc = int(agg[mode][m]['hallucinated_items'])
            hp = halluc / total_items if total_items else 0.0
            concept_total = int(agg[mode][m]['concept_total'])
            c_ground = int(agg[mode][m]['concept_grounded'])
            c_unground = int(agg[mode][m]['concept_ungrounded'])
            triple_total = int(agg[mode][m]['triple_total'])
            t_valid = int(agg[mode][m]['triple_valid'])
            t_invalid = int(agg[mode][m]['triple_invalid'])
            by_model_rows.append({'evidence_mode': mode, 'model': m, 'slides_total': slides_total, 'slides_with_transcript': slides_with_transcript, 'slides_with_ocr': slides_with_ocr, 'concept_total': concept_total, 'concept_grounded': c_ground, 'concept_ungrounded': c_unground, 'concept_grounded_rate': round(c_ground / concept_total, 6) if concept_total else 0.0, 'triple_total': triple_total, 'triple_valid': t_valid, 'triple_invalid': t_invalid, 'triple_valid_rate': round(t_valid / triple_total, 6) if triple_total else 0.0, 'hallucinated_items': halluc, 'total_items': total_items, 'hallucination_penalty': round(hp, 6)})
    out_by_model = tables_dir / 'evidence_source_ablation_by_model.csv'
    write_csv(out_by_model, by_model_rows)
    overall_rows: List[Dict[str, Any]] = []
    for mode in EVIDENCE_MODES:
        sum_concept_total = sum((int(agg[mode][m]['concept_total']) for m in MODELS))
        sum_c_ground = sum((int(agg[mode][m]['concept_grounded']) for m in MODELS))
        sum_c_unground = sum((int(agg[mode][m]['concept_ungrounded']) for m in MODELS))
        sum_triple_total = sum((int(agg[mode][m]['triple_total']) for m in MODELS))
        sum_t_valid = sum((int(agg[mode][m]['triple_valid']) for m in MODELS))
        sum_t_invalid = sum((int(agg[mode][m]['triple_invalid']) for m in MODELS))
        sum_total_items = sum((int(agg[mode][m]['total_items']) for m in MODELS))
        sum_halluc = sum((int(agg[mode][m]['hallucinated_items']) for m in MODELS))
        hp = sum_halluc / sum_total_items if sum_total_items else 0.0
        overall_rows.append({'evidence_mode': mode, 'slides_total': slides_total, 'slides_with_transcript': slides_with_transcript, 'slides_with_ocr': slides_with_ocr, 'concept_total': sum_concept_total, 'concept_grounded': sum_c_ground, 'concept_ungrounded': sum_c_unground, 'concept_grounded_rate': round(sum_c_ground / sum_concept_total, 6) if sum_concept_total else 0.0, 'triple_total': sum_triple_total, 'triple_valid': sum_t_valid, 'triple_invalid': sum_t_invalid, 'triple_valid_rate': round(sum_t_valid / sum_triple_total, 6) if sum_triple_total else 0.0, 'hallucinated_items': sum_halluc, 'total_items': sum_total_items, 'hallucination_penalty': round(hp, 6)})
    out_overall = tables_dir / 'evidence_source_ablation_overall.csv'
    write_csv(out_overall, overall_rows)
    md = out_dir / 'phase2b_evidence_source_ablation.md'
    with md.open('w', encoding='utf-8') as f:
        f.write('# Phase 2b Summary (Evidence-source ablation)\n\n')
        f.write(f'- Slides: {slides_total}\n')
        f.write(f'- Slides with transcript non-empty: {slides_with_transcript}\n')
        f.write(f'- Slides with OCR non-empty: {slides_with_ocr}\n')
        f.write(f'- Concepts rows (phase1): {len(concepts_rows)}\n')
        f.write(f'- Triples rows (phase1): {len(triples_rows)}\n\n')
        f.write('## Overall (aggregated across models)\n\n')
        f.write('| evidence_mode | concept_grounded_rate | triple_valid_rate | hallucination_penalty |\n')
        f.write('|---|---:|---:|---:|\n')
        for r in overall_rows:
            f.write(f'| {r['evidence_mode']} | {r['concept_grounded_rate']} | {r['triple_valid_rate']} | {r['hallucination_penalty']} |\n')
        f.write('\n## By model\n\n')
        f.write('| evidence_mode | model | concept_grounded_rate | triple_valid_rate | hallucination_penalty |\n')
        f.write('|---|---|---:|---:|---:|\n')
        for r in by_model_rows:
            f.write(f'| {r['evidence_mode']} | {r['model']} | {r['concept_grounded_rate']} | {r['triple_valid_rate']} | {r['hallucination_penalty']} |\n')
    print('[OK] Wrote:')
    print(' -', out_by_model)
    print(' -', out_overall)
    print(' -', md)
if __name__ == '__main__':
    main()