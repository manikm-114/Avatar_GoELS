from __future__ import annotations
import argparse
import csv
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
TARGET_MODELS = ['Qwen__Qwen3-VL-4B-Instruct', 'llava-hf__llava-onevision-qwen2-7b-ov-hf', 'OpenGVLab__InternVL3-14B', 'Qwen__Qwen2-VL-7B-Instruct']
PREDICATE_ALLOWED_SET = {'uses', 'via', 'represents', 'depends_on', 'measures', 'produces', 'reconstructs_with'}

def short_model(name: str) -> str:
    n = (name or '').lower()
    if n.startswith('llava-hf__llava-onevision') or 'llava-onevision' in n or ('llava' in n and 'onevision' in n):
        return 'LLaVA-OneVision'
    if 'internvl3-14b' in n or ('opengvlab' in n and 'internvl3' in n):
        return 'InternVL3-14B'
    if 'qwen3' in n and 'vl' in n:
        return 'Qwen3-VL-4B'
    if 'qwen2' in n and 'vl' in n:
        return 'Qwen2-VL-7B'
    return name

def safe_read_text(p: Path) -> str:
    try:
        return p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        try:
            return p.read_text(encoding='utf-8-sig', errors='ignore')
        except Exception:
            return ''

def norm_ws(s: str) -> str:
    return re.sub('\\s+', ' ', s.strip())

def contains_ci(haystack: str, needle: str) -> bool:
    needle = needle.strip()
    if not needle:
        return False
    return needle.lower() in haystack.lower()

def parse_triples(parsed_obj: Any) -> List[Dict[str, Any]]:
    if parsed_obj is None:
        return []
    if isinstance(parsed_obj, dict):
        if 'triples' in parsed_obj and isinstance(parsed_obj['triples'], list):
            triples = parsed_obj['triples']
        elif all((k in parsed_obj for k in ('s', 'p', 'o'))):
            triples = [parsed_obj]
        else:
            return []
    elif isinstance(parsed_obj, list):
        triples = parsed_obj
    else:
        return []
    out: List[Dict[str, Any]] = []
    for t in triples:
        if not isinstance(t, dict):
            continue
        s = t.get('s')
        p = t.get('p')
        o = t.get('o')
        if not isinstance(s, str) or not isinstance(p, str) or (not isinstance(o, str)):
            continue
        confidence = t.get('confidence', None)
        try:
            confidence = float(confidence) if confidence is not None else None
        except Exception:
            confidence = None
        modalities = t.get('modalities', [])
        if modalities is None:
            modalities = []
        if isinstance(modalities, str):
            try:
                modalities = json.loads(modalities)
            except Exception:
                modalities = re.findall('[A-Za-z]+', modalities)
        if not isinstance(modalities, list):
            modalities = []
        modalities = [str(m).lower().strip() for m in modalities if str(m).strip()]
        evidence = t.get('evidence', '')
        if isinstance(evidence, list):
            evidence = ' | '.join([str(x) for x in evidence if str(x).strip()])
        elif evidence is None:
            evidence = ''
        evidence = str(evidence)
        out.append({'s': norm_ws(s), 'p': norm_ws(p), 'o': norm_ws(o), 'confidence': confidence, 'modalities': modalities, 'evidence': norm_ws(evidence)})
    return out

def load_slide_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding='utf-8', errors='ignore'))
    except Exception:
        return None

def iter_slide_jsons(root: Path) -> List[Path]:
    paths = sorted(root.glob('Lecture */Slide*.json'))
    if paths:
        return paths
    paths = sorted(root.glob('Lecture*/Slide*.json'))
    return paths

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='Root folder containing Lecture X/SlideY.json')
    ap.add_argument('--out', required=True, help='Output folder, e.g., phase4_out')
    ap.add_argument('--ocr-cache', default=None, help='OCR cache root (phase2_out/ocr_cache). If omitted, defaults to <out>/../phase2_out/ocr_cache')
    ap.add_argument('--only-target-models', action='store_true', help='If set, only process the 4 target VLMs.')
    ap.add_argument('--topk', type=int, default=50, help='Top-k slides for ranking')
    args = ap.parse_args()
    root = Path(args.root).resolve()
    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.ocr_cache is None:
        ocr_cache = (out_dir.parent / 'phase2_out' / 'ocr_cache').resolve()
    else:
        ocr_cache = Path(args.ocr_cache).resolve()
    slide_paths = iter_slide_jsons(root)
    if not slide_paths:
        raise SystemExit(f'No Lecture*/Slide*.json found under: {root}')
    triples_long_path = out_dir / 'triples_with_modalities_long.csv'
    slide_stats: Dict[Tuple[str, str], Dict[str, Any]] = {}
    model_agg: Dict[str, Dict[str, int]] = {}

    def agg_get(m: str) -> Dict[str, int]:
        if m not in model_agg:
            model_agg[m] = {'triples_total': 0, 'img_claim_n': 0, 'ocr_evidenced_n': 0, 'hallucinated_img_claim_n': 0}
        return model_agg[m]
    with triples_long_path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['lecture', 'slide_id', 'model', 'model_short', 's', 'p', 'o', 'predicate_allowed', 'has_image_modality', 'confidence', 'modalities_json', 'evidence', 's_in_transcript', 'o_in_transcript', 's_in_ocr', 'o_in_ocr', 'ocr_evidenced', 'hallucinated_entity'])
        for jp in slide_paths:
            payload = load_slide_json(jp)
            if not isinstance(payload, dict):
                continue
            lecture = str(payload.get('lecture', jp.parent.name))
            slide_id = str(payload.get('slide_id', jp.stem))
            paths = payload.get('paths', {}) if isinstance(payload.get('paths', {}), dict) else {}
            img_path = paths.get('image', '')
            txt_path = paths.get('text', '')
            transcript = ''
            if isinstance(txt_path, str) and txt_path.strip():
                transcript = safe_read_text(Path(txt_path))
            else:
                transcript = ''
            ocr_text = ''
            ocr_txt_path = ocr_cache / lecture / f'{slide_id}.txt'
            if ocr_txt_path.exists():
                ocr_text = safe_read_text(ocr_txt_path)
            else:
                ocr_text = ''
            models_obj = payload.get('models', {})
            if not isinstance(models_obj, dict):
                continue
            for model_name, model_payload in models_obj.items():
                if args.only_target_models and model_name not in TARGET_MODELS:
                    continue
                if not isinstance(model_payload, dict):
                    continue
                triples_block = model_payload.get('triples')
                triples_parsed = None
                if isinstance(triples_block, dict):
                    triples_parsed = triples_block.get('parsed')
                triples = parse_triples(triples_parsed)
                if not triples:
                    continue
                mshort = short_model(model_name)
                agg = agg_get(model_name)
                for t in triples:
                    s = t['s']
                    p = t['p']
                    o = t['o']
                    modalities = t['modalities']
                    has_img_mod = 'image' in modalities
                    pred_allowed = p.lower() in PREDICATE_ALLOWED_SET
                    s_in_tr = contains_ci(transcript, s)
                    o_in_tr = contains_ci(transcript, o)
                    s_in_ocr = contains_ci(ocr_text, s)
                    o_in_ocr = contains_ci(ocr_text, o)
                    ocr_evidenced = not s_in_tr and s_in_ocr or (not o_in_tr and o_in_ocr)
                    halluc_entity = not s_in_tr and (not s_in_ocr) or (not o_in_tr and (not o_in_ocr))
                    agg['triples_total'] += 1
                    if has_img_mod:
                        agg['img_claim_n'] += 1
                        if halluc_entity:
                            agg['hallucinated_img_claim_n'] += 1
                    if ocr_evidenced:
                        agg['ocr_evidenced_n'] += 1
                    key = (lecture, slide_id)
                    if key not in slide_stats:
                        slide_stats[key] = {'lecture': lecture, 'slide_id': slide_id, 'slide_json': str(jp.relative_to(root)), 'image_path': img_path, 'text_path': txt_path, 'ocr_evidenced_triples_total': 0, 'triples_total': 0, 'img_claim_triples_total': 0}
                    slide_stats[key]['triples_total'] += 1
                    if ocr_evidenced:
                        slide_stats[key]['ocr_evidenced_triples_total'] += 1
                    if has_img_mod:
                        slide_stats[key]['img_claim_triples_total'] += 1
                    w.writerow([lecture, slide_id, model_name, mshort, s, p, o, int(pred_allowed), int(has_img_mod), '' if t['confidence'] is None else t['confidence'], json.dumps(modalities, ensure_ascii=False), t['evidence'], int(s_in_tr), int(o_in_tr), int(s_in_ocr), int(o_in_ocr), int(ocr_evidenced), int(halluc_entity)])
    model_csv = out_dir / 'model_modality_claim_vs_ocr_evidence.csv'
    with model_csv.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['model', 'model_short', 'triples_total', 'img_claim_n', 'img_claim_rate', 'ocr_evidenced_n', 'ocr_evidenced_rate', 'hallucinated_img_claim_n', 'hallucinated_img_claim_rate'])
        for m in sorted(model_agg.keys()):
            a = model_agg[m]
            total = a['triples_total']
            img_n = a['img_claim_n']
            ocr_n = a['ocr_evidenced_n']
            hall_img_n = a['hallucinated_img_claim_n']
            img_rate = img_n / total if total else 0.0
            ocr_rate = ocr_n / total if total else 0.0
            hall_img_rate = hall_img_n / img_n if img_n else 0.0
            w.writerow([m, short_model(m), total, img_n, img_rate, ocr_n, ocr_rate, hall_img_n, hall_img_rate])
    ranked_csv = out_dir / 'slides_ranked_ocr_evidenced.csv'
    rows = []
    for _, st in slide_stats.items():
        total = st['triples_total']
        ocr_n = st['ocr_evidenced_triples_total']
        img_n = st['img_claim_triples_total']
        ocr_rate = ocr_n / total if total else 0.0
        img_rate = img_n / total if total else 0.0
        rows.append({**st, 'ocr_evidenced_rate': ocr_rate, 'img_claim_rate': img_rate})
    rows.sort(key=lambda r: (r['ocr_evidenced_rate'], r['ocr_evidenced_triples_total']), reverse=True)
    with ranked_csv.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['lecture', 'slide_id', 'slide_json', 'image_path', 'text_path', 'triples_total', 'ocr_evidenced_triples_total', 'ocr_evidenced_rate', 'img_claim_triples_total', 'img_claim_rate'])
        for r in rows[:max(args.topk, 1)]:
            w.writerow([r['lecture'], r['slide_id'], r['slide_json'], r['image_path'], r['text_path'], r['triples_total'], r['ocr_evidenced_triples_total'], r['ocr_evidenced_rate'], r['img_claim_triples_total'], r['img_claim_rate']])
    md = out_dir / 'phase4_summary.md'
    with md.open('w', encoding='utf-8') as f:
        f.write('# Phase 4 Summary (Modality claims vs OCR-evidenced image use)\n\n')
        f.write(f'- Root scanned: `{root}`\n')
        f.write(f'- OCR cache: `{ocr_cache}`\n\n')
        f.write('## Output files\n\n')
        f.write(f'- `{triples_long_path.name}`\n')
        f.write(f'- `{model_csv.name}`\n')
        f.write(f'- `{ranked_csv.name}`\n\n')
        f.write('## Notes\n\n')
        f.write('- `img_claim_rate` comes from the triple `modalities` field (contains `"image"`).\n')
        f.write('- `ocr_evidenced_rate` counts triples where an entity is absent from transcript but present in OCR.\n')
        f.write('- `hallucinated_img_claim_rate` counts image-claimed triples where an entity is in neither transcript nor OCR.\n')
    print('[OK] Wrote:')
    print(f' - {triples_long_path}')
    print(f' - {model_csv}')
    print(f' - {ranked_csv}')
    print(f' - {md}')
if __name__ == '__main__':
    main()