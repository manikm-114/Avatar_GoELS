import argparse
import csv
from collections import defaultdict
from pathlib import Path
MODELS = ['Qwen__Qwen3-VL-4B-Instruct', 'llava-hf__llava-onevision-qwen2-7b-ov-hf', 'OpenGVLab__InternVL3-14B', 'Qwen__Qwen2-VL-7B-Instruct']

def read_csv(path: Path):
    with path.open('r', encoding='utf-8', errors='replace') as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows):
    if not rows:
        return
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase2_out', required=True, help='phase2_out folder')
    args = ap.parse_args()
    phase2_out = Path(args.phase2_out)
    tables = phase2_out / 'tables'
    out_tables = phase2_out / 'tables'
    concept_path = tables / 'concept_grounding.csv'
    triple_path = tables / 'triple_entity_grounding.csv'
    concepts = read_csv(concept_path)
    triples = read_csv(triple_path)
    concept_model = {m: defaultdict(int) for m in MODELS}
    triple_model = {m: defaultdict(int) for m in MODELS}
    for r in concepts:
        m = r['model']
        if m not in concept_model:
            continue
        g = r['grounding']
        concept_model[m]['total'] += 1
        concept_model[m][g] += 1
    for r in triples:
        m = r['model']
        if m not in triple_model:
            continue
        triple_model[m]['total'] += 1
        triple_model[m]['valid'] += int(r['triple_valid'])
        triple_model[m]['invalid'] += 1 - int(r['triple_valid'])
        triple_model[m][f's_{r['s_grounding']}'] += 1
        triple_model[m][f'o_{r['o_grounding']}'] += 1
    model_summary = []
    for m in MODELS:
        ct = concept_model[m]['total']
        tt = triple_model[m]['total']
        model_summary.append({'model': m, 'concept_total': ct, 'concept_transcript': concept_model[m]['transcript'], 'concept_ocr': concept_model[m]['ocr'], 'concept_neither': concept_model[m]['neither'], 'concept_transcript_rate': round(concept_model[m]['transcript'] / ct, 6) if ct else 0.0, 'concept_ocr_rate': round(concept_model[m]['ocr'] / ct, 6) if ct else 0.0, 'concept_neither_rate': round(concept_model[m]['neither'] / ct, 6) if ct else 0.0, 'triple_total': tt, 'triple_valid': triple_model[m]['valid'], 'triple_valid_rate': round(triple_model[m]['valid'] / tt, 6) if tt else 0.0, 'triple_invalid': triple_model[m]['invalid']})
    write_csv(out_tables / 'model_grounding_rates.csv', model_summary)
    concept_lecture = defaultdict(lambda: defaultdict(int))
    triple_lecture = defaultdict(lambda: defaultdict(int))
    for r in concepts:
        key = (r['lecture'], r['model'])
        g = r['grounding']
        concept_lecture[key]['total'] += 1
        concept_lecture[key][g] += 1
    for r in triples:
        key = (r['lecture'], r['model'])
        triple_lecture[key]['total'] += 1
        triple_lecture[key]['valid'] += int(r['triple_valid'])
        triple_lecture[key]['invalid'] += 1 - int(r['triple_valid'])
    lecture_rows = []
    for (lec, m), c in concept_lecture.items():
        if m not in MODELS:
            continue
        ct = c['total']
        t = triple_lecture.get((lec, m), defaultdict(int))
        tt = t['total']
        lecture_rows.append({'lecture': lec, 'model': m, 'concept_total': ct, 'concept_neither_rate': round(c['neither'] / ct, 6) if ct else 0.0, 'concept_ocr_rate': round(c['ocr'] / ct, 6) if ct else 0.0, 'concept_transcript_rate': round(c['transcript'] / ct, 6) if ct else 0.0, 'triple_total': tt, 'triple_valid_rate': round(t['valid'] / tt, 6) if tt else ''})
    for (lec, m), t in triple_lecture.items():
        if m not in MODELS:
            continue
        if any((r['lecture'] == lec and r['model'] == m for r in lecture_rows)):
            continue
        tt = t['total']
        lecture_rows.append({'lecture': lec, 'model': m, 'concept_total': 0, 'concept_neither_rate': '', 'concept_ocr_rate': '', 'concept_transcript_rate': '', 'triple_total': tt, 'triple_valid_rate': round(t['valid'] / tt, 6) if tt else ''})
    lecture_rows.sort(key=lambda x: (x['lecture'], x['model']))
    write_csv(out_tables / 'lecture_grounding_rates.csv', lecture_rows)
    print('[OK] Wrote:')
    print(' -', out_tables / 'model_grounding_rates.csv')
    print(' -', out_tables / 'lecture_grounding_rates.csv')
if __name__ == '__main__':
    main()