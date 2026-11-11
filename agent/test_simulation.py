"""
Unit test & Simulator for DLP Watchdog
Tests:
 1. Blocked extension detection (.fbx, .blend, .zip)
 2. Disguised file / Magic byte detection (.fbx disguised as .jpg)
 3. Safe file allowance (.txt, .png without 3D headers)
"""

import os
import sys
import time
import subprocess
import json
from dlp_watchdog import DLPWatchdog, load_config

def test_dlp_detection():
    config = load_config()
    watchdog = DLPWatchdog(config)

    test_dir = os.path.join(os.path.dirname(__file__), "test_files")
    os.makedirs(test_dir, exist_ok=True)

    fbx_file = os.path.join(test_dir, "character_model.fbx")
    blend_file = os.path.join(test_dir, "scene.blend")
    safe_txt = os.path.join(test_dir, "meeting_notes.txt")
    disguised_file = os.path.join(test_dir, "cat_photo.jpg") # actually has FBX header!

    # Create dummy files
    with open(fbx_file, "wb") as f:
        f.write(b"Kaydara FBX Binary  \x00\x1a\x00")

    with open(blend_file, "wb") as f:
        f.write(b"BLENDER_v300")

    with open(safe_txt, "w") as f:
        f.write("Hello, standard text notes.")

    with open(disguised_file, "wb") as f:
        # FBX binary header inside a file named .jpg
        f.write(b"Kaydara FBX Binary  \x00\x1a\x00dummy data")

    print("[TEST 1] Testing normal .fbx file...")
    reason = watchdog.is_violation(fbx_file)
    assert reason is not None and ".fbx" in reason, f"Expected .fbx block, got: {reason}"
    print(f" -> PASSED: {reason}")

    print("[TEST 2] Testing normal .blend file...")
    reason = watchdog.is_violation(blend_file)
    assert reason is not None and ".blend" in reason, f"Expected .blend block, got: {reason}"
    print(f" -> PASSED: {reason}")

    print("[TEST 2B] Testing Rhino .3dm file...")
    rhino_file = os.path.join(test_dir, "product_design.3dm")
    with open(rhino_file, "wb") as f:
        f.write(b"3D Model Geometry, Version 7.0")
    reason = watchdog.is_violation(rhino_file)
    assert reason is not None and ".3dm" in reason, f"Expected .3dm block, got: {reason}"
    print(f" -> PASSED: {reason}")

    print("[TEST 3] Testing safe .txt file...")
    reason = watchdog.is_violation(safe_txt)
    assert reason is None, f"Expected safe file to pass, but got: {reason}"
    print(" -> PASSED: Allowed safe file.")

    print("[TEST 4] Testing disguised file (FBX with .jpg extension)...")
    reason = watchdog.is_violation(disguised_file)
    assert reason is not None and "Kaydara FBX" in reason, f"Expected magic byte detection, got: {reason}"
    print(f" -> PASSED: Disguise thwarted! Detected: {reason}")

    print("[TEST 5] Testing incoming download in Telegram Desktop folder (must NOT be blocked)...")
    dl_zip = os.path.join(test_dir, "Telegram Desktop", "received_archive.zip")
    os.makedirs(os.path.dirname(dl_zip), exist_ok=True)
    with open(dl_zip, "wb") as f:
        f.write(b"PK\x03\x04dummy")
    reason = watchdog.is_violation(dl_zip)
    assert reason is None, f"Expected received download to be allowed, but got: {reason}"
    print(" -> PASSED: Incoming download allowed!")

    print("[TEST 6] Testing temp download part file (must NOT be blocked)...")
    part_file = os.path.join(test_dir, "incoming_character.fbx.part")
    with open(part_file, "wb") as f:
        f.write(b"Kaydara FBX Binary")
    reason = watchdog.is_violation(part_file)
    assert reason is None, f"Expected .part temp file to be allowed, but got: {reason}"
    print(" -> PASSED: Incomplete download (.part) allowed!")

    print("\n[SUCCESS] All DLP detection tests passed perfectly!\n")

    # Clean up test files
    for fp in [fbx_file, blend_file, safe_txt, disguised_file]:
        try:
            os.remove(fp)
        except Exception:
            pass
    try:
        os.rmdir(test_dir)
    except Exception:
        pass

if __name__ == "__main__":
    test_dlp_detection()

