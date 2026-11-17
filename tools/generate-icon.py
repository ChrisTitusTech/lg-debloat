#!/usr/bin/env python3
"""Build a small original geometric Home icon without copying vendor artwork."""
from pathlib import Path
import struct
import zlib

size = 80
rows = []
for y in range(size):
    row = bytearray([0])  # PNG filter: none
    for x in range(size):
        roof = 18 <= y <= 42 and abs(x - 40) <= y - 17
        house = 24 <= x <= 56 and 38 <= y <= 64
        door = 36 <= x <= 44 and 49 <= y <= 64
        row.extend((235, 241, 245) if (roof or house) and not door else (20, 30, 40))
    rows.append(bytes(row))
def chunk(kind, data):
    return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
image = b'\x89PNG\r\n\x1a\n'
image += chunk(b'IHDR', struct.pack('!2I5B', size, size, 8, 2, 0, 0, 0))
image += chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b'')
(Path(__file__).resolve().parents[1] / 'app/icon.png').write_bytes(image)
print('Created original Home icon (no metadata).')
