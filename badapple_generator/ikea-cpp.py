#!/usr/bin/env python3
from PIL import Image
from itertools import batched
import glob
import sys

frames = []
i = 0

for file in sorted(glob.glob(sys.argv[1])):
  img = Image.open(file)
  out = img.resize((16, 16), Image.NEAREST)
  out = out.convert('L')

  pixels = []
  for d in out.getdata():
    pixels += [d]

  if i % 300 == 0:
    frames.append(pixels)


def pack_pixels_to_ints(frame: list[int]):
    for row in batched(frame, 8):
        bits = [pixel > 128 for pixel in row]
        bit_string = "".join("1" if bit else "0" for bit in bits)
        yield int(bit_string, base=2)

for frame in frames:
    print("\t{", ", ".join([hex(row) for row in pack_pixels_to_ints(frame)]), "},", end="\n")
