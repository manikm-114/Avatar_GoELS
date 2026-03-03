import argparse
import csv
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ----------------------------
# Robust JSON loading (handles NaN/null-ish)
# ----------------------------
_NAN_RE = re.compile(r'(?<!")\bNaN\b(?!")')
_INF_RE = re.compile(r'(?<!")\bInfinity\b(?!")')
_NINF_RE = re.compile(r'(?<!")\b-Infinity\b(?!")')

def load_json_relaxed(path: Path) -> Dict[str, Any]:
    """
    Loads JSON but tries to be tolerant to NaN/Infinity tokens that occasionally appear
    in model outputs / merged files.
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Replace bare NaN/Infinity with null
        cleaned = _NINF_RE.sub("null", raw)
        cleaned = _INF_RE.sub("null", cleaned)
        cleaned = _NAN_RE.sub("null", cleaned)
        return json.loads(cleaned)

# ----------------------------
# Helpers
# ----------------------------
def safe_lower(s: Any) -> str:
    return str(s).lower() if s is not None else ""

def is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""

def load_slide_text(slide_json: Dict[str, Any]) -> str:
    """
    Loads the slide text from paths.text if it exists.
    If missing/unreadable, returns empty string.
    """
    paths = slide_json.get("paths") or {}
    text_path = paths.get("text")
    if not text_path or not isinstance(text_path, str):
        return ""
    p = Path(text_path)
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

def normalize_concepts(concepts_parsed: Any) -> List[Dict[str, Any]]:
    """
    Normalizes concepts into list of {term, category}.
    Handles:
      - {"concepts":[...]}  OR
      - {"term": "...", "category": "..."} OR
      - [] / None
    """
    if concepts_parsed is None:
        return []
    if isinstance(concepts_parsed, list):
        # sometimes concepts may be directly a list (rare)
        out = []
        for item in concepts_parsed:
            if isinstance(item, dict) and is_nonempty_str(item.get("term")):
                out.append({"term": item.get("term"), "category": item.get("category")})
        return out

    if isinstance(concepts_parsed, dict):
        if isinstance(concepts_parsed.get("concepts"), list):
            out = []
            for item in concepts_parsed["concepts"]:
                if isinstance(item, dict) and is_nonempty_str(item.get("term")):
                    out.append({"term": item.get("term"), "category": item.get("category")})
            return out
        # single concept shape
        if is_nonempty_str(concepts_parsed.get("term")):
            return [{"term": concepts_parsed.get("term"), "category": concepts_parsed.get("category")}]

    return []

def normalize_triples(triples_parsed: Any) -> List[Dict[str, Any]]:
    """
    Normalizes triples into list of dicts containing s,p,o,modalities,confidence,evidence.
    Handles:
      - {"triples":[...]} OR
      - {"s":..., "p":..., "o":...} OR
      - [] / None
    """
    if triples_parsed is None:
        return []
    if isinstance(triples_parsed, list):
        # sometimes triples may be directly a list (rare)
        out = []
        for t in triples_parsed:
            if isinstance(t, dict) and is_nonempty_str(t.get("s")) and is_nonempty_str(t.get("o")):
                out.append(t)
        return out

    if isinstance(triples_parsed, dict):
        if isinstance(triples_parsed.get("triples"), list):
            out = []
            for t in triples_parsed["triples"]:
                if isinstance(t, dict) and is_nonempty_str(t.get("s")) and is_nonempty_str(t.get("o")):
                    out.append(t)
            return out
        # single triple shape
        if is_nonempty_str(triples_parsed.get("s")) and is_nonempty_str(triples_parsed.get("o")):
            return [triples_parsed]

    return []

def contains_verbatim(haystack: str, needle: str) -> bool:
    """
    Case-insensitive substring check.
    """
    if not haystack or not needle:
        return False
    return needle.lower() in haystack.lower()

def modalities_has_image(m: Any) -> bool:
    if not isinstance(m, list):
        return False
    return any(isinstance(x, str) and x.lower() == "image" for x in m)

def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, (int, float)):
            if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
                return default
            return float(x)
        return float(str(x))
    except Exception:
        return default

# ----------------------------
# Data structures
# ----------------------------
@dataclass
class SlideKey:
    lecture: str
    slide_id: str
    path: str

# ----------------------------
# Main analysis
# ----------------------------
def find_slide_jsons(root: Path) -> List[Path]:
    # Matches Lecture*/Slide*.json (case-insensitive "Lecture")
    candidates = []
    for p in root.rglob("*.json"):
        if p.name.lower().startswith("slide") and p.parent.name.lower().startswith("lecture"):
            candidates.append(p)
    return sorted(candidates)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Root folder that contains Lecture*/Slide*.json")
    ap.add_argument("--out", default="analysis_out", help="Output directory")
    ap.add_argument("--topk", type=int, default=50, help="How many top image-heavy slides to list")
    args = ap.parse_args()

    root = Path(args.root)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    slide_files = find_slide_jsons(root)
    if not slide_files:
        raise SystemExit(f"No Lecture*/Slide*.json files found under: {root}")

    # Aggregates
    model_stats: Dict[str, Dict[str, float]] = {}
    ranked_rows: List[Dict[str, Any]] = []
    violation_samples: List[Dict[str, Any]] = []

    def ms(model: str) -> Dict[str, float]:
        model_stats.setdefault(model, {
            "slides_seen": 0,
            "slides_with_text": 0,
            "slides_with_concepts": 0,
            "slides_with_triples": 0,
            "concept_terms_total": 0,
            "concept_terms_not_in_text": 0,
            "triples_total": 0,
            "triples_s_not_in_text": 0,
            "triples_o_not_in_text": 0,
            "triples_with_image_modality": 0,
        })
        return model_stats[model]

    for sf in slide_files:
        sj = load_json_relaxed(sf)
        lecture = sj.get("lecture") or sf.parent.name
        slide_id = sj.get("slide_id") or sf.stem
        slide_text = load_slide_text(sj)
        has_text = bool(slide_text.strip())

        models = sj.get("models") or {}
        # score components for this slide
        slide_image_modality_hits = 0
        slide_concept_not_in_text = 0
        slide_concept_total = 0
        slide_triples_total = 0
        slide_triple_not_in_text = 0  # s or o missing
        slide_models_count = 0

        for model_name, payload in models.items():
            if not isinstance(payload, dict):
                continue
            slide_models_count += 1
            st = ms(model_name)
            st["slides_seen"] += 1
            if has_text:
                st["slides_with_text"] += 1

            concepts_block = payload.get("concepts")
            triples_block = payload.get("triples")

            # Concepts
            concepts_parsed = None
            if isinstance(concepts_block, dict):
                concepts_parsed = concepts_block.get("parsed")
            concepts = normalize_concepts(concepts_parsed)
            if concepts:
                st["slides_with_concepts"] += 1
            for c in concepts:
                term = c.get("term")
                if not is_nonempty_str(term):
                    continue
                slide_concept_total += 1
                st["concept_terms_total"] += 1
                if has_text and not contains_verbatim(slide_text, term):
                    slide_concept_not_in_text += 1
                    st["concept_terms_not_in_text"] += 1
                    if len(violation_samples) < 500:
                        violation_samples.append({
                            "lecture": lecture,
                            "slide_id": slide_id,
                            "model": model_name,
                            "type": "concept_term_not_in_text",
                            "term_or_entity": term
                        })

            # Triples
            triples_parsed = None
            if isinstance(triples_block, dict):
                triples_parsed = triples_block.get("parsed")
            triples = normalize_triples(triples_parsed)
            if triples:
                st["slides_with_triples"] += 1
            for t in triples:
                s = t.get("s")
                o = t.get("o")
                p = t.get("p")
                modalities = t.get("modalities")
                conf = safe_float(t.get("confidence"), default=0.0)

                if not (is_nonempty_str(s) and is_nonempty_str(o)):
                    continue
                slide_triples_total += 1
                st["triples_total"] += 1

                # image modality flag
                if modalities_has_image(modalities):
                    slide_image_modality_hits += 1
                    st["triples_with_image_modality"] += 1

                # verbatim checks for s/o
                s_bad = has_text and not contains_verbatim(slide_text, s)
                o_bad = has_text and not contains_verbatim(slide_text, o)
                if s_bad:
                    st["triples_s_not_in_text"] += 1
                if o_bad:
                    st["triples_o_not_in_text"] += 1
                if s_bad or o_bad:
                    slide_triple_not_in_text += 1
                    if len(violation_samples) < 500:
                        violation_samples.append({
                            "lecture": lecture,
                            "slide_id": slide_id,
                            "model": model_name,
                            "type": "triple_entity_not_in_text",
                            "term_or_entity": f"s={s} | p={p} | o={o} | conf={conf}"
                        })

        # Compute "image-heavy score" for slide:
        # - fraction of triples that explicitly mark image modality (strong signal)
        # - fraction of extracted items not in text (signal of image reliance or instruction violation)
        # We keep it simple & explainable.
        img_modality_rate = (slide_image_modality_hits / slide_triples_total) if slide_triples_total else 0.0
        not_in_text_rate = 0.0
        denom = (slide_concept_total + slide_triples_total)
        if denom > 0 and has_text:
            not_in_text_rate = (slide_concept_not_in_text + slide_triple_not_in_text) / denom

        # Final score: weighted combination (tunable)
        # Image modality is more reliable than "not in text" (which could be hallucination),
        # so give it higher weight.
        image_heavy_score = 0.7 * img_modality_rate + 0.3 * not_in_text_rate

        ranked_rows.append({
            "lecture": lecture,
            "slide_id": slide_id,
            "slide_json": str(sf),
            "has_text": int(has_text),
            "models_count": slide_models_count,
            "concepts_total": slide_concept_total,
            "concepts_not_in_text": slide_concept_not_in_text if has_text else "",
            "triples_total": slide_triples_total,
            "triples_with_image_modality": slide_image_modality_hits,
            "triple_entities_not_in_text": slide_triple_not_in_text if has_text else "",
            "img_modality_rate": round(img_modality_rate, 4),
            "not_in_text_rate": round(not_in_text_rate, 4) if has_text else "",
            "image_heavy_score": round(image_heavy_score, 4),
        })

    # Sort slides by score descending
    ranked_rows.sort(key=lambda r: (r["image_heavy_score"], r["triples_with_image_modality"], r["triples_total"]), reverse=True)

    # Write ranked CSV
    ranked_csv = out_dir / "slides_ranked_image_heavy.csv"
    with ranked_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ranked_rows[0].keys()))
        w.writeheader()
        w.writerows(ranked_rows)

    # Write per-model metrics CSV
    model_csv = out_dir / "model_metrics.csv"
    model_rows = []
    for m, st in sorted(model_stats.items(), key=lambda kv: kv[0].lower()):
        slides_seen = st["slides_seen"]
        denom_concepts = st["concept_terms_total"] if st["concept_terms_total"] else 1.0
        denom_triples = st["triples_total"] if st["triples_total"] else 1.0

        model_rows.append({
            "model": m,
            "slides_seen": int(slides_seen),
            "slides_with_text": int(st["slides_with_text"]),
            "slides_with_concepts": int(st["slides_with_concepts"]),
            "slides_with_triples": int(st["slides_with_triples"]),
            "concept_terms_total": int(st["concept_terms_total"]),
            "concept_terms_not_in_text": int(st["concept_terms_not_in_text"]),
            "concept_verbatim_ok_rate": round(1.0 - (st["concept_terms_not_in_text"] / denom_concepts), 4),
            "triples_total": int(st["triples_total"]),
            "triples_with_image_modality": int(st["triples_with_image_modality"]),
            "triple_image_modality_rate": round(st["triples_with_image_modality"] / denom_triples, 4),
            "triples_s_not_in_text": int(st["triples_s_not_in_text"]),
            "triples_o_not_in_text": int(st["triples_o_not_in_text"]),
        })

    with model_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(model_rows[0].keys()))
        w.writeheader()
        w.writerows(model_rows)

    # Write a small violations sample CSV (capped)
    viol_csv = out_dir / "violations_samples.csv"
    if violation_samples:
        with viol_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(violation_samples[0].keys()))
            w.writeheader()
            w.writerows(violation_samples)

    # Write markdown summary
    md = out_dir / "report_summary.md"
    topk = min(args.topk, len(ranked_rows))
    with md.open("w", encoding="utf-8") as f:
        f.write("# Snapshot Analysis Report (Merged Slide JSONs)\n\n")
        f.write(f"- Root scanned: `{root}`\n")
        f.write(f"- Slides found: **{len(slide_files)}**\n")
        f.write(f"- Models found: **{len(model_stats)}**\n\n")

        f.write("## Top image-heavy slide candidates\n\n")
        f.write("This ranking uses a weighted score:\n")
        f.write("- `img_modality_rate` = fraction of triples that include `modalities: [\"image\"]`\n")
        f.write("- `not_in_text_rate` = fraction of extracted items (concept terms + triples) that do **not** appear in slide text\n")
        f.write("- `image_heavy_score = 0.7*img_modality_rate + 0.3*not_in_text_rate`\n\n")

        f.write("| Rank | Lecture | Slide | Score | img_modality_rate | not_in_text_rate | triples(image/total) | concepts_not_in_text |\n")
        f.write("|---:|---|---|---:|---:|---:|---:|---:|\n")
        for i in range(topk):
            r = ranked_rows[i]
            f.write(
                f"| {i+1} | {r['lecture']} | {r['slide_id']} | {r['image_heavy_score']} | "
                f"{r['img_modality_rate']} | {r['not_in_text_rate']} | "
                f"{r['triples_with_image_modality']}/{r['triples_total']} | {r['concepts_not_in_text']} |\n"
            )

        f.write("\n## Per-model behavior summary\n\n")
        f.write("| Model | slides_seen | concept_verbatim_ok_rate | triple_image_modality_rate | concepts_not_in_text | triples_total |\n")
        f.write("|---|---:|---:|---:|---:|---:|\n")
        for row in sorted(model_rows, key=lambda x: x["slides_seen"], reverse=True):
            f.write(
                f"| {row['model']} | {row['slides_seen']} | {row['concept_verbatim_ok_rate']} | "
                f"{row['triple_image_modality_rate']} | {row['concept_terms_not_in_text']} | {row['triples_total']} |\n"
            )

        f.write("\n## Output files\n\n")
        f.write(f"- `{ranked_csv.name}`: ranked per-slide table\n")
        f.write(f"- `{model_csv.name}`: per-model metrics\n")
        if violation_samples:
            f.write(f"- `{viol_csv.name}`: sampled violations (capped)\n")

    print(f"[OK] Wrote:\n  {ranked_csv}\n  {model_csv}\n  {md}")
    if violation_samples:
        print(f"  {viol_csv}")

if __name__ == "__main__":
    main()