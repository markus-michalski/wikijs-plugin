"""Display width for wiki screenshots (stdlib only, no network, no uploads).

Screenshots are captured at viewport 1200 px and device pixel ratio 2, then
cropped without rescaling. The width to embed is therefore pixel width / 2.
Full-width screens (about 2400 px) are embedded without a width, cropped
strips and blocks get ``=Wx``.

Usable as a library (``read_image_size``, ``assess``, ``markdown_image``) and
as a script::

    run-server servers/wikijs-mcp-server/tools/screenshot_width.py shot.png
    run-server servers/wikijs-mcp-server/tools/screenshot_width.py shot.png \
        --url "https://cdn.example/.../shot.webp" --alt "Settings page"
"""
from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

# A full-viewport capture at DPR 2 is 2400 px wide. Anything at or above this
# is treated as a full-width screen and needs no width.
FULL_SCREEN_MIN_PX = 1700
# Below this a file is either a small DPR 2 crop or a DPR 1 capture.
SMALL_CROP_MAX_PX = 800
# Header bytes that are enough to read the size of PNG and WebP files.
HEADER_BYTES = 4096

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def read_image_size(data: bytes) -> tuple[int, int] | None:
    """Return (width, height) of a PNG or WebP from its header bytes, else None.

    A truncated download is fine as long as it contains the header, so a
    partial HTTP range request can be passed in directly.
    """
    size: tuple[int, int] | None = None

    if data[:8] == _PNG_SIGNATURE and len(data) >= 24 and data[12:16] == b"IHDR":
        size = struct.unpack(">II", data[16:24])

    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP" and len(data) >= 30:
        kind = data[12:16]
        if kind == b"VP8 " and data[23:26] == b"\x9d\x01\x2a":
            width, height = struct.unpack("<HH", data[26:30])
            size = (width & 0x3FFF, height & 0x3FFF)
        elif kind == b"VP8L" and data[20] == 0x2F:
            bits = struct.unpack("<I", data[21:25])[0]
            size = ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
        elif kind == b"VP8X":
            size = (
                int.from_bytes(data[24:27], "little") + 1,
                int.from_bytes(data[27:30], "little") + 1,
            )

    # A zero dimension means a malformed header, not an image.
    if size is None or size[0] == 0 or size[1] == 0:
        return None
    return size


def display_width(pixel_width: int) -> int:
    """Width to embed for a DPR 2 capture: pixel width / 2, rounded down."""
    return pixel_width // 2


@dataclass(frozen=True)
class Assessment:
    level: str  # "ok" | "warn"
    kind: str  # "full" | "crop" | "small"
    suggested_width: int | None  # None means: embed without a width
    message: str


def assess(pixel_width: int, declared_width: int | None = None) -> Assessment:
    """Judge a screenshot of ``pixel_width`` px, embedded with ``declared_width``.

    ``declared_width`` is the ``=Wx`` value on the image, or None when the image
    is embedded without a width.
    """
    if pixel_width >= FULL_SCREEN_MIN_PX:
        kind = "full"
        suggested: int | None = None
    elif pixel_width >= SMALL_CROP_MAX_PX:
        kind = "crop"
        suggested = display_width(pixel_width)
    else:
        kind = "small"
        suggested = display_width(pixel_width)

    if declared_width is None:
        if kind == "full":
            return Assessment("ok", kind, None, "full-width screen, no width needed")
        if kind == "crop":
            return Assessment(
                "warn", kind, suggested,
                f"cropped image without a display width, embed with ={suggested}x",
            )
        return Assessment(
            "warn", kind, suggested,
            f"only {pixel_width} px wide: a small DPR 2 crop (={suggested}x) or a DPR 1 capture "
            f"(={pixel_width}x), check how it was captured",
        )

    # A width equal to the pixel width only fits a small DPR 1 capture. For a
    # larger file it is the double-size case the rule is meant to catch.
    if abs(pixel_width - 2 * declared_width) <= 2 or (kind == "small" and pixel_width == declared_width):
        return Assessment("ok", kind, suggested, "display width matches the pixel width")
    expected = display_width(pixel_width)
    return Assessment(
        "warn", kind, suggested,
        f"={declared_width}x does not match {pixel_width} px (pixel width / 2 is {expected}); "
        "fine for an older upscaled image, otherwise correct the width",
    )


def markdown_image(alt: str, url: str, pixel_width: int) -> str:
    """Finished markdown image line with the right display width.

    Full-width screens get no width, everything else ``=Wx`` (pixel width / 2).
    """
    width = assess(pixel_width).suggested_width
    suffix = f" ={width}x" if width is not None else ""
    return f"![{alt}]({url}{suffix})"


def _read_header(path: Path) -> bytes | None:
    try:
        return path.read_bytes()[:HEADER_BYTES]
    except OSError as exc:
        print(f"{path.name}: cannot read file ({exc.strerror or exc})", file=sys.stderr)
        return None


def _report(path: Path) -> int:
    header = _read_header(path)
    if header is None:
        return 1
    size = read_image_size(header)
    if size is None:
        print(f"{path.name}: not a PNG or WebP file, size unknown", file=sys.stderr)
        return 1
    width, height = size
    result = assess(width)
    shown = f"={result.suggested_width}x" if result.suggested_width is not None else "no width"
    flag = "WARN" if result.kind == "small" else "ok  "
    print(f"{flag} {path.name}: {width}x{height} px, embed with {shown} ({result.kind})")
    if result.kind == "small":
        print(f"     {result.message}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Display width for wiki screenshots (DPR 2 rule).")
    parser.add_argument("files", nargs="+", type=Path, help="PNG or WebP files")
    parser.add_argument("--url", help="CDN URL of the uploaded file, prints the finished markdown line")
    parser.add_argument("--alt", default="", help="alt text for the markdown line")
    args = parser.parse_args(argv)

    if args.url and len(args.files) != 1:
        parser.error("--url works with exactly one file")

    status = 0
    for path in args.files:
        status |= _report(path)

    if args.url and status == 0:
        header = _read_header(args.files[0])
        size = read_image_size(header) if header is not None else None
        if size is None:
            return 1
        print(markdown_image(args.alt, args.url, size[0]))
    return status


if __name__ == "__main__":
    sys.exit(main())
