#!/usr/bin/env python3
"""Convert a .huf file to a C++ byte-array header.

Usage:
    python huf_to_header.py <input.huf> <output.h>

The output can be included directly into a uint8_t array initialiser:

    static const uint8_t huf_data[] = {
    #include "badApple.h"
    };
"""

import sys

BYTES_PER_LINE = 16


def convert(in_path: str, out_path: str) -> None:
    with open(in_path, "rb") as f:
        data = f.read()

    lines = []
    for i in range(0, len(data), BYTES_PER_LINE):
        chunk = data[i : i + BYTES_PER_LINE]
        lines.append(", ".join(f"0x{b:02x}" for b in chunk) + ",")

    with open(out_path, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Wrote {len(data)} bytes → {out_path} ({len(lines)} lines)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
