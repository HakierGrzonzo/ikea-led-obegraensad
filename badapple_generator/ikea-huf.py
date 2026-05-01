#!/usr/bin/env python3
"""Huffman-compress 16×16 video frames from a directory.

Usage:
    python ikea-huf.py <glob_pattern> <output_file>
    python ikea-huf.py --verify <output_file>

Example:
    python ikea-huf.py "frames/*.png" badapple.huf
    python ikea-huf.py --verify badapple.huf

File format
-----------
  [4 B]  magic "IHUF"
  [4 B]  frame count (uint32 big-endian)
  [4 B]  tree bit-length (uint32 big-endian)
  [N B]  tree bytes (pre-order: '0'=internal, '1'+8-bit symbol=leaf)
  per frame:
    [4 B]  compressed bit-length (uint32 big-endian)
    [N B]  compressed bytes (MSB-first, zero-padded to byte boundary)
"""

import glob
import heapq
import struct
import sys
from collections import Counter

from PIL import Image

MAGIC = b"IHUF"
FRAME_W = 16
FRAME_H = 16
FRAME_PIXELS = FRAME_W * FRAME_H


# ── Huffman tree ──────────────────────────────────────────────────────────────

class Node:
    __slots__ = ("symbol", "freq", "left", "right")

    def __init__(self, symbol, freq, left=None, right=None):
        self.symbol = symbol
        self.freq = freq
        self.left = left
        self.right = right

    def __lt__(self, other):
        return self.freq < other.freq


def build_tree(data: bytes) -> Node:
    freq = Counter(data)
    heap = [Node(sym, cnt) for sym, cnt in freq.items()]
    heapq.heapify(heap)
    while len(heap) > 1:
        a = heapq.heappop(heap)
        b = heapq.heappop(heap)
        heapq.heappush(heap, Node(None, a.freq + b.freq, a, b))
    return heap[0]


def build_codebook(node: Node, prefix: str = "", codes: dict | None = None) -> dict:
    if codes is None:
        codes = {}
    if node is None:
        return codes
    if node.symbol is not None:
        # Edge case: single unique symbol — assign code "0"
        codes[node.symbol] = prefix if prefix else "0"
        return codes
    build_codebook(node.left,  prefix + "0", codes)
    build_codebook(node.right, prefix + "1", codes)
    return codes


# ── Bit I/O helpers ───────────────────────────────────────────────────────────

def bits_to_bytes(bits: str) -> tuple[int, bytes]:
    """Pack a bit-string into bytes (MSB-first, zero-padded).

    Returns (original_bit_count, packed_bytes).
    """
    n = len(bits)
    pad = (-n) % 8
    bits += "0" * pad
    data = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))
    return n, data


def bytes_to_bits(data: bytes, num_bits: int) -> str:
    """Unpack bytes to a bit-string of exactly num_bits bits."""
    bits = "".join(f"{b:08b}" for b in data)
    return bits[:num_bits]


# ── Tree serialization (pre-order) ────────────────────────────────────────────

def _serialize(node: Node, out: list[str]) -> None:
    if node.symbol is not None:
        out.append("1")
        out.append(f"{node.symbol:08b}")
    else:
        out.append("0")
        _serialize(node.left,  out)
        _serialize(node.right, out)


def serialize_tree(root: Node) -> tuple[int, bytes]:
    """Serialize the tree to bytes using pre-order traversal."""
    parts: list[str] = []
    _serialize(root, parts)
    return bits_to_bytes("".join(parts))


def deserialize_tree(bits: str, pos: list[int]) -> Node:
    """Reconstruct the tree from a pre-order bit-string."""
    flag = bits[pos[0]]
    pos[0] += 1
    if flag == "1":
        sym = int(bits[pos[0]:pos[0] + 8], 2)
        pos[0] += 8
        return Node(sym, 0)
    left  = deserialize_tree(bits, pos)
    right = deserialize_tree(bits, pos)
    return Node(None, 0, left, right)


# ── Frame encode / decode ─────────────────────────────────────────────────────

def compress_frame(frame: bytes, codebook: dict) -> str:
    return "".join(codebook[b] for b in frame)


def decompress_frame(bits: str, root: Node, length: int) -> bytes:
    """Walk the tree bit-by-bit to recover `length` symbols."""
    # Edge case: single-symbol tree
    if root.symbol is not None:
        return bytes([root.symbol] * length)

    result: list[int] = []
    node = root
    for bit in bits:
        node = node.left if bit == "0" else node.right
        if node.symbol is not None:
            result.append(node.symbol)
            if len(result) == length:
                break
            node = root
    return bytes(result)


# ── Frame loading ─────────────────────────────────────────────────────────────

def load_frames(pattern: str) -> list[bytes]:
    frames = []
    for path in sorted(glob.glob(pattern)):
        img = Image.open(path).resize((FRAME_W, FRAME_H), Image.BICUBIC).convert("L")
        frames.append(bytes(img.getdata()))
    return frames


# ── Write compressed file ─────────────────────────────────────────────────────

def write_compressed(frames: list[bytes], out_path: str) -> None:
    all_data = b"".join(frames)
    root = build_tree(all_data)
    codebook = build_codebook(root)

    tree_num_bits, tree_bytes = serialize_tree(root)

    frame_payloads: list[tuple[int, bytes]] = []
    for frame in frames:
        frame_payloads.append(bits_to_bytes(compress_frame(frame, codebook)))

    with open(out_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack(">I", len(frames)))
        f.write(struct.pack(">I", tree_num_bits))
        f.write(tree_bytes)
        for num_bits, data in frame_payloads:
            f.write(struct.pack(">I", num_bits))
            f.write(data)

    raw_size  = len(all_data)
    out_size  = (
        len(MAGIC) + 4           # magic + frame count
        + 4 + len(tree_bytes)    # tree
        + sum(4 + len(d) for _, d in frame_payloads)
    )
    print(f"Wrote {len(frames)} frames → {out_path}")
    print(f"Tree:  {len(tree_bytes)} bytes ({tree_num_bits} bits)")
    print(f"Total: {raw_size} B raw → {out_size} B compressed "
          f"({100 * out_size / raw_size:.1f} %)")


# ── Read + verify ─────────────────────────────────────────────────────────────

def read_and_verify(in_path: str) -> bool:
    """Read the compressed file, decompress all frames, and verify round-trip."""
    with open(in_path, "rb") as f:
        magic = f.read(4)
        if magic != MAGIC:
            raise ValueError(f"Bad magic bytes: {magic!r}")

        num_frames = struct.unpack(">I", f.read(4))[0]

        # Reconstruct tree
        tree_num_bits  = struct.unpack(">I", f.read(4))[0]
        tree_byte_count = (tree_num_bits + 7) // 8
        tree_bytes = f.read(tree_byte_count)
        tree_bits  = bytes_to_bits(tree_bytes, tree_num_bits)
        root = deserialize_tree(tree_bits, [0])
        codebook = build_codebook(root)

        # Decompress each frame and verify round-trip
        mismatches = 0
        for i in range(num_frames):
            num_bits   = struct.unpack(">I", f.read(4))[0]
            byte_count = (num_bits + 7) // 8
            raw        = f.read(byte_count)

            stored_bits    = bytes_to_bits(raw, num_bits)
            frame          = decompress_frame(stored_bits, root, FRAME_PIXELS)
            recompressed   = compress_frame(frame, codebook)

            if recompressed != stored_bits:
                print(f"  Frame {i:5d}: round-trip MISMATCH "
                      f"(stored {num_bits} bits, re-encoded {len(recompressed)} bits)")
                mismatches += 1

    if mismatches == 0:
        print(f"All {num_frames} frames decompressed and verified ✓")
    else:
        print(f"{mismatches}/{num_frames} frames failed verification ✗")
    return mismatches == 0


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--verify":
        ok = read_and_verify(sys.argv[2])
        sys.exit(0 if ok else 1)
    elif len(sys.argv) == 3:
        frames = load_frames(sys.argv[1])
        if not frames:
            sys.exit(f"No files matched pattern: {sys.argv[1]!r}")
        write_compressed(frames, sys.argv[2])
    else:
        print(__doc__)
        sys.exit(1)
