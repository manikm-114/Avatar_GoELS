# Snapshot Analysis Report (Merged Slide JSONs)

- Root scanned: `.`
- Slides found: **1117**
- Models found: **5**

## Top image-heavy slide candidates

This ranking uses a weighted score:
- `img_modality_rate` = fraction of triples that include `modalities: ["image"]`
- `not_in_text_rate` = fraction of extracted items (concept terms + triples) that do **not** appear in slide text
- `image_heavy_score = 0.7*img_modality_rate + 0.3*not_in_text_rate`

| Rank | Lecture | Slide | Score | img_modality_rate | not_in_text_rate | triples(image/total) | concepts_not_in_text |
|---:|---|---|---:|---:|---:|---:|---:|
| 1 | Lecture 19 | Slide43 | 1.0 | 1.0 | 1.0 | 1/1 | 3 |
| 2 | Lecture 19 | Slide53 | 1.0 | 1.0 | 1.0 | 1/1 | 2 |
| 3 | Lecture 19 | Slide38 | 0.88 | 1.0 | 0.6 | 2/2 | 2 |
| 4 | Lecture 17 | Slide22 | 0.85 | 1.0 | 0.5 | 2/2 | 1 |
| 5 | Lecture 13 | Slide10 | 0.85 | 1.0 | 0.5 | 1/1 | 1 |
| 6 | Lecture 19 | Slide14 | 0.85 | 1.0 | 0.5 | 1/1 | 1 |
| 7 | Lecture 19 | Slide7 | 0.85 | 1.0 | 0.5 | 1/1 | 1 |
| 8 | Lecture 5 | Slide11 | 0.85 | 1.0 | 0.5 | 1/1 | 1 |
| 9 | Lecture 5 | Slide20 | 0.85 | 1.0 | 0.5 | 1/1 | 1 |
| 10 | Lecture 5 | Slide22 | 0.85 | 1.0 | 0.5 | 1/1 | 2 |
| 11 | Lecture 5 | Slide25 | 0.85 | 1.0 | 0.5 | 1/1 | 2 |
| 12 | Lecture 21 | Slide34 | 0.8286 | 1.0 | 0.4286 | 3/3 | 1 |
| 13 | Lecture 5 | Slide10 | 0.82 | 1.0 | 0.4 | 2/2 | 1 |
| 14 | Lecture 17 | Slide37 | 0.82 | 1.0 | 0.4 | 1/1 | 1 |
| 15 | Lecture 7 | Slide40 | 0.82 | 1.0 | 0.4 | 1/1 | 2 |
| 16 | Lecture 5 | Slide43 | 0.8 | 1.0 | 0.3333 | 1/1 | 0 |
| 17 | Lecture 10 | Slide47 | 0.775 | 1.0 | 0.25 | 1/1 | 1 |
| 18 | Lecture 13 | Slide19 | 0.775 | 1.0 | 0.25 | 1/1 | 0 |
| 19 | Lecture 13 | Slide23 | 0.775 | 1.0 | 0.25 | 1/1 | 1 |
| 20 | Lecture 19 | Slide21 | 0.775 | 1.0 | 0.25 | 1/1 | 0 |
| 21 | Lecture 19 | Slide27 | 0.775 | 1.0 | 0.25 | 1/1 | 1 |
| 22 | Lecture 19 | Slide41 | 0.775 | 1.0 | 0.25 | 1/1 | 1 |
| 23 | Lecture 19 | Slide49 | 0.775 | 1.0 | 0.25 | 1/1 | 2 |
| 24 | Lecture 19 | Slide51 | 0.775 | 1.0 | 0.25 | 1/1 | 0 |
| 25 | Lecture 19 | Slide9 | 0.775 | 1.0 | 0.25 | 1/1 | 0 |
| 26 | Lecture 5 | Slide19 | 0.775 | 1.0 | 0.25 | 1/1 | 1 |
| 27 | Lecture 6 | Slide12 | 0.775 | 1.0 | 0.25 | 1/1 | 0 |
| 28 | Lecture 5 | Slide49 | 0.76 | 1.0 | 0.2 | 2/2 | 0 |
| 29 | Lecture 6 | Slide35 | 0.76 | 1.0 | 0.2 | 2/2 | 0 |
| 30 | Lecture 23 | Slide47 | 0.76 | 1.0 | 0.2 | 1/1 | 1 |
| 31 | Lecture 16 | Slide45 | 0.75 | 1.0 | 0.1667 | 2/2 | 0 |
| 32 | Lecture 9 | Slide6 | 0.75 | 1.0 | 0.1667 | 2/2 | 0 |
| 33 | Lecture 22 | Slide18 | 0.7462 | 1.0 | 0.1538 | 3/3 | 1 |
| 34 | Lecture 22 | Slide38 | 0.7429 | 1.0 | 0.1429 | 3/3 | 1 |
| 35 | Lecture 22 | Slide6 | 0.7429 | 1.0 | 0.1429 | 3/3 | 1 |
| 36 | Lecture 23 | Slide37 | 0.7429 | 1.0 | 0.1429 | 3/3 | 1 |
| 37 | Lecture 11 | Slide47 | 0.74 | 1.0 | 0.1333 | 3/3 | 2 |
| 38 | Lecture 19 | Slide45 | 0.74 | 1.0 | 0.1333 | 2/2 | 1 |
| 39 | Lecture 23 | Slide10 | 0.74 | 1.0 | 0.1333 | 1/1 | 1 |
| 40 | Lecture 19 | Slide31 | 0.7375 | 1.0 | 0.125 | 1/1 | 1 |
| 41 | Lecture 4 | Slide31 | 0.7333 | 1.0 | 0.1111 | 1/1 | 1 |
| 42 | Lecture 19 | Slide6 | 0.73 | 1.0 | 0.1 | 2/2 | 1 |
| 43 | Lecture 1 | Slide36 | 0.73 | 1.0 | 0.1 | 1/1 | 1 |
| 44 | Lecture 11 | Slide11 | 0.73 | 1.0 | 0.1 | 1/1 | 1 |
| 45 | Lecture 13 | Slide46 | 0.73 | 1.0 | 0.1 | 1/1 | 1 |
| 46 | Lecture 9 | Slide27 | 0.7273 | 1.0 | 0.0909 | 3/3 | 1 |
| 47 | Lecture 13 | Slide39 | 0.7273 | 1.0 | 0.0909 | 1/1 | 0 |
| 48 | Lecture 1 | Slide39 | 0.7214 | 1.0 | 0.0714 | 1/1 | 0 |
| 49 | Lecture 23 | Slide2 | 0.7214 | 1.0 | 0.0714 | 1/1 | 1 |
| 50 | Lecture 6 | Slide38 | 0.7214 | 1.0 | 0.0714 | 1/1 | 0 |

## Per-model behavior summary

| Model | slides_seen | concept_verbatim_ok_rate | triple_image_modality_rate | concepts_not_in_text | triples_total |
|---|---:|---:|---:|---:|---:|
| llava-hf__llava-onevision-qwen2-7b-ov-hf | 1117 | 0.9509 | 0.1133 | 138 | 256 |
| OpenGVLab__InternVL3-14B | 1117 | 0.9847 | 0.0469 | 54 | 1193 |
| Qwen__Qwen2-VL-7B-Instruct | 1117 | 0.9338 | 0.4802 | 169 | 177 |
| Qwen__Qwen3-VL-4B-Instruct | 1117 | 0.8438 | 0.7124 | 238 | 685 |
| llava-hf__llava-onevision-qwen2-7b-ov-hf__text_only | 1112 | 1.0 | 0.0 | 0 | 0 |

## Output files

- `slides_ranked_image_heavy.csv`: ranked per-slide table
- `model_metrics.csv`: per-model metrics
- `violations_samples.csv`: sampled violations (capped)
