"""
Compression engine — no GUI dependencies.
Algorithms: Huffman Coding, RLE, LZW
"""

import os
import io
import time
import math
import struct
import heapq
import json
import collections
from datetime import datetime

APP_VERSION   = "1.0.0"
MAGIC_HEADER  = b"FUDMC"
COMPRESSED_EXT = ".fudmc"


# ── Huffman ───────────────────────────────────────────────────────────────────
class HuffmanNode:
    def __init__(self, byte, freq):
        self.byte  = byte
        self.freq  = freq
        self.left  = None
        self.right = None
    def __lt__(self, other):
        return self.freq < other.freq


class HuffmanCodec:
    ALGO_ID = 0x01

    @staticmethod
    def compress(data: bytes) -> bytes:
        if not data:
            return b""
        freq = collections.Counter(data)
        if len(freq) == 1:
            byte  = list(freq.keys())[0]
            count = freq[byte]
            return struct.pack(">BBI", 0xFF, byte, count)

        heap = [HuffmanNode(b, f) for b, f in freq.items()]
        heapq.heapify(heap)
        while len(heap) > 1:
            left  = heapq.heappop(heap)
            right = heapq.heappop(heap)
            merged = HuffmanNode(None, left.freq + right.freq)
            merged.left, merged.right = left, right
            heapq.heappush(heap, merged)

        codes = {}
        HuffmanCodec._build_codes(heap[0], "", codes)

        bit_str = "".join(codes[b] for b in data)
        padding = (8 - len(bit_str) % 8) % 8
        bit_str += "0" * padding

        encoded = bytearray(int(bit_str[i:i+8], 2) for i in range(0, len(bit_str), 8))
        codebook = json.dumps({str(k): v for k, v in codes.items()}).encode()
        return struct.pack(">I", len(codebook)) + codebook + struct.pack("B", padding) + bytes(encoded)

    @staticmethod
    def _build_codes(node, prefix, codes):
        if node is None:
            return
        if node.byte is not None:
            codes[node.byte] = prefix or "0"
            return
        HuffmanCodec._build_codes(node.left,  prefix + "0", codes)
        HuffmanCodec._build_codes(node.right, prefix + "1", codes)

    @staticmethod
    def decompress(data: bytes) -> bytes:
        if not data:
            return b""
        if data[0] == 0xFF and len(data) == 6:
            return bytes([data[1]] * struct.unpack(">I", data[2:6])[0])

        offset = 0
        cb_len  = struct.unpack(">I", data[offset:offset+4])[0]; offset += 4
        codes   = {int(k): v for k, v in json.loads(data[offset:offset+cb_len]).items()}; offset += cb_len
        padding = data[offset]; offset += 1
        bit_str = "".join(f"{b:08b}" for b in data[offset:])
        if padding:
            bit_str = bit_str[:-padding]

        reverse = {v: k for k, v in codes.items()}
        result, cur = bytearray(), ""
        for bit in bit_str:
            cur += bit
            if cur in reverse:
                result.append(reverse[cur])
                cur = ""
        return bytes(result)


# ── RLE ───────────────────────────────────────────────────────────────────────
class RLECodec:
    ALGO_ID = 0x02

    @staticmethod
    def compress(data: bytes) -> bytes:
        if not data:
            return b""
        out, i, n = bytearray(), 0, len(data)
        while i < n:
            run = 1
            while i + run < n and data[i + run] == data[i] and run < 255:
                run += 1
            out.append(run); out.append(data[i])
            i += run
        return bytes(out)

    @staticmethod
    def decompress(data: bytes) -> bytes:
        if not data:
            return b""
        out = bytearray()
        for i in range(0, len(data) - 1, 2):
            out.extend([data[i + 1]] * data[i])
        return bytes(out)


# ── LZW ───────────────────────────────────────────────────────────────────────
class LZWCodec:
    ALGO_ID = 0x03
    MAX_DICT = 4096

    @staticmethod
    def compress(data: bytes) -> bytes:
        if not data:
            return b""
        dictionary = {bytes([i]): i for i in range(256)}
        next_code, codes, w = 256, [], bytes([data[0]])
        for byte in data[1:]:
            c = bytes([byte])
            wc = w + c
            if wc in dictionary:
                w = wc
            else:
                codes.append(dictionary[w])
                if next_code < LZWCodec.MAX_DICT:
                    dictionary[wc] = next_code; next_code += 1
                w = c
        codes.append(dictionary[w])

        out, buf, bits = bytearray(), 0, 0
        for code in codes:
            buf = (buf << 12) | code; bits += 12
            while bits >= 8:
                bits -= 8; out.append((buf >> bits) & 0xFF)
        if bits:
            out.append((buf << (8 - bits)) & 0xFF)
        return struct.pack(">I", len(codes)) + bytes(out)

    @staticmethod
    def decompress(data: bytes) -> bytes:
        if not data:
            return b""
        code_count = struct.unpack(">I", data[:4])[0]
        codes, buf, bits = [], 0, 0
        for byte in data[4:]:
            buf = (buf << 8) | byte; bits += 8
            while bits >= 12 and len(codes) < code_count:
                bits -= 12; codes.append((buf >> bits) & 0xFFF)
        if not codes:
            return b""

        dictionary = {i: bytes([i]) for i in range(256)}
        next_code  = 256
        result = bytearray()
        w = dictionary[codes[0]]; result.extend(w)
        for code in codes[1:]:
            if code in dictionary:
                entry = dictionary[code]
            elif code == next_code:
                entry = w + bytes([w[0]])
            else:
                raise ValueError(f"Bad LZW code: {code}")
            result.extend(entry)
            if next_code < LZWCodec.MAX_DICT:
                dictionary[next_code] = w + bytes([entry[0]]); next_code += 1
            w = entry
        return bytes(result)


# ── Registry ──────────────────────────────────────────────────────────────────
ALGO_MAP = {
    "Huffman Coding":            HuffmanCodec,
    "Run-Length Encoding (RLE)": RLECodec,
    "Lempel-Ziv-Welch (LZW)":   LZWCodec,
}
CODEC_BY_ID = {c.ALGO_ID: c for c in ALGO_MAP.values()}


def _choose_best(data: bytes) -> str:
    sample = data[:65536]
    best_algo, best_score = "Huffman Coding", 0.0
    for name, codec in ALGO_MAP.items():
        try:
            t0 = time.perf_counter()
            c  = codec.compress(sample)
            elapsed = time.perf_counter() - t0
            score = (len(sample) / max(len(c), 1)) * 0.7 + (1 / max(elapsed, 1e-4)) * 3e-5
            if score > best_score:
                best_score, best_algo = score, name
        except Exception:
            pass
    return best_algo


# ── Engine ────────────────────────────────────────────────────────────────────
class CompressionEngine:

    @staticmethod
    def compress_bytes(raw: bytes, algo_name: str, progress_cb=None) -> tuple:
        """Returns (compressed_bytes, metrics_dict)."""
        if algo_name == "Auto (Best Fit)":
            if progress_cb: progress_cb(20, "Selecting best algorithm…")
            algo_name = _choose_best(raw)

        codec = ALGO_MAP[algo_name]
        if progress_cb: progress_cb(40, f"Compressing with {algo_name}…")

        t0      = time.perf_counter()
        payload = codec.compress(raw)
        elapsed = time.perf_counter() - t0

        # Frame: MAGIC | version(1) | algo_id(1) | orig_size(8) | fname_len(2) | fname | payload
        # fname is empty string when compressing from bytes (web upload)
        fname_bytes = b""
        header = (MAGIC_HEADER + struct.pack("B", 1) + struct.pack("B", codec.ALGO_ID)
                  + struct.pack(">Q", len(raw)) + struct.pack(">H", len(fname_bytes)) + fname_bytes)
        compressed = header + payload

        orig, comp = len(raw), len(compressed)
        return compressed, {
            "algorithm":       algo_name,
            "original_size":   orig,
            "compressed_size": comp,
            "ratio":           orig / max(comp, 1),
            "saving_pct":      max(0, (1 - comp / max(orig, 1)) * 100),
            "compress_time":   elapsed,
            "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    @staticmethod
    def decompress_bytes(raw: bytes, progress_cb=None) -> tuple:
        """Returns (decompressed_bytes, metrics_dict)."""
        if not raw.startswith(MAGIC_HEADER):
            raise ValueError("Not a valid FUDMC file. Please upload a .fudmc file.")

        offset  = len(MAGIC_HEADER)
        version = raw[offset]; offset += 1
        if version != 1:
            raise ValueError(f"Unsupported file version: {version}")
        algo_id = raw[offset]; offset += 1
        orig_sz = struct.unpack(">Q", raw[offset:offset+8])[0]; offset += 8
        fn_len  = struct.unpack(">H", raw[offset:offset+2])[0]; offset += 2
        orig_filename = raw[offset:offset+fn_len].decode("utf-8"); offset += fn_len
        payload = raw[offset:]

        codec = CODEC_BY_ID.get(algo_id)
        if not codec:
            raise ValueError(f"Unknown algorithm ID: {algo_id:#04x}")

        algo_name = {v.ALGO_ID: k for k, v in ALGO_MAP.items()}.get(algo_id, "Unknown")
        if progress_cb: progress_cb(40, f"Decompressing with {algo_name}…")

        t0   = time.perf_counter()
        data = codec.decompress(payload)
        elapsed = time.perf_counter() - t0

        comp = len(raw)
        return data, orig_filename, {
            "algorithm":        algo_name,
            "original_size":    orig_sz,
            "compressed_size":  comp,
            "ratio":            orig_sz / max(comp, 1),
            "decompress_time":  elapsed,
            "timestamp":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


# ── Utilities ─────────────────────────────────────────────────────────────────
def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def entropy_bits(data: bytes) -> float:
    if not data:
        return 0.0
    freq  = collections.Counter(data)
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in freq.values())
