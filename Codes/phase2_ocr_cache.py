import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List
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
    out = []
    for p in root.rglob('*.json'):
        if p.name.lower().startswith('slide') and p.parent.name.lower().startswith('lecture'):
            out.append(p)
    return sorted(out)

def run_tesseract(image_path: Path) -> str:
    cmd = ['tesseract', str(image_path), 'stdout', '-l', 'eng']
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode != 0:
        err = (res.stderr or b'').decode('utf-8', errors='replace').strip()
        raise RuntimeError(err or 'tesseract failed')
    return (res.stdout or b'').decode('utf-8', errors='replace')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='Root containing Lecture*/Slide*.json')
    ap.add_argument('--out', default='phase2_out', help='Output folder')
    ap.add_argument('--limit', type=int, default=0, help='If >0, only OCR this many slides (debug)')
    ap.add_argument('--force', action='store_true', help='Re-run OCR even if cached file exists')
    args = ap.parse_args()
    root = Path(args.root)
    out_dir = Path(args.out)
    ocr_dir = out_dir / 'ocr_cache'
    ocr_dir.mkdir(parents=True, exist_ok=True)
    slides = find_slide_jsons(root)
    if args.limit and args.limit > 0:
        slides = slides[:args.limit]
    ok, fail, skipped = (0, 0, 0)
    for sf in slides:
        sj = load_json_relaxed(sf)
        lecture = sj.get('lecture') or sf.parent.name
        slide_id = sj.get('slide_id') or sf.stem
        paths = sj.get('paths') or {}
        img = paths.get('image')
        if not isinstance(img, str) or not img.strip():
            fail += 1
            continue
        img_path = Path(img)
        if not img_path.exists():
            fail += 1
            continue
        lec_dir = ocr_dir / lecture
        lec_dir.mkdir(parents=True, exist_ok=True)
        out_txt = lec_dir / f'{slide_id}.txt'
        if out_txt.exists() and (not args.force):
            skipped += 1
            continue
        try:
            text = run_tesseract(img_path)
            out_txt.write_text(text, encoding='utf-8', errors='replace')
            ok += 1
        except Exception as e:
            out_txt.write_text(f'[OCR_ERROR] {e}', encoding='utf-8', errors='replace')
            fail += 1
        if (ok + fail + skipped) % 50 == 0:
            print(f'[PROGRESS] done={ok + fail + skipped} ok={ok} fail={fail} skipped={skipped}')
    print('[DONE]')
    print(f'ok={ok} fail={fail} skipped={skipped}')
    print('ocr_cache at:', ocr_dir)
if __name__ == '__main__':
    main()