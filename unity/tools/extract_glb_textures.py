#!/usr/bin/env python3
"""Extract the first material's embedded PBR atlases from a binary glTF file."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("glb", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    data = args.glb.read_bytes()
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise SystemExit("Input is not a valid glTF 2.0 binary.")

    chunks: dict[bytes, bytes] = {}
    offset = 12
    while offset < len(data):
        length, kind = struct.unpack_from("<I4s", data, offset)
        offset += 8
        chunks[kind] = data[offset : offset + length]
        offset += length
    document = json.loads(chunks[b"JSON"].decode("utf-8").rstrip("\x00 "))
    binary = chunks[b"BIN\x00"]
    material = document["materials"][0]

    requests = {
        "Albedo": material["pbrMetallicRoughness"]["baseColorTexture"]["index"],
        "Normal": material["normalTexture"]["index"],
        "MetallicRoughness": material["pbrMetallicRoughness"]["metallicRoughnessTexture"]["index"],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    created = []
    for name, texture_index in requests.items():
        image_index = document["textures"][texture_index]["source"]
        image = document["images"][image_index]
        view = document["bufferViews"][image["bufferView"]]
        start = view.get("byteOffset", 0)
        payload = binary[start : start + view["byteLength"]]
        extension = { "image/jpeg": ".jpg", "image/png": ".png" }.get(image["mimeType"])
        if not extension:
            raise SystemExit(f"Unsupported embedded texture type: {image['mimeType']}")
        destination = args.output / f"{name}{extension}"
        if destination.exists():
            raise SystemExit(f"Refusing to overwrite: {destination}")
        destination.write_bytes(payload)
        created.append(destination)
    for path in created:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

