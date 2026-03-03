import argparse
import csv
from pathlib import Path

def read_csv(path: Path):
    with path.open('r', encoding='utf-8', errors='replace') as f:
        return list(csv.DictReader(f))

def short_model(name: str) -> str:
    n = name.lower()
    if 'internvl3-14b' in n:
        return 'InternVL3-14B'
    if 'llava' in n:
        return 'LLaVA-OneVision'
    if 'qwen3' in n:
        return 'Qwen3-VL-4B'
    if 'qwen2' in n:
        return 'Qwen2-VL-7B'
    return name

def latex_escape(s: str) -> str:
    return s.replace('\\', '\\textbackslash{}').replace('&', '\\&').replace('%', '\\%').replace('_', '\\_').replace('#', '\\#').replace('{', '\\{').replace('}', '\\}').replace('^', '\\^{}').replace('~', '\\~{}')

def write_text(path: Path, text: str):
    path.write_text(text, encoding='utf-8')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase2_out', required=True)
    ap.add_argument('--phase3_out', required=True)
    ap.add_argument('--out', default='paper_assets')
    args = ap.parse_args()
    phase2_out = Path(args.phase2_out)
    phase3_out = Path(args.phase3_out)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    model_rates = read_csv(phase2_out / 'tables' / 'model_grounding_rates.csv')
    pairwise_mean = read_csv(phase3_out / 'tables' / 'pairwise_stability_mean.csv')
    sweep = read_csv(phase3_out / 'tables' / 'consensus_threshold_sweep.csv')
    t1_csv = out_dir / 'table1_grounding_by_model.csv'
    with t1_csv.open('w', newline='', encoding='utf-8') as f:
        fieldnames = ['model', 'concept_total', 'concept_transcript_rate', 'concept_ocr_rate', 'concept_neither_rate', 'triple_total', 'triple_valid_rate']
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in model_rates:
            w.writerow({'model': short_model(r['model']), 'concept_total': r['concept_total'], 'concept_transcript_rate': r['concept_transcript_rate'], 'concept_ocr_rate': r['concept_ocr_rate'], 'concept_neither_rate': r['concept_neither_rate'], 'triple_total': r['triple_total'], 'triple_valid_rate': r['triple_valid_rate']})
    lines = []
    lines.append('\\begin{table}[t]\n\\centering\n\\small')
    lines.append('\\begin{tabular}{lrrrrrr}')
    lines.append('\\toprule')
    lines.append('Model & $N_c$ & Tr. & OCR & Neither & $N_t$ & Triple-valid \\\\')
    lines.append('\\midrule')
    for r in model_rates:
        lines.append(f'{latex_escape(short_model(r['model']))} & {r['concept_total']} & {float(r['concept_transcript_rate']):.3f} & {float(r['concept_ocr_rate']):.3f} & {float(r['concept_neither_rate']):.3f} & {r['triple_total']} & {float(r['triple_valid_rate']):.3f} \\\\')
    lines.append('\\bottomrule')
    lines.append('\\end{tabular}')
    lines.append('\\caption{Grounding reliability by model. Tr.=Transcript-grounded concept rate; OCR=OCR-grounded concept rate; Neither=ungrounded concept rate. Triple-valid is the fraction of extracted triples whose subject and object are grounded (transcript or OCR).}')
    lines.append('\\label{tab:grounding}')
    lines.append('\\end{table}\n')
    write_text(out_dir / 'table1_grounding_by_model.tex', '\n'.join(lines))
    concept_pairs = [r for r in pairwise_mean if r['type'] == 'concept']
    triple_pairs = [r for r in pairwise_mean if r['type'] == 'triple']
    t2_csv = out_dir / 'table2_pairwise_stability.csv'
    with t2_csv.open('w', newline='', encoding='utf-8') as f:
        fieldnames = ['model_a', 'model_b', 'concept_mean_jaccard', 'triple_mean_jaccard', 'n_slides']
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        c_map = {(r['model_a'], r['model_b']): r for r in concept_pairs}
        t_map = {(r['model_a'], r['model_b']): r for r in triple_pairs}
        keys = sorted(set(c_map.keys()) | set(t_map.keys()))
        for a, b in keys:
            c = c_map.get((a, b))
            t = t_map.get((a, b))
            w.writerow({'model_a': short_model(a), 'model_b': short_model(b), 'concept_mean_jaccard': c['mean_jaccard'] if c else '', 'triple_mean_jaccard': t['mean_jaccard'] if t else '', 'n_slides': c['n_slides'] if c else t['n_slides'] if t else ''})
    sweep_lines = []
    sweep_lines.append('\\begin{table}[t]\n\\centering\n\\small')
    sweep_lines.append('\\begin{tabular}{rrrrrr}')
    sweep_lines.append('\\toprule')
    sweep_lines.append('$T$ & SlideCov$_c$ & Ground$_c$ & SlideCov$_t$ & Valid$_t$ & TotTriples \\\\')
    sweep_lines.append('\\midrule')
    for r in sweep:
        T = r['threshold_T']
        sc = float(r['slides_with_consensus_concepts_rate'])
        gc = r['consensus_concepts_grounded_rate']
        st = float(r['slides_with_consensus_triples_rate'])
        vt = r['consensus_triples_valid_rate']
        tot = r['consensus_triples_total']
        sweep_lines.append(f'{T} & {sc:.3f} & {(gc if gc != '' else '')} & {st:.3f} & {(vt if vt != '' else '')} & {tot} \\\\')
    sweep_lines.append('\\bottomrule')
    sweep_lines.append('\\end{tabular}')
    sweep_lines.append('\\caption{Consensus threshold sweep ($T$ models must agree). SlideCov$_c$ / SlideCov$_t$ are the fraction of slides with at least one consensus concept/triple. Ground$_c$ is grounded rate of consensus concepts; Valid$_t$ is validity rate of consensus triples.}')
    sweep_lines.append('\\label{tab:sweep}')
    sweep_lines.append('\\end{table}\n')
    write_text(out_dir / 'table3_consensus_sweep.tex', '\n'.join(sweep_lines))
    print('[OK] Wrote paper assets to:', out_dir)
    print(' - table1_grounding_by_model.csv/.tex')
    print(' - table2_pairwise_stability.csv')
    print(' - table3_consensus_sweep.tex')
if __name__ == '__main__':
    main()