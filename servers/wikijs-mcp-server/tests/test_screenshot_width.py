"""Tests for the screenshot display-width helper (DPR 2 rule)."""
from __future__ import annotations

import struct
import zlib

import pytest
from tools.screenshot_width import (
    FULL_SCREEN_MIN_PX,
    assess,
    display_width,
    main,
    markdown_image,
    read_image_size,
)


def _png(width: int, height: int) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunk = b"IHDR" + ihdr
    return (
        b"\x89PNG\r\n\x1a\n"
        + struct.pack(">I", len(ihdr))
        + chunk
        + struct.pack(">I", zlib.crc32(chunk))
    )


def _riff(chunk_type: bytes, payload: bytes) -> bytes:
    body = b"WEBP" + chunk_type + struct.pack("<I", len(payload)) + payload
    return b"RIFF" + struct.pack("<I", len(body)) + body


def _webp_lossy(width: int, height: int) -> bytes:
    payload = b"\x00\x00\x00" + b"\x9d\x01\x2a" + struct.pack("<HH", width, height) + b"\x00" * 8
    return _riff(b"VP8 ", payload)


def _webp_lossless(width: int, height: int) -> bytes:
    bits = (width - 1) | ((height - 1) << 14)
    payload = b"\x2f" + struct.pack("<I", bits) + b"\x00" * 8
    return _riff(b"VP8L", payload)


def _webp_extended(width: int, height: int) -> bytes:
    payload = b"\x00\x00\x00\x00" + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    return _riff(b"VP8X", payload)


class TestReadImageSize:
    def test_png(self):
        assert read_image_size(_png(1075, 345)) == (1075, 345)

    def test_webp_lossy(self):
        assert read_image_size(_webp_lossy(1075, 345)) == (1075, 345)

    def test_webp_lossless(self):
        assert read_image_size(_webp_lossless(2400, 900)) == (2400, 900)

    def test_webp_extended(self):
        assert read_image_size(_webp_extended(1050, 358)) == (1050, 358)

    def test_truncated_download_is_fine(self):
        assert read_image_size(_png(2400, 1200)[:30]) == (2400, 1200)

    @pytest.mark.parametrize("size", [(0, 100), (100, 0), (0, 0)])
    def test_zero_dimension_is_rejected(self, size):
        assert read_image_size(_png(*size)) is None

    @pytest.mark.parametrize("data", [b"", b"GIF89a....", b"\x89PNG\r\n\x1a\n", b"<html>not an image</html>"])
    def test_unknown_data_returns_none(self, data):
        assert read_image_size(data) is None


class TestDisplayWidth:
    @pytest.mark.parametrize("pixels,expected", [(1075, 537), (1050, 525), (2400, 1200), (539, 269)])
    def test_pixel_width_halved(self, pixels, expected):
        assert display_width(pixels) == expected


class TestAssess:
    def test_full_screen_without_width_is_ok(self):
        result = assess(2400)
        assert (result.level, result.kind, result.suggested_width) == ("ok", "full", None)

    def test_crop_without_width_warns(self):
        result = assess(1075)
        assert (result.level, result.kind, result.suggested_width) == ("warn", "crop", 537)
        assert "=537x" in result.message

    def test_crop_with_matching_width_is_ok(self):
        assert assess(1075, 537).level == "ok"
        assert assess(1050, 525).level == "ok"

    def test_full_screen_with_matching_width_is_ok(self):
        assert assess(2400, 1200).level == "ok"

    def test_dpr1_image_at_native_width_is_ok(self):
        assert assess(539, 539).level == "ok"

    def test_large_file_at_its_full_pixel_width_warns(self):
        # 1075 px shown as =1075x is the double-size crop the rule is meant to catch
        result = assess(1075, 1075)
        assert result.level == "warn"
        assert "537" in result.message

    def test_small_dpr2_crop_with_half_width_is_ok(self):
        assert assess(600, 300).level == "ok"

    def test_mismatch_warns_and_names_expected_width(self):
        result = assess(1200, 525)
        assert result.level == "warn"
        assert "600" in result.message

    def test_small_file_without_width_warns_about_dpr(self):
        result = assess(542)
        assert (result.level, result.kind) == ("warn", "small")
        assert "DPR 1" in result.message

    def test_threshold_boundary(self):
        assert assess(FULL_SCREEN_MIN_PX).kind == "full"
        assert assess(FULL_SCREEN_MIN_PX - 1).kind == "crop"


class TestMarkdownImage:
    def test_crop_gets_width(self):
        assert markdown_image("Direct debit", "https://cdn/x.webp", 1075) == "![Direct debit](https://cdn/x.webp =537x)"

    def test_full_screen_gets_no_width(self):
        assert markdown_image("Settings", "https://cdn/x.webp", 2400) == "![Settings](https://cdn/x.webp)"


class TestCli:
    def test_reports_file(self, tmp_path, capsys):
        image = tmp_path / "block.png"
        image.write_bytes(_png(1075, 345))
        assert main([str(image)]) == 0
        assert "1075x345 px, embed with =537x" in capsys.readouterr().out

    def test_prints_markdown_with_url(self, tmp_path, capsys):
        image = tmp_path / "block.png"
        image.write_bytes(_png(1075, 345))
        assert main([str(image), "--url", "https://cdn/block.webp", "--alt", "Block"]) == 0
        assert "![Block](https://cdn/block.webp =537x)" in capsys.readouterr().out

    def test_small_file_prints_warning(self, tmp_path, capsys):
        image = tmp_path / "small.png"
        image.write_bytes(_png(542, 179))
        assert main([str(image)]) == 0
        out = capsys.readouterr().out
        assert "WARN" in out and "DPR" in out

    def test_missing_file_fails_without_traceback(self, tmp_path, capsys):
        assert main([str(tmp_path / "missing.png")]) == 1
        assert "cannot read file" in capsys.readouterr().err

    def test_unknown_file_fails(self, tmp_path):
        image = tmp_path / "x.txt"
        image.write_text("hello", encoding="utf-8")
        assert main([str(image)]) == 1
