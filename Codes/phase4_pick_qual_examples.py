import argparse, csv
from pathlib import Path

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase1_out', required=True)
    ap.add_argument('--phase2_out', required=True)
    ap.add_argument('--phase3_out', required=True)
    ap.add_argument('--out', default='phase4_out')
    ap.add_argument('--topk', type=int, default=50)
    args = ap.parse_args()
    phase1 = Path(args.phase1_out)
    phase2 = Path(args.phase2_out)
    phase3 = Path(args.phase3_out)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cg = read_csv(phase2 / 'tables' / 'concept_grounding.csv')
    tg = read_csv(phase2 / 'tables' / 'triple_entity_grounding.csv')
    ps = read_csv(phase3 / 'tables' / 'pairwise_stability_per_slide.csv')
    slide_ungrounded_concepts = {}
    slide_invalid_triples = {}
    slide_concept_jaccards = {}
    for r in cg:
        key = (r['lecture'], r['slide_id'])
        if key not in slide_ungrounded_concepts:
            slide_ungrounded_concepts[key] = 0
        if r['grounding'] == 'neither':
            slide_ungrounded_concepts[key] += 1
    for r in tg:
        key = (r['lecture'], r['slide_id'])
        if key not in slide_invalid_triples:
            slide_invalid_triples[key] = 0
        if str(r['triple_valid']).strip() == '0':
            slide_invalid_triples[key] += 1
    for r in ps:
        key = (r['lecture'], r['slide_id'])
        slide_concept_jaccards.setdefault(key, []).append(float(r['concept_jaccard']))
    rows = []
    for key in set(list(slide_ungrounded_concepts.keys()) + list(slide_invalid_triples.keys()) + list(slide_concept_jaccards.keys())):
        lec, sid = key
        uc = slide_ungrounded_concepts.get(key, 0)
        it = slide_invalid_triples.get(key, 0)
        cj_list = slide_concept_jaccards.get(key, [])
        cj_mean = sum(cj_list) / len(cj_list) if cj_list else None
        score = 2.0 * uc + 2.0 * it + 5.0 * (1.0 - (cj_mean if cj_mean is not None else 0.0))
        rows.append({'lecture': lec, 'slide_id': sid, 'ungrounded_concepts': uc, 'invalid_triples': it, 'mean_concept_jaccard': '' if cj_mean is None else round(cj_mean, 6), 'score': round(score, 6)})
    rows.sort(key=lambda r: r['score'], reverse=True)
    write_csv(out / 'qual_examples_ranked.csv', rows[:args.topk])
    print('[OK] Wrote:', out / 'qual_examples_ranked.csv')
if __name__ == '__main__':
    main()