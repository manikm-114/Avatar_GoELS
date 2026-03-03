import argparse
import csv
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
MODELS = ['Qwen__Qwen3-VL-4B-Instruct', 'llava-hf__llava-onevision-qwen2-7b-ov-hf', 'OpenGVLab__InternVL3-14B', 'Qwen__Qwen2-VL-7B-Instruct']

def short(name: str) -> str:
    if 'InternVL3-14B' in name:
        return 'InternVL3-14B'
    if 'qwen3' in name.lower():
        return 'Qwen3-VL-4B'
    if 'qwen2' in name.lower():
        return 'Qwen2-VL-7B'
    if 'llava' in name.lower():
        return 'LLaVA-OneVision'
    return name

def read_csv(path: Path):
    with path.open('r', encoding='utf-8', errors='replace') as f:
        return list(csv.DictReader(f))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase3_out', required=True)
    args = ap.parse_args()
    phase3_out = Path(args.phase3_out)
    tables = phase3_out / 'tables'
    figs = phase3_out / 'figures'
    figs.mkdir(parents=True, exist_ok=True)
    mean_rows = read_csv(tables / 'pairwise_stability_mean.csv')
    per_slide_rows = read_csv(tables / 'pairwise_stability_per_slide.csv')
    idx = {m: i for i, m in enumerate(MODELS)}
    n = len(MODELS)
    concept_mat = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    triple_mat = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for r in mean_rows:
        a, b = (r['model_a'], r['model_b'])
        t = r['type']
        v = float(r['mean_jaccard'])
        i, j = (idx[a], idx[b])
        if t == 'concept':
            concept_mat[i][j] = v
            concept_mat[j][i] = v
        elif t == 'triple':
            triple_mat[i][j] = v
            triple_mat[j][i] = v
    labels = [short(m) for m in MODELS]

    def heatmap(mat, title, outname):
        plt.figure()
        plt.imshow(mat)
        plt.xticks(range(n), labels, rotation=25, ha='right')
        plt.yticks(range(n), labels)
        plt.colorbar()
        plt.title(title)
        plt.tight_layout()
        plt.savefig(figs / outname, dpi=200)
    heatmap(concept_mat, 'Cross-model stability (Concept Jaccard, mean)', 'fig_heatmap_concept_jaccard.png')
    heatmap(triple_mat, 'Cross-model stability (Triple Jaccard, mean)', 'fig_heatmap_triple_jaccard.png')
    concept_vals = [float(r['concept_jaccard']) for r in per_slide_rows]
    triple_vals = [float(r['triple_jaccard']) for r in per_slide_rows]
    plt.figure()
    plt.hist(concept_vals, bins=40)
    plt.xlabel('Concept Jaccard (per slide, per model pair)')
    plt.ylabel('Count')
    plt.title('Distribution of concept stability across slides')
    plt.tight_layout()
    plt.savefig(figs / 'fig_hist_concept_jaccard.png', dpi=200)
    plt.figure()
    plt.hist(triple_vals, bins=40)
    plt.xlabel('Triple Jaccard (per slide, per model pair)')
    plt.ylabel('Count')
    plt.title('Distribution of triple stability across slides')
    plt.tight_layout()
    plt.savefig(figs / 'fig_hist_triple_jaccard.png', dpi=200)
    print('[OK] Wrote figures to:', figs)
if __name__ == '__main__':
    main()