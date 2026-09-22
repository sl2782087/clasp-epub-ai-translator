# Covers and designed artwork

## Treat titles as typography groups

A cover title is usually a complete layout group, not a collection of isolated OCR boxes. If only kana are replaced while old kanji remain, mixed fonts, baselines, and weights often look visibly wrong. Unless the user requires specific source glyph pixels to remain untouched, rebuild the whole title group with one coordinated family, weight, scale, color, alignment, line structure, and spacing.

Measure the complete translation before removing source text. Prefer changing the whole group's font size, tracking, or line breaks over squeezing individual words into old boxes. Keep natural aspect ratio; do not independently stretch width and height. Use optical correction when Latin digits and CJK glyphs have different apparent heights.

## Review the clean plate first

Save the background without replacement text as `clean-plate.png`. Its mask must cover source glyphs, antialiasing, outlines, shadows, glow, and compression bleed while preserving artwork and decoration. Prefer layered source art, a known clean original, local cloning, and bounded repair in that order. If generative editing is necessary, request background reconstruction only and composite only the mask back onto the source.

At original size and 2–4×, reject any readable old outline, haze, block seam, erased decoration, crop, or composition change. New text must never be used to hide a failed clean plate.

## Four cover gates

- `background_review`: clean plate approved independently.
- `typography_review`: text layer viewed on a neutral background; glyphs, baselines, spacing, weights, and natural proportions approved.
- `text_review`: full title, author, numbers, names, and punctuation checked character by character.
- `pixel_audit`: approved edit mask and independent protected regions pass.

Only after all four gates pass may the cover enter the replacement map. Pixel checks cannot automatically approve the other three gates.
