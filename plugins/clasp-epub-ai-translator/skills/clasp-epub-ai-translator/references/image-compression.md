# Image delivery compression

Keep a lossless reviewed master, then choose the EPUB delivery image. Compression is a normal part of the reviewed image stage; preserve unmodified images byte-for-byte unless the user requests broader compression. Never overwrite the input or the master.

## Measure against the input EPUB

Measure ZIP entry `file_size` and `compress_size` as well as standalone files; EPUB already compresses many resources. Record input and final EPUB sizes. An edited JPEG saved as PNG can grow substantially even after PNG optimization, especially with scan paper texture. If this drives book growth, examine the largest changed images and their delivery formats rather than only reporting savings over an unoptimized master. A second master EPUB is not required just to compute savings.

Distinguish file size from pixel dimensions. Side-by-side comparison sheets have a wider canvas but do not belong in the final EPUB. Do not delete resources, remove paper texture, quantize approximately, or downsample merely to hit an arbitrary size target.

## Choose per image

- Line art, tables, and dense small-label diagrams: prefer lossless PNG, particularly when JPEG savings are minor. Exact neutral RGB may become grayscale only after decoded RGBA equality is proven; approximate palette reduction is not lossless.
- Edited textured scan maps and illustrations: start losslessly. If PNG growth over the source JPEG is a major contributor to book growth, compare a few high-quality JPEG candidates from the reviewed master, for example qualities 95 and 92 with 4:4:4 sampling. These are starting points, not mandatory settings. Keep the lossless master and disclose lossy delivery. If the user requires lossless or pixel-identical delivery, retain lossless output.
- Covers and photos: first optimize losslessly. If JPEG is useful, inspect small text, edges, gradients, shadows, and repair seams before choosing it.
- Unmodified existing JPEG: normally preserve it. Every new candidate must come from the same reviewed master, never a previously compressed candidate.
- Transparent images, formulas, and SVG: preserve alpha or structure; do not rasterize SVG or flatten transparency by default.
- Keep original dimensions. Different images may use different formats and quality settings; one suitable JPEG does not justify converting every image.

## Review candidates and stop

Start with a small, meaningful candidate set, not a sweep through every quality value. Record the master, candidate format/settings, size, and review outcome. Inspect each whole image and compare enlarged small text, vertical labels, brackets, numbers, location dots, airport symbols, dashed routes, and repaired boundaries against the master. Look for ringing, broken or merged strokes, gray halos, and seams. A lower file size or average error score is not a readability check.

Stop once a smaller acceptable candidate is selected. If candidates fail, retain the lossless image or change approach for a concrete identified reason. Do not repeatedly recompress, blindly reduce quality, or retry an unchanged method. Explain unavoidable size tradeoffs.

## Lossless PNG helper

```bash
uv run --script scripts/optimize_png.py /absolute/master.png \
  --output /absolute/delivery.png \
  --report /absolute/compression.json
```

This helper preserves the original when optimization is not smaller and accepts alternate PNG encodings only when decoded RGBA pixels, dimensions, alpha, and supported color profile data remain identical. It does not produce JPEG or choose a lossy quality automatically.

## Verify and report separately

- Original image to lossless translated master: semantic/visual checks plus explicit edit-mask and protected-region pixel audit.
- Master to delivery image: decoded pixel equality for lossless output; a separate final-image readability review and explicit lossy disclosure for JPEG. Never use the master pixel audit as evidence that JPEG pixels are unchanged.
- Pack the selected files using `epub_images.py`, updating both decision outputs and replacement paths. Its format detection updates extension, MIME, and references. Confirm packed image bytes match selected files and that prose, spine, links, and untouched images remain intact.
- Report input EPUB to final EPUB size and percentage change, resolution changes, and which images are lossy. If also comparing a master-image EPUB to a compact EPUB, label that baseline separately. The pack report's `source_bytes` and `output_bytes` supply actual package sizes. Keep masters, comparisons, and audit records outside the delivered EPUB.
