import argparse, csv, json, random, re
from pathlib import Path
from collections import defaultdict
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

def find_slide_jsons(root: Path):
    out = []
    for lec_dir in sorted(root.glob('Lecture *')):
        if not lec_dir.is_dir():
            continue
        for sj in sorted(lec_dir.glob('Slide*.json')):
            out.append(sj)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True, help='by_slide root')
    ap.add_argument('--phase2_out', required=True)
    ap.add_argument('--out', default='phase5_out')
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--per_lecture_cap', type=int, default=3)
    ap.add_argument('--n_image', type=int, default=25)
    ap.add_argument('--n_text', type=int, default=25)
    args = ap.parse_args()
    random.seed(args.seed)
    root = Path(args.root)
    phase2 = Path(args.phase2_out)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    concept_ground = read_csv(phase2 / 'tables' / 'concept_grounding.csv')
    triple_ground = read_csv(phase2 / 'tables' / 'triple_entity_grounding.csv')
    slide_stats = defaultdict(lambda: {'concept_total': 0, 'concept_transcript': 0, 'concept_ocr': 0, 'concept_neither': 0, 'triple_total': 0, 'triple_valid': 0, 'triple_invalid': 0})
    for r in concept_ground:
        lec, sid = (r['lecture'], r['slide_id'])
        g = r['grounding']
        key = (lec, sid)
        slide_stats[key]['concept_total'] += 1
        if g == 'transcript':
            slide_stats[key]['concept_transcript'] += 1
        elif g == 'ocr':
            slide_stats[key]['concept_ocr'] += 1
        elif g == 'neither':
            slide_stats[key]['concept_neither'] += 1
    for r in triple_ground:
        lec, sid = (r['lecture'], r['slide_id'])
        tv = int(str(r['triple_valid']).strip() or '0')
        key = (lec, sid)
        slide_stats[key]['triple_total'] += 1
        if tv == 1:
            slide_stats[key]['triple_valid'] += 1
        else:
            slide_stats[key]['triple_invalid'] += 1
    slide_jsons = find_slide_jsons(root)
    path_map = {}
    for sj in slide_jsons:
        payload = load_json(sj)
        lec = payload.get('lecture')
        sid = payload.get('slide_id')
        if not lec or not sid:
            continue
        paths = payload.get('paths', {})
        path_map[lec, sid] = {'slide_json': str(sj.as_posix()), 'image': paths.get('image', ''), 'text': paths.get('text', '')}
    image_candidates = []
    text_candidates = []
    for (lec, sid), st in slide_stats.items():
        pm = path_map.get((lec, sid))
        if not pm:
            continue
        ctot = st['concept_total'] or 0
        ttot = st['triple_total'] or 0
        c_ocr_rate = st['concept_ocr'] / ctot if ctot else 0.0
        c_neither_rate = st['concept_neither'] / ctot if ctot else 0.0
        c_trans_rate = st['concept_transcript'] / ctot if ctot else 0.0
        t_valid_rate = st['triple_valid'] / ttot if ttot else None
        image_score = 3.0 * st['concept_ocr'] + 2.0 * st['triple_invalid'] + 1.0 * c_neither_rate * 10.0
        text_score = 3.0 * st['concept_transcript'] - 3.0 * st['concept_ocr'] - 3.0 * st['concept_neither']
        image_candidates.append((image_score, lec, sid, c_ocr_rate, c_trans_rate, c_neither_rate, t_valid_rate))
        text_candidates.append((text_score, lec, sid, c_ocr_rate, c_trans_rate, c_neither_rate, t_valid_rate))
    image_candidates.sort(reverse=True)
    text_candidates.sort(reverse=True)

    def pick_with_cap(cands, n):
        picked = []
        per_lec = defaultdict(int)
        for score, lec, sid, cocr, ctr, cne, tval in cands:
            if per_lec[lec] >= args.per_lecture_cap:
                continue
            picked.append((score, lec, sid, cocr, ctr, cne, tval))
            per_lec[lec] += 1
            if len(picked) >= n:
                break
        return picked
    picked_image = pick_with_cap(image_candidates, args.n_image)
    picked_text = pick_with_cap(text_candidates, args.n_text)
    rows = []
    for group_name, picked in [('image_reliant', picked_image), ('text_dominant', picked_text)]:
        for score, lec, sid, cocr, ctr, cne, tval in picked:
            pm = path_map[lec, sid]
            rows.append({'group': group_name, 'lecture': lec, 'slide_id': sid, 'score': round(score, 6), 'concept_ocr_rate': round(cocr, 6), 'concept_transcript_rate': round(ctr, 6), 'concept_neither_rate': round(cne, 6), 'triple_valid_rate': '' if tval is None else round(tval, 6), 'image_path': pm['image'], 'text_path': pm['text'], 'slide_json': pm['slide_json']})
    write_csv(out / 'audit_slides.csv', rows)
    print('[OK] Wrote:', out / 'audit_slides.csv')
    print(f'[INFO] image_reliant={len(picked_image)} text_dominant={len(picked_text)} per_lecture_cap={args.per_lecture_cap}')
if __name__ == '__main__':
    main()