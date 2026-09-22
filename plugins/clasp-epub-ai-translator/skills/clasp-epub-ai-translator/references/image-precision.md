# Image regions, typesetting, and pixel audit

Use integer source-pixel rectangles `[left, top, right, bottom]` with the lower-right boundary excluded. A useful record is:

```json
{
  "patches": [
    {"id": "calendar-note", "source": "休日運休", "translation": "假日停运", "box": [100, 200, 180, 220], "status": "checked"}
  ],
  "protected_regions": [[185, 200, 260, 220]],
  "allowed_regions": [[96, 196, 184, 224]]
}
```

Coordinates above are examples only. `box` records old text; `allowed_regions` records the actual erase, repair, blend, and typesetting footprint. Select protection regions independently from the source image. For irregular edits, use a same-size grayscale mask: black forbids change, any non-zero value allows it.

Use a font with verified target glyph coverage. Match family, weight, color, writing direction, spacing, and actual visible height. Account for font bounding-box offsets and baselines. Render text at high resolution and downsample the text layer only; keep the underlying image at original size. For long translations, prefer concise accurate wording, tracking, font size, or natural line breaks over anisotropic stretching.

For maps, separate text, identifiers, location dots, and lines when defining erase regions. The bounding rectangle of a slanted or spaced-out label may contain protected map information; prefer per-character boxes or an irregular mask. Lay out the translation in independently chosen clear space rather than filling the old bounding box.

Choose a target visible text height from neighboring labels of the same rank, then fit using glyph bounds with clearance from symbols and borders. A short translation need not fill the original width. Prefer sensible wrapping, vertical layout, or nearby clear space over shrinking indefinitely or stretching glyphs. For font collections such as TTC, inspect family/style names: the default face can be Black or Bold rather than Regular, and face indexes are not portable.

Small labels can be rendered on a transparent text layer at 2–4× resolution and scaled back uniformly. For vertical text, explicitly position characters and suitable vertical brackets; check character order, punctuation, spacing, and glyph coverage. Keep the base image untouched by resampling.

If protected pixels change, identify the conflicting erase region or text placement and correct it. Restoring original markers is not sufficient by itself: inspect the composite so restoration does not cut through the new text. Review clean output with neighboring content visible, not only annotated boxes or difference maps.

```bash
uv run --script scripts/audit_regions.py \
  --original /absolute/source.png \
  --edited /absolute/translated.png \
  --regions /absolute/regions.json \
  --report /absolute/audit.json \
  --diff /absolute/difference.png
```

The report checks dimensions, changed RGBA pixels, changes outside the whitelist, and changes inside protected regions. Gray is unchanged, red is allowed change, magenta is outside-whitelist change, and orange is protected-region change. A pass proves only the declared pixel constraints. It does not detect wrong translations, missed text, or a mistakenly broad whitelist.
