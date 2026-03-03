# Avatar_GoELS — Evidence-grounded reliability diagnostics for structured slide understanding

This repository contains the **reproducible analysis pipeline** used in our CVPR-style submission on **evidence-grounded structured extraction** from educational slides (MILU23: 23 lectures, 1,117 slides).  
We analyze cached structured outputs (concepts + relation triples) from multiple open VLMs and evaluate reliability via **transcript/OCR grounding**, **evidence-source ablations**, **modality tag calibration**, and **secondary stability/consensus diagnostics**, complemented by a lightweight human audit.

> Note: The full MILU23 slide images/transcripts and per-slide JSON outputs are not distributed here. This repo releases the **code**, **definitions**, and **paper-facing aggregate artifacts** needed to reproduce tables/figures from provided CSVs, and to rerun the pipeline on your own compatible data.

---

## Repository layout

- `Codes/*.py` — analysis scripts organized by phase (Phase 0–5)
- `Codes/paper_assets/` — LaTeX-ready tables used in the paper
- `Codes/phase2_out/figures/` — paper figures derived from aggregate CSVs
- `Codes/phase3_out/figures/` — stability figures (main paper / appendix)
- `Codes/phase4_out/figures/` — modality calibration plots
- `Codes/phase5_out/` — audit summaries + manual proxy validation CSV

---

## Environment

Tested with Python 3.10+ (recommended). Install dependencies:

```bash
pip install -r requirements.txt
