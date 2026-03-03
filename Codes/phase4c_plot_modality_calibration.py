import argparse
import csv
from pathlib import Path
import matplotlib.pyplot as plt

def read_rows(csv_path: Path):
    rows = []
    with csv_path.open('r', encoding='utf-8', errors='replace', newline='') as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows

def to_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in_csv', required=True, help='Path to *_claim_vs_ocr_evidence.csv')
    ap.add_argument('--out_png', default='phase4_out/figures/fig_modality_calibration.png', help='Output PNG path')
    ap.add_argument('--use_short_names', action='store_true', help='Use model_short for x-axis labels when available')
    args = ap.parse_args()
    in_csv = Path(args.in_csv)
    out_png = Path(args.out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    rows = read_rows(in_csv)
    if not rows:
        raise SystemExit(f'No rows found in {in_csv}')

    def sort_key(r):
        return (r.get('model_short') or '', r.get('model') or '')
    rows = sorted(rows, key=sort_key)
    labels = []
    img_claim = []
    ocr_evid = []
    hall_img = []
    for r in rows:
        label = r.get('model_short') if args.use_short_names else r.get('model')
        label = label or r.get('model') or 'UNKNOWN'
        labels.append(label)
        img_claim.append(to_float(r.get('img_claim_rate')))
        ocr_evid.append(to_float(r.get('ocr_evidenced_rate')))
        hall_img.append(to_float(r.get('hallucinated_img_claim_rate')))
    x = list(range(len(labels)))
    width = 0.26
    plt.figure()
    plt.bar([i - width for i in x], img_claim, width=width, label='ImgClaim')
    plt.bar(x, ocr_evid, width=width, label='OCR-Evid')
    plt.bar([i + width for i in x], hall_img, width=width, label='HallImg')
    plt.xticks(x, labels, rotation=25, ha='right')
    plt.ylim(0.0, 1.0)
    plt.ylabel('Rate')
    plt.title('Modality tag calibration vs evidence')
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    print('[OK] Wrote:', out_png)
if __name__ == '__main__':
    main()