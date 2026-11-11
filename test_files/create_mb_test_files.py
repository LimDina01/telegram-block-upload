"""
Generator for Realistic MB-Sized DLP Test Files
-----------------------------------------------
Creates realistic, multi-megabyte files to test Telegram upload blocking:
1. large_3d_character.fbx   (~35 MB) - Realistic binary FBX 3D model
2. disguised_3d_asset.png   (~25 MB) - 3D FBX binary disguised as a .png image
3. valid_highres_artwork.png (~15 MB) - Valid, real PNG image (allowed through)
4. large_archive_bundle.zip (~30 MB) - Archive bundle (blocked)
"""

import os
import struct
import zlib

TARGET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_files")
os.makedirs(TARGET_DIR, exist_ok=True)

chunk_1mb = os.urandom(1024 * 1024)

# 1. Realistic 35MB Binary FBX File
fbx_path = os.path.join(TARGET_DIR, "large_3d_character.fbx")
print(f"[*] Generating {fbx_path} (~35 MB)...")
with open(fbx_path, "wb") as f:
    # Kaydara FBX Binary header
    header = b"Kaydara FBX Binary  \x00\x1a\x00\x00\x00\x00\x00"
    f.write(header)
    # Write 35 MB of simulated vertex and mesh binary data
    for _ in range(35):
        f.write(chunk_1mb)
print(f"[+] Created: {fbx_path} ({os.path.getsize(fbx_path) / (1024*1024):.1f} MB)")

# 2. Realistic 25MB Disguised FBX (.png extension, but binary FBX)
disguised_path = os.path.join(TARGET_DIR, "disguised_3d_asset.png")
print(f"[*] Generating {disguised_path} (~25 MB)...")
with open(disguised_path, "wb") as f:
    header = b"Kaydara FBX Binary  \x00\x1a\x00\x00\x00\x00\x00"
    f.write(header)
    for _ in range(25):
        f.write(chunk_1mb)
print(f"[+] Created: {disguised_path} ({os.path.getsize(disguised_path) / (1024*1024):.1f} MB)")

# 3. Realistic 15MB Valid PNG Image (Allowed by policy)
valid_png_path = os.path.join(TARGET_DIR, "valid_highres_artwork.png")
print(f"[*] Generating {valid_png_path} (~15 MB)...")
width, height = 3000, 3000
raw_scanlines = b"\x00" + (b"\x1e\x88\xe5" * width)  # Blue color scanline
raw_data = raw_scanlines * 1200 # Multiple scanlines to create large valid compressed stream
compressed = zlib.compress(raw_data, level=1)

with open(valid_png_path, "wb") as f:
    # PNG Signature
    f.write(b"\x89PNG\r\n\x1a\n")
    # IHDR
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data)
    f.write(struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc))
    # IDAT (repeat compressed stream until ~15MB)
    target_bytes = 15 * 1024 * 1024
    written = 0
    while written < target_bytes:
        chunk = compressed[:min(len(compressed), target_bytes - written)]
        idat_crc = zlib.crc32(b"IDAT" + chunk)
        f.write(struct.pack(">I", len(chunk)) + b"IDAT" + chunk + struct.pack(">I", idat_crc))
        written += len(chunk)
    # IEND
    iend_crc = zlib.crc32(b"IEND")
    f.write(struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc))
print(f"[+] Created: {valid_png_path} ({os.path.getsize(valid_png_path) / (1024*1024):.1f} MB)")

# 4. Realistic 30MB ZIP Archive (Blocked by policy)
zip_path = os.path.join(TARGET_DIR, "large_archive_bundle.zip")
print(f"[*] Generating {zip_path} (~30 MB)...")
with open(zip_path, "wb") as f:
    # Standard ZIP Local File Header
    f.write(b"PK\x03\x04\x14\x00\x00\x00\x00\x00\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0a\x00\x00\x00assets.dat")
    for _ in range(30):
        f.write(chunk_1mb)
print(f"[+] Created: {zip_path} ({os.path.getsize(zip_path) / (1024*1024):.1f} MB)")

print("\n[SUCCESS] All MB-sized test files generated successfully!")
