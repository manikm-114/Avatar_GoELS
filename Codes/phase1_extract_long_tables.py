import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
_NAN_RE = re.compile('(?<!")\\bNaN\\b(?!")')
_INF_RE = re.compile('(?<!")\\bInfinity\\b(?!")')
_NINF_RE = re.compile('(?<!")\\b-Infinity\\b(?!")')
TARGET_MODELS = ['Qwen__Qwen3-VL-4B-Instruct', 'llava-hf__llava-onevision-qwen2-7b-ov-hf', 'OpenGVLab__InternVL3-14B', 'Qwen__Qwen2-VL-7B-Instruct']
TEXT_ONLY_KEY = 'llava-hf__llava-onevision-qwen2-7b-ov-hf__text_only'
ALLOWED_PREDICATES = {'uses', 'via', 'represents', 'depends_on', 'measures', 'produces', 'reconstructs_with'}

def load_json_relaxed(p: Path) -> Dict[str, Any]:
    raw = p.read_text(encoding='utf-8', errors='replace')
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raw = _NINF_RE.sub('null', raw)
        raw = _INF_RE.sub('null', raw)
        raw = _NAN_RE.sub('null', raw)
        return json.loads(raw)

def find_slide_jsons(root: Path) -> List[Path]:
    out = []
    for p in root.rglob('*.json'):
        if p.name.lower().startswith('slide') and p.parent.name.lower().startswith('lecture'):
            out.append(p)
    return sorted(out)

def safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}

def safe_list(x: Any) -> List[Any]:
    return x if isinstance(x, list) else []

def safe_str(x: Any) -> str:
    return x.strip() if isinstance(x, str) else ''

def normalize_concepts(parsed: Any) -> List[Tuple[str, str]]:
    if parsed is None:
        return []
    if isinstance(parsed, dict) and isinstance(parsed.get('concepts'), list):
        out = []
        for it in parsed['concepts']:
            if isinstance(it, dict):
                term = safe_str(it.get('term'))
                cat = safe_str(it.get('category'))
                if term:
                    out.append((term, cat))
        return out
    if isinstance(parsed, dict):
        term = safe_str(parsed.get('term'))
        if term:
            return [(term, safe_str(parsed.get('category')))]
    return []

def normalize_triples(parsed: Any) -> List[Dict[str, Any]]:
    if parsed is None:
        return []
    if isinstance(parsed, dict) and isinstance(parsed.get('triples'), list):
        out = []
        for t in parsed['triples']:
            if isinstance(t, dict):
                s = safe_str(t.get('s'))
                p = safe_str(t.get('p'))
                o = safe_str(t.get('o'))
                if s and p and o:
                    out.append({'s': s, 'p': p, 'o': o, 'confidence': t.get('confidence'), 'modalities': t.get('modalities'), 'evidence': t.get('evidence')})
        return out
    if isinstance(parsed, dict):
        s = safe_str(parsed.get('s'))
        p = safe_str(parsed.get('p'))
        o = safe_str(parsed.get('o'))
        if s and p and o:
            return [{'s': s, 'p': p, 'o': o, 'confidence': parsed.get('confidence'), 'modalities': parsed.get('modalities'), 'evidence': parsed.get('evidence')}]
    return []

def modalities_has_image(m: Any) -> int:
    if not isinstance(m, list):
        return 0
    return 1 if any((isinstance(x, str) and x.lower() == 'image' for x in m)) else 0

def safe_exists(path_str: Any) -> bool:
    if not isinstance(path_str, str) or not path_str.strip():
        return False
    try:
        return Path(path_str).exists()
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='Root containing Lecture*/Slide*.json')
    ap.add_argument('--out', default='phase1_out', help='Output folder')
    args = ap.parse_args()
    root = Path(args.root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = find_slide_jsons(root)
    if not slides:
        raise SystemExit(f'No slides found under {root}')
    concepts_rows: List[Dict[str, Any]] = []
    triples_rows: List[Dict[str, Any]] = []
    coverage_rows: List[Dict[str, Any]] = []
    for sf in slides:
        sj = load_json_relaxed(sf)
        lecture = sj.get('lecture') or sf.parent.name
        slide_id = sj.get('slide_id') or sf.stem
        paths = safe_dict(sj.get('paths'))
        has_img = safe_exists(paths.get('image'))
        has_txt = safe_exists(paths.get('text'))
        models = sj.get('models')
        models = models if isinstance(models, dict) else {}
        cov = {'lecture': lecture, 'slide_id': slide_id, 'slide_json': str(sf), 'has_image': int(has_img), 'has_text': int(has_txt), 'has_text_only_key': int(TEXT_ONLY_KEY in models)}
        for m in TARGET_MODELS:
            payload = models.get(m)
            payload = payload if isinstance(payload, dict) else {}
            concepts_block = payload.get('concepts')
            triples_block = payload.get('triples')
            concepts_block = concepts_block if isinstance(concepts_block, dict) else {}
            triples_block = triples_block if isinstance(triples_block, dict) else {}
            c_parsed = concepts_block.get('parsed')
            t_parsed = triples_block.get('parsed')
            concepts = normalize_concepts(c_parsed)
            triples = normalize_triples(t_parsed)
            cov[f'{m}__has_concepts'] = int(len(concepts) > 0)
            cov[f'{m}__has_triples'] = int(len(triples) > 0)
            for term, cat in concepts:
                concepts_rows.append({'lecture': lecture, 'slide_id': slide_id, 'model': m, 'term': term, 'category': cat})
            for t in triples:
                p = safe_str(t.get('p'))
                triples_rows.append({'lecture': lecture, 'slide_id': slide_id, 'model': m, 's': safe_str(t.get('s')), 'p': p, 'o': safe_str(t.get('o')), 'predicate_allowed': int(p in ALLOWED_PREDICATES), 'has_image_modality': modalities_has_image(t.get('modalities')), 'confidence': t.get('confidence')})
        coverage_rows.append(cov)

    def write_csv(path: Path, rows: List[Dict[str, Any]]):
        if not rows:
            print('[WARN] No rows for', path.name)
            return
        with path.open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    write_csv(out_dir / 'coverage.csv', coverage_rows)
    write_csv(out_dir / 'concepts_long.csv', concepts_rows)
    write_csv(out_dir / 'triples_long.csv', triples_rows)
    print('[OK] Wrote:')
    print(' -', out_dir / 'coverage.csv')
    print(' -', out_dir / 'concepts_long.csv')
    print(' -', out_dir / 'triples_long.csv')
    print(f'[INFO] slides={len(slides)} concepts_rows={len(concepts_rows)} triples_rows={len(triples_rows)}')
if __name__ == '__main__':
    main()