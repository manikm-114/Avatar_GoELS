import argparse
import csv
from collections import defaultdict
from pathlib import Path

def read_rows(p: Path):
    with p.open('r', encoding='utf-8', errors='replace', newline='') as f:
        return list(csv.DictReader(f))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--triple_csv', required=True, help='phase2_out/tables/triple_entity_grounding.csv')
    ap.add_argument('--out_csv', default='phase4_out/slides_ranked_ocr_evidenced_full.csv')
    ap.add_argument('--min_triples', type=int, default=1, help='Only include slides with >= this many triples')
    args = ap.parse_args()
    triple_csv = Path(args.triple_csv)
    out_csv = Path(args.out_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    rows = read_rows(triple_csv)
    totals = defaultdict(int)
    ocr_evid = defaultdict(int)
    for r in rows:
        lecture = r['lecture']
        slide_id = r['slide_id']
        totals[lecture, slide_id] += 1
        s_g = (r.get('s_grounding') or '').strip().lower()
        o_g = (r.get('o_grounding') or '').strip().lower()
        is_ocr_evid = s_g == 'ocr' and o_g != 'transcript' or (o_g == 'ocr' and s_g != 'transcript')
        if is_ocr_evid:
            ocr_evid[lecture, slide_id] += 1
    out_rows = []
    for (lecture, slide_id), t in totals.items():
        if t < args.min_triples:
            continue
        oe = ocr_evid.get((lecture, slide_id), 0)
        rate = oe / t if t else 0.0
        out_rows.append({'lecture': lecture, 'slide_id': slide_id, 'triples_total': t, 'ocr_evidenced_triples_total': oe, 'ocr_evidenced_rate': f'{rate:.6f}'})
    out_rows.sort(key=lambda x: (float(x['ocr_evidenced_rate']), int(x['triples_total'])), reverse=True)
    with out_csv.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print('[OK] wrote:', out_csv)
    print('rows:', len(out_rows))
if __name__ == '__main__':
    main()