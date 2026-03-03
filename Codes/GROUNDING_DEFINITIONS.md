# Grounding Definitions (Frozen)

Dataset unit: one slide = (slide image, aligned transcript text).

## Grounding sources
1) Transcript-grounded:
   A string appears verbatim (case-insensitive substring match) in the slide transcript text file referenced by `paths.text`.

2) Slide-grounded (OCR):
   A string appears verbatim (case-insensitive substring match) in OCR text extracted from the slide image referenced by `paths.image`.

3) Ungrounded:
   The string appears in neither transcript nor OCR.

## Validity rules
Concept validity:
- A concept term is valid if it is transcript-grounded OR OCR-grounded.

Triple validity:
- A triple (s, p, o) is valid if:
  - s is transcript-grounded OR OCR-grounded, AND
  - o is transcript-grounded OR OCR-grounded, AND
  - predicate p belongs to the allowed predicate set.

## Hallucination
- Any extracted concept or triple entity that is ungrounded is treated as hallucinated/invalid grounding.