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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase1_out', required=True)
    ap.add_argument('--phase2_out', required=True)
    ap.add_argument('--out', default='phase3_out')
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
    concept_sets = defaultdict(set)
    triple_sets = defaultdict(set)
    slides = set()
    for r in concepts:
        lec, sid, m = (r['lecture'], r['slide_id'], r['model'])
        if m not in MODELS:
            continue
        term = norm(r['term'])
        if term:
            concept_sets[lec, sid, m].add(term)
            slides.add((lec, sid))
    for r in triples:
        lec, sid, m = (r['lecture'], r['slide_id'], r['model'])
        if m not in MODELS:
            continue
        s, p, o = (norm(r['s']), norm(r['p']), norm(r['o']))
        if s and p and o:
            triple_sets[lec, sid, m].add((s, p, o))
            slides.add((lec, sid))
    concept_ground_map = {}
    for r in concept_ground:
        concept_ground_map[r['lecture'], r['slide_id'], r['model'], norm(r['term'])] = r['grounding']
    triple_valid_map = {}
    for r in triple_ent_ground:
        triple_valid_map[r['lecture'], r['slide_id'], r['model'], norm(r['s']), norm(r['p']), norm(r['o'])] = int(r['triple_valid'])
    thresholds = [1, 2, 3]
    sweep_rows = []
    for T in thresholds:
        total_cons_c = 0
        total_cons_t = 0
        grounded_cons_c = 0
        valid_cons_t = 0
        slides_with_any_c = 0
        slides_with_any_t = 0
        for lec, sid in slides:
            c_by_m = {m: concept_sets.get((lec, sid, m), set()) for m in MODELS}
            t_by_m = {m: triple_sets.get((lec, sid, m), set()) for m in MODELS}
            c_counts = defaultdict(int)
            for m in MODELS:
                for term in c_by_m[m]:
                    c_counts[term] += 1
            cons_c = {term for term, cnt in c_counts.items() if cnt >= T}
            t_counts = defaultdict(int)
            for m in MODELS:
                for tri in t_by_m[m]:
                    t_counts[tri] += 1
            cons_t = {tri for tri, cnt in t_counts.items() if cnt >= T}
            if cons_c:
                slides_with_any_c += 1
            if cons_t:
                slides_with_any_t += 1
            for term in cons_c:
                total_cons_c += 1
                supported = False
                for m in MODELS:
                    if term in c_by_m[m]:
                        g = concept_ground_map.get((lec, sid, m, term), 'neither')
                        if g != 'neither':
                            supported = True
                            break
                grounded_cons_c += int(supported)
            for s, p, o in cons_t:
                total_cons_t += 1
                supported = False
                for m in MODELS:
                    if (s, p, o) in t_by_m[m]:
                        tv = triple_valid_map.get((lec, sid, m, s, p, o), 0)
                        if tv == 1:
                            supported = True
                            break
                valid_cons_t += int(supported)
        nslides = len(slides)
        sweep_rows.append({'threshold_T': T, 'slides': nslides, 'slides_with_consensus_concepts': slides_with_any_c, 'slides_with_consensus_concepts_rate': round(slides_with_any_c / nslides, 6) if nslides else 0.0, 'consensus_concepts_total': total_cons_c, 'consensus_concepts_grounded_rate': round(grounded_cons_c / total_cons_c, 6) if total_cons_c else '', 'slides_with_consensus_triples': slides_with_any_t, 'slides_with_consensus_triples_rate': round(slides_with_any_t / nslides, 6) if nslides else 0.0, 'consensus_triples_total': total_cons_t, 'consensus_triples_valid_rate': round(valid_cons_t / total_cons_t, 6) if total_cons_t else ''})
    write_csv(tables_dir / 'consensus_threshold_sweep.csv', sweep_rows)
    print('[OK] Wrote:', tables_dir / 'consensus_threshold_sweep.csv')
if __name__ == '__main__':
    main()