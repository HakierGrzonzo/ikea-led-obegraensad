  #!/usr/bin/env python3
from PIL import Image
import socket
import glob
import time
import json
import sys

print(sys.argv[1])

frames = []
i = 0

for file in sorted(glob.glob(sys.argv[1])):
  img = Image.open(file)
  # out = img.resize((16, 16), Image.LANCZOS)
  out = img.resize((16, 16), Image.NEAREST)
  # out = img.resize((16, 16), Image.BILINEAR)
  # out = img.resize((16, 16), Image.BICUBIC)
  out = out.convert('L')
  # out = out.rotate(90)
  # out.show()

  pixels = []
  for d in out.getdata():
    # print(d)
    pixels += [d]

  # print("len", len(pixels))
  # header = bytearray([0x41, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
  # packet = header + pixels
  # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  # sock.sendto(packet, ("151.219.193.66", 4048))
  # sock.close()
  if i % 300 == 0:
    frames.append(pixels)

  # print(pixels)
  # time.sleep(1)
  # break
  i += 1
print("frames", len(frames))
j = {"version":1, "frames":frames}
# print(json.dumps(j))
with open('dump.json', 'w') as f:
  json.dump(j, f)