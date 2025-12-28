#!/usr/bin/env python3
from PIL import Image
import socket
import glob
import time
import sys

IP = "192.168.77.253"

print(sys.argv[1])
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

for file in sorted(glob.glob(sys.argv[1]))[::]:
  print(file)
  img = Image.open(file)
  # out = img.resize((16, 16), Image.LANCZOS)
  # out = img.resize((16, 16), Image.NEAREST)
  out = img.resize((16, 16), Image.BILINEAR)
  # out = img.resize((16, 16), Image.BICUBIC)
  out = out.convert('L')
  out = out.rotate(-90)
  # out.show()

  pixels = bytearray()
  for d in out.getdata():
    # print(d)
    pixels += bytearray([d, d, d])

  # print("len", len(pixels))
  header = bytearray([0x41, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
  packet = header + pixels

  sock.sendto(packet, (IP, 4048))
  time.sleep(0.03)

sock.close()

