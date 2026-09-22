# Image delivery compression

Keep a lossless reviewed master, then choose the EPUB delivery image. Measure ZIP entry sizes as well as standalone files; EPUB already compresses many resources.

- Line art, tables, maps, and scans: prefer lossless PNG. Exact neutral RGB may become grayscale only after decoded RGBA equality is proven.
- Covers and photos: first optimize losslessly. If JPEG is necessary, create candidates from the same master, inspect small text, edges, gradients, shadows, and repair seams, and explicitly report lossy output.
- Existing JPEG: normally preserve it. Never repeatedly recompress a previous candidate.
- Transparent images and SVG: preserve alpha or structure; do not rasterize SVG by default.
- Keep original dimensions unless a separate readability review authorizes downsampling.

```bash
uv run --script scripts/optimize_png.py /absolute/master.png \
  --output /absolute/delivery.png \
  --report /absolute/compression.json
```

This helper preserves the original when optimization is not smaller and accepts alternate PNG encodings only when decoded RGBA pixels, dimensions, alpha, and supported color profile data remain identical. Translation edit auditing and delivery compression verification are separate checks; do not use one report as evidence for the other.
