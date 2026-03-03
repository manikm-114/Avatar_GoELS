import argparse, csv, json
from pathlib import Path
from collections import Counter, defaultdict
YES = {'yes', 'y', 'true', '1'}
NO = {'no', 'n', 'false', '0'}

def norm(x):
    return (x or '').strip().lower()

def as_bool(x):
    x = norm(x)
    if x in YES:
        return True
    if x in NO:
        return False
    return None

def read_csv(path: Path):
    with path.open('r', encoding='utf-8', errors='replace') as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def rate(num, den):
    return num / den if den else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--responses', required=True, help='audit_responses.csv')
    ap.add_argument('--out', required=True, help='output folder, e.g., .\\phase5_out')
    args = ap.parse_args()
    resp_path = Path(args.responses)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_csv(resp_path)
    parsed = []
    for r in rows:
        group = r.get('group', '').strip()
        lec = r.get('lecture', '').strip()
        sid = r.get('slide_id', '').strip()
        c = as_bool(r.get('concepts_correct', ''))
        t = as_bool(r.get('triples_correct', ''))
        im = as_bool(r.get('image_dominant', ''))
        notes = (r.get('notes', '') or '').strip()
        parsed.append({'group': group, 'lecture': lec, 'slide_id': sid, 'concepts_correct': c, 'triples_correct': t, 'image_dominant': im, 'notes': notes})

    def summarize(subset):
        N = len(subset)
        c_ans = [x['concepts_correct'] for x in subset if x['concepts_correct'] is not None]
        t_ans = [x['triples_correct'] for x in subset if x['triples_correct'] is not None]
        i_ans = [x['image_dominant'] for x in subset if x['image_dominant'] is not None]
        out = {'n_slides': N, 'concepts_labeled': len(c_ans), 'concepts_yes': sum(c_ans), 'concepts_yes_rate': rate(sum(c_ans), len(c_ans)), 'triples_labeled': len(t_ans), 'triples_yes': sum(t_ans), 'triples_yes_rate': rate(sum(t_ans), len(t_ans)), 'image_dom_labeled': len(i_ans), 'image_dom_yes': sum(i_ans), 'image_dom_yes_rate': rate(sum(i_ans), len(i_ans))}
        return out
    overall = summarize(parsed)
    by_group = {}
    for g in sorted(set((x['group'] for x in parsed))):
        by_group[g] = summarize([x for x in parsed if x['group'] == g])
    conf = []
    for g, stats in by_group.items():
        conf.append({'group': g, 'n': stats['n_slides'], 'image_dom_labeled': stats['image_dom_labeled'], 'image_dom_yes': stats['image_dom_yes'], 'image_dom_yes_rate': stats['image_dom_yes_rate']})

    def keyfail(x):
        c = x['concepts_correct']
        t = x['triples_correct']
        score = 0
        if c is False:
            score -= 2
        if t is False:
            score -= 2
        if x['notes']:
            score -= 1
        return score
    failures = sorted([x for x in parsed if x['concepts_correct'] is False or x['triples_correct'] is False], key=keyfail)
    top_failures = failures[:15]
    out_summary = {'overall': overall, 'by_group': by_group, 'group_vs_image_dominant': conf, 'n_failures': len(failures), 'top_failures': top_failures, 'notes_nonempty': sum((1 for x in parsed if x['notes']))}
    (out_dir / 'phase5_audit_summary.json').write_text(json.dumps(out_summary, indent=2), encoding='utf-8')
    table_rows = []
    for name, stats in [('overall', overall)] + [(f'group:{g}', by_group[g]) for g in by_group]:
        table_rows.append({'split': name, 'n_slides': stats['n_slides'], 'concepts_yes_rate': stats['concepts_yes_rate'], 'triples_yes_rate': stats['triples_yes_rate'], 'image_dom_yes_rate': stats['image_dom_yes_rate'], 'concepts_labeled': stats['concepts_labeled'], 'triples_labeled': stats['triples_labeled'], 'image_dom_labeled': stats['image_dom_labeled']})
    write_csv(out_dir / 'phase5_audit_table.csv', table_rows, ['split', 'n_slides', 'concepts_yes_rate', 'triples_yes_rate', 'image_dom_yes_rate', 'concepts_labeled', 'triples_labeled', 'image_dom_labeled'])
    write_csv(out_dir / 'phase5_audit_failures.csv', failures, ['group', 'lecture', 'slide_id', 'concepts_correct', 'triples_correct', 'image_dominant', 'notes'])
    print('[OK] Wrote:')
    print(' -', out_dir / 'phase5_audit_summary.json')
    print(' -', out_dir / 'phase5_audit_table.csv')
    print(' -', out_dir / 'phase5_audit_failures.csv')
if __name__ == '__main__':
    main()