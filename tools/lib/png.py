"""Minimal PNG and JPEG-free image I/O for the Prismatic Shards asset tools.

This module is part of the *development* tooling. It is deliberately
dependency-free (stdlib `zlib` + `struct` only) so that the wallpapers,
previews and cursor artwork in this repository can be regenerated on any
machine with a stock Python 3.11+, without Pillow, cairo or ImageMagick.

Public API
----------
write_png(path, width, height, pixels, channels=3)
    `pixels` is a bytes-like object of width*height*channels interleaved
    samples (RGB or RGBA, 8 bit per channel).
read_png_header(path)
    Returns (width, height, bit_depth, colour_type) for validation.

Nothing here is used at runtime by the installed theme.
"""

from __future__ import annotations

import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

COLOUR_TYPE_RGB = 2
COLOUR_TYPE_RGBA = 6


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + tag
        + payload
        + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    )


def write_png(path: str, width: int, height: int, pixels, channels: int = 3) -> int:
    """Write an 8-bit RGB/RGBA PNG and return the number of bytes written."""
    if channels not in (3, 4):
        raise ValueError("channels must be 3 (RGB) or 4 (RGBA)")

    expected = width * height * channels
    data = bytes(pixels)
    if len(data) != expected:
        raise ValueError(f"expected {expected} bytes, got {len(data)}")

    colour_type = COLOUR_TYPE_RGB if channels == 3 else COLOUR_TYPE_RGBA
    stride = width * channels

    # Filter type 0 (None) per scanline. Gradients this smooth compress well
    # enough that a smarter filter would only cost CPU time.
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw += data[y * stride : (y + 1) * stride]

    ihdr = struct.pack(">IIBBBBB", width, height, 8, colour_type, 0, 0, 0)
    blob = (
        PNG_SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )

    with open(path, "wb") as handle:
        handle.write(blob)
    return len(blob)


def read_png_header(path: str):
    """Return (width, height, bit_depth, colour_type) of a PNG file."""
    with open(path, "rb") as handle:
        head = handle.read(33)

    if head[:8] != PNG_SIGNATURE:
        raise ValueError(f"{path}: not a PNG")
    if head[12:16] != b"IHDR":
        raise ValueError(f"{path}: missing IHDR")

    width, height, bit_depth, colour_type = struct.unpack(">IIBB", head[16:26])
    return width, height, bit_depth, colour_type


def read_png_rgba(path: str, width: int, height: int) -> bytearray:
    """Decode a non-interlaced 8-bit RGB/RGBA PNG (used by the validator)."""
    with open(path, "rb") as handle:
        blob = handle.read()

    if blob[:8] != PNG_SIGNATURE:
        raise ValueError(f"{path}: not a PNG")

    pos = 8
    idat = bytearray()
    colour_type = None
    while pos < len(blob):
        (length,) = struct.unpack(">I", blob[pos : pos + 4])
        tag = blob[pos + 4 : pos + 8]
        payload = blob[pos + 8 : pos + 8 + length]
        crc = struct.unpack(">I", blob[pos + 8 + length : pos + 12 + length])[0]
        if crc != (zlib.crc32(tag + payload) & 0xFFFFFFFF):
            raise ValueError(f"{path}: bad CRC in {tag!r}")
        if tag == b"IHDR":
            colour_type = payload[9]
        elif tag == b"IDAT":
            idat += payload
        elif tag == b"IEND":
            break
        pos += 12 + length

    channels = {COLOUR_TYPE_RGB: 3, COLOUR_TYPE_RGBA: 4}[colour_type]
    raw = zlib.decompress(bytes(idat))
    stride = width * channels

    out = bytearray(width * height * 4)
    previous = bytearray(stride)
    offset = 0
    for y in range(height):
        filter_type = raw[offset]
        offset += 1
        line = bytearray(raw[offset : offset + stride])
        offset += stride
        if filter_type == 1:  # Sub
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif filter_type == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif filter_type == 3:  # Average
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif filter_type == 4:  # Paeth
            for i in range(stride):
                left = line[i - channels] if i >= channels else 0
                up = previous[i]
                upleft = previous[i - channels] if i >= channels else 0
                p = left + up - upleft
                pa, pb, pc = abs(p - left), abs(p - up), abs(p - upleft)
                if pa <= pb and pa <= pc:
                    pred = left
                elif pb <= pc:
                    pred = up
                else:
                    pred = upleft
                line[i] = (line[i] + pred) & 0xFF
        elif filter_type != 0:
            raise ValueError(f"{path}: unsupported filter {filter_type}")

        previous = line
        base = y * width * 4
        if channels == 4:
            out[base : base + width * 4] = line
        else:
            for x in range(width):
                out[base + x * 4 : base + x * 4 + 3] = line[x * 3 : x * 3 + 3]
                out[base + x * 4 + 3] = 255

    return out
