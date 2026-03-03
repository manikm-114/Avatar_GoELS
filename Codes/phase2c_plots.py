import argparse
import csv
from pathlib import Path
import matplotlib.pyplot as plt

def read_csv(path: Path):
    with path.open('r', encoding='utf-8', errors='replace') as f:
        return list(csv.DictReader(f))

def short_model(name: str) -> str:
    if 'InternVL3-14B' in name:
        return 'InternVL3-14B'
    if 'qwen3' in name.lower():
        return 'Qwen3-VL-4B'
    if 'qwen2' in name.lower():
        return 'Qwen2-VL-7B'
    if 'llava' in name.lower():
        return 'LLaVA-OneVision'
    return name

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase2_out', required=True)
    args = ap.parse_args()
    phase2_out = Path(args.phase2_out)
    tables = phase2_out / 'tables'
    figs = phase2_out / 'figures'
    figs.mkdir(parents=True, exist_ok=True)
    model_rates = read_csv(tables / 'model_grounding_rates.csv')
    labels = [short_model(r['model']) for r in model_rates]
    concept_neither = [float(r['concept_neither_rate']) for r in model_rates]
    concept_ocr = [float(r['concept_ocr_rate']) for r in model_rates]
    concept_trans = [float(r['concept_transcript_rate']) for r in model_rates]
    triple_valid_rate = [float(r['triple_valid_rate']) for r in model_rates]
    plt.figure()
    x = list(range(len(labels)))
    plt.bar(x, concept_trans, label='Transcript-grounded')
    plt.bar(x, concept_ocr, bottom=concept_trans, label='OCR-grounded')
    bottom2 = [concept_trans[i] + concept_ocr[i] for i in range(len(labels))]
    plt.bar(x, concept_neither, bottom=bottom2, label='Neither (ungrounded)')
    plt.xticks(x, labels, rotation=20, ha='right')
    plt.ylim(0, 1.0)
    plt.ylabel('Fraction of extracted concepts')
    plt.title('Concept grounding breakdown by model')
    plt.legend()
    plt.tight_layout()
    plt.savefig(figs / 'fig_concept_grounding_breakdown.png', dpi=200)
    plt.figure()
    plt.bar(x, triple_valid_rate)
    plt.xticks(x, labels, rotation=20, ha='right')
    plt.ylim(0, 1.0)
    plt.ylabel('Fraction of triples with grounded (s,o)')
    plt.title('Grounded triple validity rate by model')
    plt.tight_layout()
    plt.savefig(figs / 'fig_triple_valid_rate.png', dpi=200)
    hp_proxy = [concept_neither[i] * 0.5 + (1.0 - triple_valid_rate[i]) * 0.5 for i in range(len(labels))]
    plt.figure()
    plt.bar(x, hp_proxy)
    plt.xticks(x, labels, rotation=20, ha='right')
    plt.ylim(0, 1.0)
    plt.ylabel('Score (higher = less reliable)')
    plt.title('Reliability proxy (ungrounded concepts + invalid triples)')
    plt.tight_layout()
    plt.savefig(figs / 'fig_reliability_proxy.png', dpi=200)
    print('[OK] Wrote figures to:', figs)
if __name__ == '__main__':
    main()