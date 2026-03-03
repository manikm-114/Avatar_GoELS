import argparse, csv, shutil
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

def safe_name(s: str) -> str:
    return ''.join((ch if ch.isalnum() or ch in '._-+' else '_' for ch in s))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--phase5_out', required=True, help='Folder containing audit_slides.csv')
    ap.add_argument('--csv', default='audit_slides.csv')
    ap.add_argument('--img_dir', default='audit_images')
    args = ap.parse_args()
    out_dir = Path(args.phase5_out)
    in_csv = out_dir / args.csv
    img_dir = out_dir / args.img_dir
    img_dir.mkdir(parents=True, exist_ok=True)
    rows = read_csv(in_csv)
    updated = []
    copied, missing = (0, 0)
    for r in rows:
        src = Path(r['image_path'])
        lec = r.get('lecture', '')
        sid = r.get('slide_id', '')
        ext = src.suffix if src.suffix else '.jpg'
        dst_name = f'{safe_name(lec)}__{safe_name(sid)}{ext}'
        dst = img_dir / dst_name
        if src.exists():
            if not dst.exists():
                shutil.copy2(src, dst)
            copied += 1
            r['image_path'] = f'{args.img_dir}/{dst_name}'
        else:
            missing += 1
            r['image_path'] = ''
        updated.append(r)
    out_csv = out_dir / 'audit_slides_local.csv'
    write_csv(out_csv, updated)
    print('[OK] Copied images:', copied, 'missing:', missing)
    print('[OK] Wrote:', out_csv)
    print('[INFO] Images stored in:', img_dir)
if __name__ == '__main__':
    main()