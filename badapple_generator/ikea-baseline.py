#!/usr/bin/env python3
from PIL import Image
import glob
import sys

frames = []

for file in sorted(glob.glob(sys.argv[1])):
  img = Image.open(file)
  out = img.resize((16, 16), Image.BICUBIC)
  out = out.convert('L')

  pixels = []
  for d in out.getdata():
    pixels += [d]

  frames.append(pixels)


with open("badApple.bin", "wb") as f:
   for frame in frames:
      f.write(bytes(frame))
