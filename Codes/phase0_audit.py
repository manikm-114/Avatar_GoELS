import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
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

def find_slide_jsons(root: Path) -> List[Path]:
    out: List[Path] = []
    for p in root.rglob('*.json'):
        if p.name.lower().startswith('slide') and p.parent.name.lower().startswith('lecture'):
            out.append(p)
    return sorted(out)

def model_key_exists(models_dict: Dict[str, Any], key: str) -> bool:
    return isinstance(models_dict, dict) and key in models_dict

def safe_exists(path_str: Any) -> bool:
    if not isinstance(path_str, str) or not path_str.strip():
        return False
    try:
        return Path(path_str).exists()
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='Dataset root containing Lecture*/Slide*.json')
    ap.add_argument('--out', default='phase0_out', help='Output folder (created if missing)')
    args = ap.parse_args()
    root = Path(args.root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    slide_files = find_slide_jsons(root)
    if not slide_files:
        raise SystemExit(f'No Lecture*/Slide*.json found under: {root}')
    TARGET_MODELS = ['Qwen__Qwen3-VL-4B-Instruct', 'llava-hf__llava-onevision-qwen2-7b-ov-hf', 'OpenGVLab__InternVL3-14B', 'Qwen__Qwen2-VL-7B-Instruct']
    TEXT_ONLY_KEY = 'llava-hf__llava-onevision-qwen2-7b-ov-hf__text_only'
    missing_counts = {m: 0 for m in TARGET_MODELS}
    missing_paths_image = 0
    missing_paths_text = 0
    slides_with_text_only = 0
    slides_models_count_dist: Dict[int, int] = {}
    rows: List[Dict[str, Any]] = []
    for sf in slide_files:
        sj = load_json_relaxed(sf)
        lecture = sj.get('lecture') or sf.parent.name
        slide_id = sj.get('slide_id') or sf.stem
        paths = sj.get('paths') or {}
        img_path = paths.get('image')
        txt_path = paths.get('text')
        has_img = safe_exists(img_path)
        has_txt = safe_exists(txt_path)
        if not has_img:
            missing_paths_image += 1
        if not has_txt:
            missing_paths_text += 1
        models = sj.get('models') or {}
        if not isinstance(models, dict):
            models = {}
        n_models_in_json = len(models)
        slides_models_count_dist[n_models_in_json] = slides_models_count_dist.get(n_models_in_json, 0) + 1
        has_text_only = int(model_key_exists(models, TEXT_ONLY_KEY))
        if has_text_only:
            slides_with_text_only += 1
        present = {}
        for m in TARGET_MODELS:
            ok = model_key_exists(models, m)
            present[m] = int(ok)
            if not ok:
                missing_counts[m] += 1
        rows.append({'lecture': lecture, 'slide_id': slide_id, 'slide_json': str(sf), 'has_image_file': int(has_img), 'has_text_file': int(has_txt), 'models_in_json': n_models_in_json, 'has_text_only_key': has_text_only, 'has_Qwen3_VL_4B': present['Qwen__Qwen3-VL-4B-Instruct'], 'has_LLaVA_OneVision': present['llava-hf__llava-onevision-qwen2-7b-ov-hf'], 'has_InternVL3_14B': present['OpenGVLab__InternVL3-14B'], 'has_Qwen2_VL_7B': present['Qwen__Qwen2-VL-7B-Instruct']})
    manifest_path = out_dir / 'phase0_manifest.csv'
    with manifest_path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    report_path = out_dir / 'phase0_missing_report.md'
    total = len(rows)
    with report_path.open('w', encoding='utf-8') as f:
        f.write('# Phase 0 Audit Report (Merged Slide JSONs)\n\n')
        f.write(f'- Root scanned: `{root}`\n')
        f.write(f'- Slides found: **{total}**\n\n')
        f.write('## Path checks\n\n')
        f.write(f'- Slides missing image file: **{missing_paths_image}**\n')
        f.write(f'- Slides missing text file: **{missing_paths_text}**\n\n')
        f.write('## Target VLM keys (exact match)\n\n')
        for m in TARGET_MODELS:
            f.write(f'- Missing `{m}`: **{missing_counts[m]} / {total}**\n')
        f.write('\n')
        f.write('## Special keys\n\n')
        f.write(f'- Slides containing `{TEXT_ONLY_KEY}`: **{slides_with_text_only} / {total}**\n\n')
        f.write('## Distribution: number of keys under `models` per slide JSON\n\n')
        for n in sorted(slides_models_count_dist.keys()):
            f.write(f'- {n} model-keys: {slides_models_count_dist[n]} slides\n')
        f.write('\n')
        f.write('## Notes\n')
        f.write('- This audit uses exact-key matching for the 4 target VLMs.\n')
        f.write('- The `__text_only` entry (if present) is tracked but is not treated as a VLM.\n')
        f.write('- See `phase0_manifest.csv` for per-slide details.\n')
    print('[OK] Wrote:')
    print(' -', manifest_path)
    print(' -', report_path)
if __name__ == '__main__':
    main()