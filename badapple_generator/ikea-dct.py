#!/usr/bin/env python3
from typing import Generator, Iterable
from PIL import Image
from itertools import batched
import glob
from math import cos, pi, sqrt
import sys

frames = []

SIZE = 16

for file in sorted(glob.glob(sys.argv[1])):
  img = Image.open(file)
  out = img.resize((SIZE, SIZE), Image.BICUBIC)
  out = out.convert('L')

  pixels = []
  for d in out.getdata():
    pixels += [d]

  frames.append(pixels)


class DCTJPEG:
    sqrt_of_two_by_two = sqrt(2) / 2
    block_size = 8

    quants = [
        16, 11, 10, 16, 24,  40,   51,   61,
        12, 12, 14, 19, 26,  58,   60,   55,
        14, 13, 16, 24, 40,  57,   69,   56,
        14, 17, 22, 29, 51,  87,   80,   62,
        18, 22, 37, 56, 68,  109,  103,  77,
        24, 35, 55, 64, 81,  104,  113,  92,
        49, 64, 78, 87, 103, 121,  120,  101,
        72, 92, 95, 98, 112, 100,  103,  99
    ]

    @classmethod
    def get_block_coord(cls, x: int, y: int):
        return y * cls.block_size + x

    @classmethod
    def alpha(cls, z: int):
        if z == 0:
            return cls.sqrt_of_two_by_two
        else:
            return 1

    @classmethod
    def _calculate_dct_for_uv(cls, block: list[int], u: int, v: int):
        static = (1/4) * cls.alpha(u) * cls.alpha(v)

        summed_values = 0
        for y in range(cls.block_size):
            for x in range(cls.block_size):
                pixel = block[cls.get_block_coord(x, y)] - 127
                first_term = cos(((2 * x + 1) * u * pi) / 16)
                second_term = cos(((2 * y + 1) * v * pi) / 16)

                summed_values += pixel * first_term * second_term

        return static * summed_values

    @classmethod
    def get_dct_for_block(cls, block: list[int]):
        for u in range(cls.block_size):
            for v in range(cls.block_size):
                yield cls._calculate_dct_for_uv(block, u, v)

    @classmethod
    def quantize_block(cls, block: Iterable[float]):
        for value, quant in zip(block, cls.quants):
            yield round(value / quant)

    @classmethod
    def iter_block(cls, frame: list[int], x_offset: int, y_offset: int):
        for y in range(cls.block_size):
            for x in range(cls.block_size):
                x_with_offset = x + x_offset
                y_with_offset = y + y_offset
                index = x_with_offset + y_with_offset * SIZE
                yield frame[index]


    @classmethod
    def iter_blocks(cls, frame: list[int]):
        for y_offset in range(0, SIZE, cls.block_size):
            for x_offset in range(0, SIZE, cls.block_size):
                yield list(cls.iter_block(frame, x_offset, y_offset))

    @classmethod
    def get_snake_indexes(cls):
        is_going_up = True 
        x = 0
        y = 0
        while True:
            yield cls.get_block_coord(x, y)
            if (x, y) == (7, 7):
                break
            if (is_going_up is True and y == 0) or (is_going_up is False and y == 7):
                x += 1 # go one space left
                is_going_up = not is_going_up
                continue
            if (is_going_up is False and x == 0) or (is_going_up is True and x == 7):
                y += 1 # go one space down
                is_going_up = not is_going_up
                continue
            if is_going_up:
                x += 1
                y -= 1
            else:
                x -= 1
                y += 1



"""
for block in DCTJPEG.iter_blocks(frames[0]):
    print("\nBlock:")
    for pixel in batched(block, DCTJPEG.block_size):
        print("".join(" " if p > 128 else "X" for p in pixel))
    
    print("\nDCT:")

    dct = DCTJPEG.get_dct_for_block(block)
    for line in batched(dct, DCTJPEG.block_size):
        print(*[round(n) for n in line], sep="\t")

    print("\nquant:")

    dct = DCTJPEG.get_dct_for_block(block)
    for line in batched(DCTJPEG.quantize_block(dct), DCTJPEG.block_size):
        print(*[round(n) for n in line], sep="\t")
"""


assert 64 == len(list(DCTJPEG.get_snake_indexes()))


with open("badApple-dct.bin", "wb") as f:
   for frame in frames:
       for block in DCTJPEG.iter_blocks(frame):
           dct = DCTJPEG.get_dct_for_block(block)
           quantized = [value for value in DCTJPEG.quantize_block(dct)]
           #reordered = [quantized[index] for index in DCTJPEG.get_snake_indexes()]
           adjusted = [value + 128 for value in quantized]
           f.write(bytes(adjusted))
           """
           try:
               zero_start_index = min(test_index for test_index in range(len(reordered)) if all(v == 0 for v in reordered[test_index:]))
               print(zero_start_index, [hex(v) for v in adjusted[:zero_start_index]])
               f.write(bytes(zero_start_index))
               f.write(bytes(adjusted[:zero_start_index]))
           except ValueError:
               # Last index is not zero
               f.write(bytes(len(reordered)))
               f.write(bytes(adjusted))
           """

