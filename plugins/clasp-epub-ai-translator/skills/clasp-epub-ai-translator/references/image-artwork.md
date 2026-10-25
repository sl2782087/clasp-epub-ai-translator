# Covers and designed artwork

## Method judgment (required before editing)

Decide each text-bearing image by the **role of its lettering**, not only by file name:

1. **Designed typography / layout** — cover title stacks, styled lettering, designed front-matter title groups, text whose weight/tracking/decoration is bound to the composition: use **whole-image generation** (configured model, typically gpt-image-2) so Chinese glyphs are painted into the pixels. Match hierarchy, weight, tracking, alignment, color, and decoration. **Forbidden as final delivery:** erase-and-paste, clean-plate plus local/Pillow overlay, Japanese/kana remnants.

2. **Informational labels only** — map notes, floorplan room tags, table cells, timetables, diagram callouts with no designed title group: **erase then replace/overlay** with deterministic typesetting is OK. Still match the original as closely as possible: position, size, color, and writing direction; no occlusion of neighboring lines/numbers/icons, no misalignment, no stretch, no leftover source glyphs. Inspect at original size and 2–4×.

When unsure, treat as designed typography and use whole-image generation.

Drive cover / designed-title generation through Codex in the CLASP pipeline. Show side-by-side compare (and title-band zoom) and wait for user visual approval before packaging.

## Treat titles as typography groups

A cover title is usually a complete layout group, not a collection of isolated OCR boxes. Rebuild the whole title group in one coordinated generation pass: family, weight, scale, color, alignment, line structure, and spacing should stay consistent with the source cover.

Measure the complete translation before generating. Prefer natural line breaks and optical size matching over squeezing words into old boxes. Keep natural aspect ratio; do not independently stretch width and height.

## Four cover gates (whole-image edition)

- `background_review`: photographic/illustration regions and decorations retain composition; no crop or layout collapse.
- `typography_review`: title hierarchy, weight, spacing, and style match the source; lettering is model-generated in-pixel, not a pasted layer.
- `text_review`: full title, author, numbers, names, and punctuation checked character by character; no Japanese/kana remnants.
- `pixel_audit`: final dimensions match source; record method as whole-image generation; confirm no local text overlay was used for delivery.

Only after all four gates pass and the user approves the cover may it enter the replacement map / packaging step.
