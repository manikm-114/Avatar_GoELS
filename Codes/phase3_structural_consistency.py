import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple
MODELS = ['Qwen__Qwen3-VL-4B-Instruct', 'llava-hf__llava-onevision-qwen2-7b-ov-hf', 'OpenGVLab__InternVL3-14B', 'Qwen__Qwen2-VL-7B-Instruct']

def norm(s: str) -> str:
    return ' '.join((s or '').strip().lower().split())

def read_csv(path: Path) -> List[dict]:
    with path.open('r', encoding='utf-8', errors='replace') as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows: List[dict]):
    if not rows:
        return
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and (not b):
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    uni = len(a | b)
    return inter / uni if uni else 0.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase1_out', required=True, help='phase1_out with concepts_long.csv and triples_long.csv')
    ap.add_argument('--phase2_out', required=True, help='phase2_out with tables/concept_grounding.csv and tables/triple_entity_grounding.csv')
    ap.add_argument('--out', default='phase3_out', help='output folder')
    args = ap.parse_args()
    phase1_out = Path(args.phase1_out)
    phase2_out = Path(args.phase2_out)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = out_dir / 'tables'
    tables_dir.mkdir(parents=True, exist_ok=True)
    concepts = read_csv(phase1_out / 'concepts_long.csv')
    triples = read_csv(phase1_out / 'triples_long.csv')
    concept_ground = read_csv(phase2_out / 'tables' / 'concept_grounding.csv')
    triple_ent_ground = read_csv(phase2_out / 'tables' / 'triple_entity_grounding.csv')
    concept_sets: Dict[Tuple[str, str, str], Set[str]] = defaultdict(set)
    for r in concepts:
        lec, sid, m = (r['lecture'], r['slide_id'], r['model'])
        if m not in MODELS:
            continue
        term = norm(r['term'])
        if term:
            concept_sets[lec, sid, m].add(term)
    triple_sets: Dict[Tuple[str, str, str], Set[Tuple[str, str, str]]] = defaultdict(set)
    for r in triples:
        lec, sid, m = (r['lecture'], r['slide_id'], r['model'])
        if m not in MODELS:
            continue
        s = norm(r['s'])
        p = norm(r['p'])
        o = norm(r['o'])
        if s and p and o:
            triple_sets[lec, sid, m].add((s, p, o))
    slides = sorted({(r['lecture'], r['slide_id']) for r in concepts} | {(r['lecture'], r['slide_id']) for r in triples})
    pair_rows = []
    slide_rows = []
    CONS_T = 2
    concept_ground_map = {}
    for r in concept_ground:
        concept_ground_map[r['lecture'], r['slide_id'], r['model'], norm(r['term'])] = r['grounding']
    triple_valid_map = {}
    for r in triple_ent_ground:
        triple_valid_map[r['lecture'], r['slide_id'], r['model'], norm(r['s']), norm(r['p']), norm(r['o'])] = int(r['triple_valid'])
    pair_acc = defaultdict(list)
    for lec, sid in slides:
        c_by_m = {m: concept_sets.get((lec, sid, m), set()) for m in MODELS}
        t_by_m = {m: triple_sets.get((lec, sid, m), set()) for m in MODELS}
        for i in range(len(MODELS)):
            for j in range(i + 1, len(MODELS)):
                m1, m2 = (MODELS[i], MODELS[j])
                cj = jaccard(c_by_m[m1], c_by_m[m2])
                tj = jaccard(set(map(str, t_by_m[m1])), set(map(str, t_by_m[m2])))
                pair_rows.append({'lecture': lec, 'slide_id': sid, 'model_a': m1, 'model_b': m2, 'concept_jaccard': round(cj, 6), 'triple_jaccard': round(tj, 6)})
                pair_acc[m1, m2, 'concept'].append(cj)
                pair_acc[m1, m2, 'triple'].append(tj)
        concept_counts = defaultdict(int)
        for m in MODELS:
            for term in c_by_m[m]:
                concept_counts[term] += 1
        consensus_concepts = {term for term, c in concept_counts.items() if c >= CONS_T}
        triple_counts = defaultdict(int)
        for m in MODELS:
            for tri in t_by_m[m]:
                triple_counts[tri] += 1
        consensus_triples = {tri for tri, c in triple_counts.items() if c >= CONS_T}
        cons_c_total = len(consensus_concepts)
        cons_c_grounded = 0
        for term in consensus_concepts:
            supported = False
            for m in MODELS:
                if term in c_by_m[m]:
                    g = concept_ground_map.get((lec, sid, m, term), 'neither')
                    if g != 'neither':
                        supported = True
                        break
            cons_c_grounded += int(supported)
        cons_t_total = len(consensus_triples)
        cons_t_valid = 0
        for s, p, o in consensus_triples:
            supported = False
            for m in MODELS:
                if (s, p, o) in t_by_m[m]:
                    tv = triple_valid_map.get((lec, sid, m, s, p, o), 0)
                    if tv == 1:
                        supported = True
                        break
            cons_t_valid += int(supported)
        slide_rows.append({'lecture': lec, 'slide_id': sid, 'consensus_concepts_total': cons_c_total, 'consensus_concepts_grounded_rate': round(cons_c_grounded / cons_c_total, 6) if cons_c_total else '', 'consensus_triples_total': cons_t_total, 'consensus_triples_valid_rate': round(cons_t_valid / cons_t_total, 6) if cons_t_total else ''})
    pair_avg_rows = []
    for (m1, m2, typ), vals in pair_acc.items():
        pair_avg_rows.append({'model_a': m1, 'model_b': m2, 'type': typ, 'mean_jaccard': round(sum(vals) / len(vals), 6) if vals else '', 'n_slides': len(vals)})
    write_csv(tables_dir / 'pairwise_stability_per_slide.csv', pair_rows)
    write_csv(tables_dir / 'pairwise_stability_mean.csv', pair_avg_rows)
    write_csv(tables_dir / 'consensus_quality_per_slide.csv', slide_rows)
    print('[OK] Wrote:')
    print(' -', tables_dir / 'pairwise_stability_per_slide.csv')
    print(' -', tables_dir / 'pairwise_stability_mean.csv')
    print(' -', tables_dir / 'consensus_quality_per_slide.csv')
if __name__ == '__main__':
    main()