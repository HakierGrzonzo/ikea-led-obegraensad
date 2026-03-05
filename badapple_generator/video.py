#!/usr/bin/env python3

import vlc
from PIL import Image
import socket
import glob
import time

from tqdm import tqdm

domain = "thisdisplay.website"
IP = socket.gethostbyname(domain)
max_frames = len(glob.glob("frames/*.jpg"))


def display_frame(frame_number):
    if frame_number > max_frames or frame_number <= 0:
        return

    file_path = f"frames\\output_{frame_number:04}.jpg"
    print(file_path)

    img = Image.open(file_path)
    out = img

    out = out.resize((32, 32), Image.BICUBIC)

    # out = out.resize((16, 16), Image.LANCZOS)
    # out = out.resize((16, 16), Image.NEAREST)
    # out = out.resize((16, 16), Image.BILINEAR)
    out = out.resize((16, 16), Image.NEAREST)
    out = out.convert('L')
    # out = out.rotate(-90)

    pixels = bytearray()
    for d in out.getdata():
        pixels += bytearray([d, d, d])

    # print("len", len(pixels))
    header = bytearray([0x41, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    packet = header + pixels

    sock.sendto(packet, (IP, 4048))


def main():
    VIDEO_PATH = "bad_apple.webm"
    FPS = 30
    time_start = None
    last_frame = None
    t = tqdm(total=max_frames, position=1)

    instance = vlc.Instance()
    player = instance.media_player_new()
    media = instance.media_new(VIDEO_PATH)
    player.set_media(media)
    player.play()

    while True:
        state = player.get_state()
        if state in (vlc.State.Ended, vlc.State.Error):
            break

        if state == vlc.State.Playing and time_start is None:
            print("Synchronizing...")
            player.pause()
            time.sleep(1)
            player.play()
            time_start = time.time()
            print("Running")

        if time_start:
            current_time_ms = time.time() - time_start
            # print(f"Current time: {current_time_ms}")
            frame_number = int(current_time_ms * FPS)
            if frame_number != last_frame:
                last_frame = frame_number
                # print(frame_number)
                print(f"Current time: {current_time_ms:.5f}", end=" ")
                display_frame(frame_number + 1)
                t.update()


        time.sleep(0.01)  # Prevent tight loop

    t.close()


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
main()
sock.close()