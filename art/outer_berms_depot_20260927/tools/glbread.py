"""Minimal GLB reader: accessors -> numpy, images -> bytes."""
import json, struct
import numpy as np
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
class GLB:
    def __init__(self, path):
        b = open(path, "rb").read(); self.b = b
        l = struct.unpack("<I", b[12:16])[0]
        self.j = json.loads(b[20:20 + l])
        off = 20 + l
        bl = struct.unpack("<I", b[off:off + 4])[0]
        self.bin = b[off + 8: off + 8 + bl]
    def acc(self, i):
        a = self.j["accessors"][i]; bv = self.j["bufferViews"][a["bufferView"]]
        dt = CT[a["componentType"]]; n = NC[a["type"]]
        start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = bv.get("byteStride", 0); isz = np.dtype(dt).itemsize * n
        if stride and stride != isz:
            raw = np.frombuffer(self.bin, np.uint8, count=stride * a["count"], offset=start).reshape(a["count"], stride)[:, :isz]
            arr = np.frombuffer(raw.tobytes(), dt).reshape(a["count"], n)
        else:
            arr = np.frombuffer(self.bin, dt, count=a["count"] * n, offset=start).reshape(a["count"], n)
        return arr
    def image(self, i):
        im = self.j["images"][i]; bv = self.j["bufferViews"][im["bufferView"]]
        o = bv.get("byteOffset", 0); return self.bin[o:o + bv["byteLength"]], im.get("mimeType")
