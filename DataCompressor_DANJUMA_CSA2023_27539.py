"""
=============================================================================
  GUI-DRIVEN DATA COMPRESSION WITH OPTIMIZED ENCODING ALGORITHMS
  AND CROSS-PLATFORM ARCHITECTURE
=============================================================================
  Student  : DANJUMA JOSHUA AUDU
  MatNo    : CSA/2023/27539
  Dept     : Computer Science & Information Technology
  Faculty  : Faculty of Computing
  Univ     : Federal University Dutsin-Ma, Katsina State, Nigeria
  Supervisor: Mr. STEPHEN LUKA
  Year     : 2025 / 2026
=============================================================================
  Algorithms Implemented (from scratch):
    1. Huffman Coding     — variable-length entropy encoding
    2. Run-Length Encoding (RLE) — sequential repeat compression
    3. Lempel-Ziv-Welch (LZW)   — dictionary-based compression
=============================================================================
  Supported File Types:
    - Text  (.txt, .csv, .log, .py, .html, .xml, .json)
    - Image (.bmp  — lossless raw bitmap)
    - Audio (.wav  — PCM lossless audio)
    - Any binary file (uses best-fit algorithm selection)
=============================================================================
  HOW TO RUN:
    python DataCompressor_DANJUMA_CSA2023_27539.py
  
  REQUIREMENTS:
    Python 3.8+  (no third-party packages needed — stdlib only)
=============================================================================
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
import os
import io
import time
import math
import struct
import heapq
import json
import threading
import collections
import sys
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
#  COLOUR PALETTE & THEME
# ─────────────────────────────────────────────────────────────────────────────
COLORS = {
    "bg_dark":      "#0D1117",
    "bg_panel":     "#161B22",
    "bg_card":      "#1C2330",
    "bg_input":     "#21262D",
    "accent":       "#00D084",
    "accent_dim":   "#00A366",
    "accent_glow":  "#00FF9F",
    "blue":         "#58A6FF",
    "orange":       "#F0883E",
    "red":          "#F85149",
    "yellow":       "#E3B341",
    "text_primary": "#E6EDF3",
    "text_sec":     "#8B949E",
    "text_muted":   "#484F58",
    "border":       "#30363D",
    "border_bright":"#58A6FF",
    "white":        "#FFFFFF",
}

ALGO_COLORS = {
    "Huffman Coding": COLORS["accent"],
    "Run-Length Encoding (RLE)": COLORS["blue"],
    "Lempel-Ziv-Welch (LZW)": COLORS["orange"],
    "Auto (Best Fit)": COLORS["yellow"],
}

APP_VERSION = "1.0.0"
MAGIC_HEADER = b"FUDMC"   # Federal University Dutsin-Ma Compressor


# ─────────────────────────────────────────────────────────────────────────────
#  HUFFMAN CODING  (lossless, entropy-based)
# ─────────────────────────────────────────────────────────────────────────────
class HuffmanNode:
    def __init__(self, byte, freq):
        self.byte  = byte
        self.freq  = freq
        self.left  = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq


class HuffmanCodec:
    """Pure-Python Huffman Coding — compresses and decompresses bytes."""

    ALGO_ID = 0x01

    # ── compress ──────────────────────────────────────────────────────────
    @staticmethod
    def compress(data: bytes) -> bytes:
        if not data:
            return b""

        freq = collections.Counter(data)

        # Edge case: only one unique byte
        if len(freq) == 1:
            byte = list(freq.keys())[0]
            count = freq[byte]
            # Store: algo_id(1) + symbol(1) + count(8) + sentinel
            return struct.pack(">BBI", 0xFF, byte, count)

        heap = [HuffmanNode(b, f) for b, f in freq.items()]
        heapq.heapify(heap)

        while len(heap) > 1:
            left  = heapq.heappop(heap)
            right = heapq.heappop(heap)
            merged = HuffmanNode(None, left.freq + right.freq)
            merged.left  = left
            merged.right = right
            heapq.heappush(heap, merged)

        root = heap[0]
        codes = {}
        HuffmanCodec._build_codes(root, "", codes)

        # Encode data to bit-string
        bit_str = "".join(codes[b] for b in data)
        # Pad to multiple of 8
        padding = (8 - len(bit_str) % 8) % 8
        bit_str += "0" * padding

        # Convert bit-string to bytes
        encoded_bytes = bytearray()
        for i in range(0, len(bit_str), 8):
            encoded_bytes.append(int(bit_str[i:i+8], 2))

        # Serialise the codebook
        codebook_json = json.dumps(
            {str(k): v for k, v in codes.items()}
        ).encode("utf-8")

        # Frame: [codebook_len(4)][codebook][padding(1)][encoded_bytes]
        frame = (
            struct.pack(">I", len(codebook_json)) +
            codebook_json +
            struct.pack("B", padding) +
            bytes(encoded_bytes)
        )
        return frame

    @staticmethod
    def _build_codes(node, prefix, codes):
        if node is None:
            return
        if node.byte is not None:
            codes[node.byte] = prefix if prefix else "0"
            return
        HuffmanCodec._build_codes(node.left,  prefix + "0", codes)
        HuffmanCodec._build_codes(node.right, prefix + "1", codes)

    # ── decompress ────────────────────────────────────────────────────────
    @staticmethod
    def decompress(data: bytes) -> bytes:
        if not data:
            return b""

        # Edge-case single-byte encoding
        if data[0] == 0xFF and len(data) == 6:
            byte  = data[1]
            count = struct.unpack(">I", data[2:6])[0]
            return bytes([byte] * count)

        offset = 0
        codebook_len = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4

        codebook_json = data[offset:offset+codebook_len].decode("utf-8")
        offset += codebook_len
        codes = {int(k): v for k, v in json.loads(codebook_json).items()}

        padding = data[offset]
        offset += 1

        encoded_bytes = data[offset:]

        # Rebuild reverse mapping
        reverse = {v: k for k, v in codes.items()}

        # Convert bytes → bit-string, strip padding
        bit_str = "".join(f"{byte:08b}" for byte in encoded_bytes)
        if padding:
            bit_str = bit_str[:-padding]

        # Decode
        result = bytearray()
        current = ""
        for bit in bit_str:
            current += bit
            if current in reverse:
                result.append(reverse[current])
                current = ""

        return bytes(result)


# ─────────────────────────────────────────────────────────────────────────────
#  RUN-LENGTH ENCODING  (lossless, sequential)
# ─────────────────────────────────────────────────────────────────────────────
class RLECodec:
    """Run-Length Encoding — works on any byte sequence."""

    ALGO_ID = 0x02

    @staticmethod
    def compress(data: bytes) -> bytes:
        if not data:
            return b""
        out = bytearray()
        i = 0
        n = len(data)
        while i < n:
            current = data[i]
            run = 1
            while i + run < n and data[i + run] == current and run < 255:
                run += 1
            out.append(run)
            out.append(current)
            i += run
        return bytes(out)

    @staticmethod
    def decompress(data: bytes) -> bytes:
        if not data:
            return b""
        out = bytearray()
        i = 0
        while i < len(data) - 1:
            count = data[i]
            byte  = data[i + 1]
            out.extend([byte] * count)
            i += 2
        return bytes(out)


# ─────────────────────────────────────────────────────────────────────────────
#  LEMPEL-ZIV-WELCH  (lossless, dictionary-based)
# ─────────────────────────────────────────────────────────────────────────────
class LZWCodec:
    """LZW — dictionary compression (byte-level, 12-bit codes)."""

    ALGO_ID = 0x03
    MAX_DICT = 4096   # 12-bit codes

    @staticmethod
    def compress(data: bytes) -> bytes:
        if not data:
            return b""

        # Initialise dictionary with all single bytes
        dictionary = {bytes([i]): i for i in range(256)}
        next_code  = 256

        codes = []
        w = bytes([data[0]])

        for i in range(1, len(data)):
            c  = bytes([data[i]])
            wc = w + c
            if wc in dictionary:
                w = wc
            else:
                codes.append(dictionary[w])
                if next_code < LZWCodec.MAX_DICT:
                    dictionary[wc] = next_code
                    next_code += 1
                w = c

        codes.append(dictionary[w])

        # Pack 12-bit codes into bytes
        out   = bytearray()
        buf   = 0
        bits  = 0
        for code in codes:
            buf   = (buf << 12) | code
            bits += 12
            while bits >= 8:
                bits -= 8
                out.append((buf >> bits) & 0xFF)

        if bits:
            out.append((buf << (8 - bits)) & 0xFF)

        # Prepend code count (4 bytes) so decompressor knows exact length
        return struct.pack(">I", len(codes)) + bytes(out)

    @staticmethod
    def decompress(data: bytes) -> bytes:
        if not data:
            return b""

        code_count = struct.unpack(">I", data[:4])[0]
        packed     = data[4:]

        # Unpack 12-bit codes
        codes = []
        buf   = 0
        bits  = 0
        for byte in packed:
            buf   = (buf << 8) | byte
            bits += 8
            while bits >= 12 and len(codes) < code_count:
                bits  -= 12
                codes.append((buf >> bits) & 0xFFF)

        if not codes:
            return b""

        dictionary  = {i: bytes([i]) for i in range(256)}
        next_code   = 256

        result = bytearray()
        w      = dictionary[codes[0]]
        result.extend(w)

        for code in codes[1:]:
            if code in dictionary:
                entry = dictionary[code]
            elif code == next_code:
                entry = w + bytes([w[0]])
            else:
                raise ValueError(f"Bad LZW code: {code}")

            result.extend(entry)

            if next_code < LZWCodec.MAX_DICT:
                dictionary[next_code] = w + bytes([entry[0]])
                next_code += 1

            w = entry

        return bytes(result)


# ─────────────────────────────────────────────────────────────────────────────
#  COMPRESSION ENGINE  (wraps all codecs + file framing)
# ─────────────────────────────────────────────────────────────────────────────
ALGO_MAP = {
    "Huffman Coding":             HuffmanCodec,
    "Run-Length Encoding (RLE)":  RLECodec,
    "Lempel-Ziv-Welch (LZW)":    LZWCodec,
}

CODEC_BY_ID = {
    HuffmanCodec.ALGO_ID: HuffmanCodec,
    RLECodec.ALGO_ID:     RLECodec,
    LZWCodec.ALGO_ID:     LZWCodec,
}

COMPRESSED_EXT = ".fudmc"

def _choose_best(data: bytes) -> str:
    """Try all three on a sample and return fastest/best-ratio algorithm."""
    sample = data[:min(len(data), 65536)]   # 64 KB sample
    best_algo  = "Huffman Coding"
    best_ratio = 0.0

    for name, codec in ALGO_MAP.items():
        try:
            t0 = time.perf_counter()
            compressed = codec.compress(sample)
            elapsed    = time.perf_counter() - t0
            if len(sample) > 0:
                ratio = len(sample) / max(len(compressed), 1)
                # Score balances ratio vs speed (weight: 70 / 30)
                score = ratio * 0.7 + (1 / max(elapsed, 0.0001)) * 0.0001 * 0.3
                if score > best_ratio:
                    best_ratio = score
                    best_algo  = name
        except Exception:
            pass

    return best_algo


class CompressionEngine:

    @staticmethod
    def compress_file(src_path: str, dst_path: str, algo_name: str,
                      progress_cb=None) -> dict:
        """
        Compress src_path → dst_path.
        Returns metrics dict.
        """
        with open(src_path, "rb") as f:
            raw = f.read()

        original_size = len(raw)
        if progress_cb:
            progress_cb(10, "Reading file…")

        if algo_name == "Auto (Best Fit)":
            if progress_cb:
                progress_cb(20, "Selecting best algorithm…")
            algo_name = _choose_best(raw)

        codec = ALGO_MAP[algo_name]
        algo_id = codec.ALGO_ID

        if progress_cb:
            progress_cb(35, f"Compressing with {algo_name}…")

        t_start = time.perf_counter()
        payload = codec.compress(raw)
        t_end   = time.perf_counter()

        compress_time = t_end - t_start

        if progress_cb:
            progress_cb(80, "Writing output file…")

        # File frame:
        # MAGIC(5) | VERSION(1) | ALGO_ID(1) | ORIG_SIZE(8) | FILENAME_LEN(2)
        # | FILENAME | PAYLOAD
        filename_bytes = os.path.basename(src_path).encode("utf-8")
        header = (
            MAGIC_HEADER +
            struct.pack("B", 1) +               # version 1
            struct.pack("B", algo_id) +
            struct.pack(">Q", original_size) +
            struct.pack(">H", len(filename_bytes)) +
            filename_bytes
        )

        with open(dst_path, "wb") as f:
            f.write(header + payload)

        compressed_size = os.path.getsize(dst_path)

        if progress_cb:
            progress_cb(100, "Done.")

        ratio = original_size / max(compressed_size, 1)
        saving_pct = max(0, (1 - compressed_size / max(original_size, 1)) * 100)

        return {
            "algorithm":       algo_name,
            "original_size":   original_size,
            "compressed_size": compressed_size,
            "ratio":           ratio,
            "saving_pct":      saving_pct,
            "compress_time":   compress_time,
            "src_path":        src_path,
            "dst_path":        dst_path,
            "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    @staticmethod
    def decompress_file(src_path: str, dst_dir: str,
                        progress_cb=None) -> dict:
        """
        Decompress src_path → dst_dir / original_filename.
        Returns metrics dict.
        """
        with open(src_path, "rb") as f:
            raw = f.read()

        if not raw.startswith(MAGIC_HEADER):
            raise ValueError(
                "Not a valid FUDMC compressed file.\n"
                "Please select a file with the .fudmc extension."
            )

        if progress_cb:
            progress_cb(15, "Reading compressed file…")

        offset = len(MAGIC_HEADER)
        version  = raw[offset];       offset += 1
        if version != 1:
            raise ValueError(f"Unsupported file version: {version}")
        algo_id  = raw[offset];       offset += 1
        orig_sz  = struct.unpack(">Q", raw[offset:offset+8])[0];  offset += 8
        fn_len   = struct.unpack(">H", raw[offset:offset+2])[0];  offset += 2
        filename = raw[offset:offset+fn_len].decode("utf-8");     offset += fn_len

        payload  = raw[offset:]
        compressed_size = len(raw)

        codec = CODEC_BY_ID.get(algo_id)
        if not codec:
            raise ValueError(f"Unknown algorithm ID: {algo_id:#04x}")

        algo_name = {v: k for k, v in
                     {n: c.ALGO_ID for n, c in ALGO_MAP.items()}
                     }.get(algo_id, "Unknown")

        if progress_cb:
            progress_cb(40, f"Decompressing with {algo_name}…")

        t_start = time.perf_counter()
        data    = codec.decompress(payload)
        t_end   = time.perf_counter()

        decompress_time = t_end - t_start

        dst_path = os.path.join(dst_dir, filename)
        # Avoid overwriting
        if os.path.exists(dst_path):
            base, ext = os.path.splitext(filename)
            dst_path  = os.path.join(dst_dir, f"{base}_restored{ext}")

        if progress_cb:
            progress_cb(85, "Writing restored file…")

        with open(dst_path, "wb") as f:
            f.write(data)

        if progress_cb:
            progress_cb(100, "Done.")

        ratio = orig_sz / max(compressed_size, 1)
        return {
            "algorithm":         algo_name,
            "original_size":     orig_sz,
            "compressed_size":   compressed_size,
            "ratio":             ratio,
            "decompress_time":   decompress_time,
            "src_path":          src_path,
            "dst_path":          dst_path,
            "timestamp":         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def entropy_bits(data: bytes) -> float:
    """Shannon entropy of the byte sequence."""
    if not data:
        return 0.0
    freq = collections.Counter(data)
    total = len(data)
    return -sum((c/total) * math.log2(c/total) for c in freq.values())


# ─────────────────────────────────────────────────────────────────────────────
#  CUSTOM WIDGETS
# ─────────────────────────────────────────────────────────────────────────────
class StyledButton(tk.Canvas):
    def __init__(self, parent, text, command=None, color=None,
                 width=160, height=40, **kwargs):
        color = color or COLORS["accent"]
        super().__init__(parent, width=width, height=height,
                         bg=COLORS["bg_panel"], highlightthickness=0, **kwargs)
        self._text    = text
        self._command = command
        self._color   = color
        self._width   = width
        self._height  = height
        self._hover   = False
        self._draw()
        self.bind("<Enter>",        self._on_enter)
        self.bind("<Leave>",        self._on_leave)
        self.bind("<ButtonPress-1>",self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _draw(self, pressed=False):
        self.delete("all")
        c  = self._color
        bg = COLORS["bg_dark"] if pressed else (
             self._darken(c, 0.15) if self._hover else COLORS["bg_card"])
        # Border rectangle
        self.create_rectangle(0, 0, self._width, self._height,
                              outline=c, fill=bg, width=2)
        # Glow line top
        if self._hover and not pressed:
            self.create_line(2, 1, self._width-2, 1, fill=c, width=1)
        self.create_text(self._width//2, self._height//2,
                         text=self._text,
                         fill=c if not pressed else COLORS["text_sec"],
                         font=("Consolas", 11, "bold"))

    def _darken(self, hex_color, amount):
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        r = max(0, int(r * (1 - amount)))
        g = max(0, int(g * (1 - amount)))
        b = max(0, int(b * (1 - amount)))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _on_enter(self, e):
        self._hover = True;  self._draw()
    def _on_leave(self, e):
        self._hover = False; self._draw()
    def _on_press(self, e):
        self._draw(pressed=True)
    def _on_release(self, e):
        self._draw();
        if self._command:
            self._command()

    def configure_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.itemconfigure("all", state=state)
        self._hover = False
        self._draw()


class MetricCard(tk.Frame):
    def __init__(self, parent, label, value="—", unit="",
                 color=None, **kwargs):
        color = color or COLORS["accent"]
        super().__init__(parent, bg=COLORS["bg_card"],
                         highlightbackground=color,
                         highlightthickness=1, **kwargs)
        tk.Label(self, text=label, bg=COLORS["bg_card"],
                 fg=COLORS["text_sec"],
                 font=("Consolas", 8, "bold")).pack(anchor="w", padx=10, pady=(8,0))
        self._val_lbl = tk.Label(self, text=value,
                                  bg=COLORS["bg_card"], fg=color,
                                  font=("Consolas", 18, "bold"))
        self._val_lbl.pack(anchor="w", padx=10)
        tk.Label(self, text=unit, bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"],
                 font=("Consolas", 8)).pack(anchor="w", padx=10, pady=(0,8))

    def set(self, value, unit=""):
        self._val_lbl.config(text=str(value))


class ProgressBar(tk.Canvas):
    def __init__(self, parent, width=500, height=6,
                 color=None, **kwargs):
        color = color or COLORS["accent"]
        super().__init__(parent, width=width, height=height,
                         bg=COLORS["bg_card"],
                         highlightthickness=0, **kwargs)
        self._w     = width
        self._h     = height
        self._color = color
        self._pct   = 0
        self._draw()

    def _draw(self):
        self.delete("all")
        self.create_rectangle(0, 0, self._w, self._h,
                              fill=COLORS["bg_dark"], outline="")
        filled = int(self._w * self._pct / 100)
        if filled > 0:
            self.create_rectangle(0, 0, filled, self._h,
                                  fill=self._color, outline="")
            # Glow tip
            tip_w = min(30, filled)
            self.create_rectangle(filled - tip_w, 0, filled, self._h,
                                  fill=COLORS["accent_glow"], outline="",
                                  stipple="gray50")

    def set_progress(self, pct: float):
        self._pct = max(0, min(100, pct))
        self._draw()


# ─────────────────────────────────────────────────────────────────────────────
#  HISTORY LOG
# ─────────────────────────────────────────────────────────────────────────────
class HistoryLog:
    def __init__(self):
        self._records: list = []

    def add(self, record: dict):
        self._records.insert(0, record)

    def all(self):
        return list(self._records)

    def clear(self):
        self._records.clear()

    def export_csv(self, path: str):
        import csv
        keys = ["timestamp", "operation", "algorithm",
                "original_size", "compressed_size", "ratio",
                "saving_pct", "src_path", "dst_path"]
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(self._records)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
class DataCompressorApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(f"DataCompressor v{APP_VERSION}  ·  FUDM CSA/2023/27539")
        self.geometry("980x720")
        self.minsize(800, 620)
        self.configure(bg=COLORS["bg_dark"])
        self.resizable(True, True)

        # Try to set a dark title bar on Windows
        try:
            from ctypes import windll, byref, c_int, sizeof
            hwnd = windll.user32.GetParent(self.winfo_id())
            windll.dwmapi.DwmSetWindowAttribute(hwnd, 20,
                                                 byref(c_int(1)), sizeof(c_int))
        except Exception:
            pass

        self._history  = HistoryLog()
        self._src_path = tk.StringVar()
        self._algo_var = tk.StringVar(value="Auto (Best Fit)")
        self._status   = tk.StringVar(value="Ready")
        self._busy     = False

        self._build_ui()

    # ─── UI BUILDER ──────────────────────────────────────────────────────
    def _build_ui(self):
        # Top bar
        self._build_header()

        # Main notebook (tabs)
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Dark.TNotebook",
                         background=COLORS["bg_dark"],
                         borderwidth=0)
        style.configure("Dark.TNotebook.Tab",
                         background=COLORS["bg_panel"],
                         foreground=COLORS["text_sec"],
                         padding=[18, 8],
                         font=("Consolas", 10, "bold"),
                         borderwidth=0)
        style.map("Dark.TNotebook.Tab",
                  background=[("selected", COLORS["bg_card"])],
                  foreground=[("selected", COLORS["accent"])])

        self._nb = ttk.Notebook(self, style="Dark.TNotebook")
        self._nb.pack(fill="both", expand=True, padx=0, pady=0)

        self._tab_compress   = tk.Frame(self._nb, bg=COLORS["bg_dark"])
        self._tab_decompress = tk.Frame(self._nb, bg=COLORS["bg_dark"])
        self._tab_history    = tk.Frame(self._nb, bg=COLORS["bg_dark"])
        self._tab_about      = tk.Frame(self._nb, bg=COLORS["bg_dark"])

        self._nb.add(self._tab_compress,   text="  COMPRESS  ")
        self._nb.add(self._tab_decompress, text="  DECOMPRESS  ")
        self._nb.add(self._tab_history,    text="  HISTORY  ")
        self._nb.add(self._tab_about,      text="  ABOUT  ")

        self._build_compress_tab()
        self._build_decompress_tab()
        self._build_history_tab()
        self._build_about_tab()

        # Status bar
        self._build_statusbar()

    def _build_header(self):
        hdr = tk.Frame(self, bg=COLORS["bg_panel"], height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Left: logo + title
        left = tk.Frame(hdr, bg=COLORS["bg_panel"])
        left.pack(side="left", padx=20, pady=8)

        tk.Label(left, text="◈", bg=COLORS["bg_panel"],
                 fg=COLORS["accent"],
                 font=("Consolas", 22, "bold")).pack(side="left")
        tk.Label(left, text=" DataCompressor",
                 bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
                 font=("Consolas", 16, "bold")).pack(side="left")
        tk.Label(left, text=f"  v{APP_VERSION}",
                 bg=COLORS["bg_panel"], fg=COLORS["text_muted"],
                 font=("Consolas", 10)).pack(side="left")

        # Right: student info
        right = tk.Frame(hdr, bg=COLORS["bg_panel"])
        right.pack(side="right", padx=20, pady=4)
        tk.Label(right, text="DANJUMA JOSHUA AUDU  ·  CSA/2023/27539",
                 bg=COLORS["bg_panel"], fg=COLORS["text_sec"],
                 font=("Consolas", 9)).pack(anchor="e")
        tk.Label(right, text="Federal University Dutsin-Ma  ·  Dept. CSIT",
                 bg=COLORS["bg_panel"], fg=COLORS["text_muted"],
                 font=("Consolas", 8)).pack(anchor="e")

        # Separator line
        sep = tk.Frame(self, bg=COLORS["accent"], height=2)
        sep.pack(fill="x")

    def _build_statusbar(self):
        bar = tk.Frame(self, bg=COLORS["bg_panel"], height=28)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Label(bar, textvariable=self._status,
                 bg=COLORS["bg_panel"], fg=COLORS["accent"],
                 font=("Consolas", 9), anchor="w").pack(
                     side="left", padx=12, pady=4)

    # ─── COMPRESS TAB ────────────────────────────────────────────────────
    def _build_compress_tab(self):
        outer = tk.Frame(self._tab_compress, bg=COLORS["bg_dark"])
        outer.pack(fill="both", expand=True, padx=24, pady=20)

        # ── File selector ──
        fs = tk.LabelFrame(outer, text=" 1.  SELECT FILE ",
                           bg=COLORS["bg_panel"],
                           fg=COLORS["accent"],
                           font=("Consolas", 10, "bold"),
                           bd=1, relief="solid",
                           highlightbackground=COLORS["border"])
        fs.pack(fill="x", pady=(0, 14))

        row = tk.Frame(fs, bg=COLORS["bg_panel"])
        row.pack(fill="x", padx=14, pady=12)

        self._c_path_entry = tk.Entry(row, textvariable=self._src_path,
                                       bg=COLORS["bg_input"],
                                       fg=COLORS["text_primary"],
                                       font=("Consolas", 10),
                                       insertbackground=COLORS["accent"],
                                       relief="flat", bd=4)
        self._c_path_entry.pack(side="left", fill="x", expand=True, ipady=5)

        StyledButton(row, "Browse…", command=self._browse_compress,
                     color=COLORS["blue"], width=110, height=34).pack(
                         side="left", padx=(8,0))

        # File info strip
        self._c_info_lbl = tk.Label(fs, text="No file selected.",
                                     bg=COLORS["bg_panel"],
                                     fg=COLORS["text_muted"],
                                     font=("Consolas", 9),
                                     anchor="w")
        self._c_info_lbl.pack(fill="x", padx=14, pady=(0,8))

        # ── Algorithm selector ──
        algo_f = tk.LabelFrame(outer, text=" 2.  CHOOSE ALGORITHM ",
                               bg=COLORS["bg_panel"],
                               fg=COLORS["accent"],
                               font=("Consolas", 10, "bold"),
                               bd=1, relief="solid")
        algo_f.pack(fill="x", pady=(0, 14))

        arow = tk.Frame(algo_f, bg=COLORS["bg_panel"])
        arow.pack(fill="x", padx=14, pady=12)

        algos = ["Auto (Best Fit)"] + list(ALGO_MAP.keys())
        self._algo_btns = {}
        for algo in algos:
            col = ALGO_COLORS.get(algo, COLORS["accent"])
            rb  = tk.Radiobutton(arow, text=algo,
                                  variable=self._algo_var,
                                  value=algo,
                                  bg=COLORS["bg_panel"],
                                  fg=col,
                                  selectcolor=COLORS["bg_dark"],
                                  activebackground=COLORS["bg_panel"],
                                  activeforeground=col,
                                  font=("Consolas", 10),
                                  indicatoron=True,
                                  cursor="hand2")
            rb.pack(side="left", padx=16, pady=4)
            self._algo_btns[algo] = rb

        # Algorithm descriptions
        self._algo_desc = tk.Label(algo_f,
                                    text=self._get_algo_desc("Auto (Best Fit)"),
                                    bg=COLORS["bg_panel"],
                                    fg=COLORS["text_sec"],
                                    font=("Consolas", 9),
                                    wraplength=800, anchor="w",
                                    justify="left")
        self._algo_desc.pack(fill="x", padx=14, pady=(0,10))
        self._algo_var.trace_add("write",
            lambda *_: self._algo_desc.config(
                text=self._get_algo_desc(self._algo_var.get())))

        # ── Action ──
        act = tk.Frame(outer, bg=COLORS["bg_dark"])
        act.pack(fill="x", pady=(0, 14))

        self._c_compress_btn = StyledButton(
            act, "⬇  COMPRESS FILE",
            command=self._do_compress,
            color=COLORS["accent"], width=220, height=46)
        self._c_compress_btn.pack(side="left")

        # Progress bar + status
        prog_f = tk.Frame(act, bg=COLORS["bg_dark"])
        prog_f.pack(side="left", fill="x", expand=True, padx=20)

        self._c_progress = ProgressBar(prog_f, width=480, height=8,
                                        color=COLORS["accent"])
        self._c_progress.pack(fill="x", pady=(12,4))

        self._c_prog_lbl = tk.Label(prog_f, text="",
                                     bg=COLORS["bg_dark"],
                                     fg=COLORS["text_sec"],
                                     font=("Consolas", 9))
        self._c_prog_lbl.pack(anchor="w")

        # ── Metrics cards ──
        metrics_f = tk.LabelFrame(outer, text=" 3.  RESULTS ",
                                   bg=COLORS["bg_panel"],
                                   fg=COLORS["accent"],
                                   font=("Consolas", 10, "bold"),
                                   bd=1, relief="solid")
        metrics_f.pack(fill="both", expand=True)

        cards_row = tk.Frame(metrics_f, bg=COLORS["bg_panel"])
        cards_row.pack(fill="x", padx=14, pady=14)

        self._c_cards = {}
        card_defs = [
            ("Original Size",    "—", "",    COLORS["text_sec"]),
            ("Compressed Size",  "—", "",    COLORS["accent"]),
            ("Compression Ratio","—", ":1",  COLORS["blue"]),
            ("Space Saved",      "—", "%",   COLORS["orange"]),
            ("Time Taken",       "—", "sec", COLORS["yellow"]),
            ("Shannon Entropy",  "—", "bits",COLORS["accent_dim"]),
        ]
        for label, val, unit, color in card_defs:
            c = MetricCard(cards_row, label, val, unit, color=color)
            c.pack(side="left", fill="both", expand=True, padx=4)
            self._c_cards[label] = c

    def _get_algo_desc(self, algo: str) -> str:
        descs = {
            "Auto (Best Fit)":
                "Automatically benchmarks all three algorithms on a sample of "
                "your file and selects the one with the best compression score.",
            "Huffman Coding":
                "Variable-length entropy encoding. Assigns shorter bit codes to "
                "more frequent bytes. Optimal for text-heavy files. O(n log n).",
            "Run-Length Encoding (RLE)":
                "Replaces consecutive identical bytes with (count, byte) pairs. "
                "Extremely fast. Best for files with long runs of repeated data.",
            "Lempel-Ziv-Welch (LZW)":
                "Dictionary-based compression. Builds a code table of repeated "
                "byte sequences on the fly. Best for structured/repetitive data.",
        }
        return descs.get(algo, "")

    def _browse_compress(self):
        path = filedialog.askopenfilename(
            title="Select a file to compress",
            filetypes=[
                ("All supported", "*.txt *.csv *.log *.py *.html *.xml "
                                  "*.json *.bmp *.wav *.bin *.dat *.*"),
                ("Text files",  "*.txt *.csv *.log *.py *.html *.xml *.json"),
                ("Image files", "*.bmp"),
                ("Audio files", "*.wav"),
                ("All files",   "*.*"),
            ]
        )
        if path:
            self._src_path.set(path)
            size = os.path.getsize(path)
            with open(path, "rb") as f:
                sample = f.read(min(size, 8192))
            ent = entropy_bits(sample)
            self._c_info_lbl.config(
                text=f"  {os.path.basename(path)}    │    "
                     f"Size: {human_size(size)}    │    "
                     f"Entropy: {ent:.3f} bits/byte    │    "
                     f"Type: {os.path.splitext(path)[1].upper() or 'binary'}",
                fg=COLORS["text_sec"]
            )
            self._status.set(f"File loaded: {os.path.basename(path)}")

    def _do_compress(self):
        src = self._src_path.get().strip()
        if not src or not os.path.isfile(src):
            messagebox.showerror("No File", "Please select a valid input file.")
            return
        if self._busy:
            return

        dst = filedialog.asksaveasfilename(
            title="Save compressed file as…",
            defaultextension=COMPRESSED_EXT,
            initialfile=os.path.basename(src) + COMPRESSED_EXT,
            filetypes=[("FUDMC Compressed", f"*{COMPRESSED_EXT}"),
                       ("All files", "*.*")]
        )
        if not dst:
            return

        self._busy = True
        self._c_compress_btn.configure_state(False)
        algo = self._algo_var.get()

        def run():
            try:
                def cb(pct, msg):
                    self.after(0, self._c_progress.set_progress, pct)
                    self.after(0, self._c_prog_lbl.config, {"text": msg})
                    self.after(0, self._status.set, msg)

                metrics = CompressionEngine.compress_file(src, dst, algo, cb)
                metrics["operation"] = "compress"
                self._history.add(metrics)
                self.after(0, self._show_compress_metrics, metrics)
            except Exception as ex:
                self.after(0, messagebox.showerror, "Error", str(ex))
            finally:
                self._busy = False
                self.after(0, self._c_compress_btn.configure_state, True)

        threading.Thread(target=run, daemon=True).start()

    def _show_compress_metrics(self, m: dict):
        self._c_cards["Original Size"].set(human_size(m["original_size"]))
        self._c_cards["Compressed Size"].set(human_size(m["compressed_size"]))
        self._c_cards["Compression Ratio"].set(f"{m['ratio']:.2f}")
        self._c_cards["Space Saved"].set(f"{m['saving_pct']:.1f}")
        self._c_cards["Time Taken"].set(f"{m['compress_time']:.4f}")

        # Entropy of source file
        with open(m["src_path"], "rb") as f:
            sample = f.read(65536)
        ent = entropy_bits(sample)
        self._c_cards["Shannon Entropy"].set(f"{ent:.3f}")

        self._c_prog_lbl.config(text=(
            f"✔  Saved to: {os.path.basename(m['dst_path'])}    "
            f"Algorithm used: {m['algorithm']}"
        ))
        self._status.set(
            f"Compressed  {human_size(m['original_size'])}  →  "
            f"{human_size(m['compressed_size'])}  "
            f"({m['saving_pct']:.1f}% saved)  via {m['algorithm']}"
        )
        self._refresh_history()

    # ─── DECOMPRESS TAB ──────────────────────────────────────────────────
    def _build_decompress_tab(self):
        outer = tk.Frame(self._tab_decompress, bg=COLORS["bg_dark"])
        outer.pack(fill="both", expand=True, padx=24, pady=20)

        # File selector
        fs = tk.LabelFrame(outer, text=" 1.  SELECT .fudmc FILE ",
                           bg=COLORS["bg_panel"], fg=COLORS["blue"],
                           font=("Consolas", 10, "bold"),
                           bd=1, relief="solid")
        fs.pack(fill="x", pady=(0, 14))

        row = tk.Frame(fs, bg=COLORS["bg_panel"])
        row.pack(fill="x", padx=14, pady=12)

        self._d_path_var   = tk.StringVar()
        self._d_path_entry = tk.Entry(row, textvariable=self._d_path_var,
                                       bg=COLORS["bg_input"],
                                       fg=COLORS["text_primary"],
                                       font=("Consolas", 10),
                                       insertbackground=COLORS["blue"],
                                       relief="flat", bd=4)
        self._d_path_entry.pack(side="left", fill="x", expand=True, ipady=5)

        StyledButton(row, "Browse…", command=self._browse_decompress,
                     color=COLORS["blue"], width=110, height=34).pack(
                         side="left", padx=(8,0))

        self._d_info_lbl = tk.Label(fs, text="No file selected.",
                                     bg=COLORS["bg_panel"],
                                     fg=COLORS["text_muted"],
                                     font=("Consolas", 9), anchor="w")
        self._d_info_lbl.pack(fill="x", padx=14, pady=(0,8))

        # Output directory
        od = tk.LabelFrame(outer, text=" 2.  SELECT OUTPUT FOLDER ",
                           bg=COLORS["bg_panel"], fg=COLORS["blue"],
                           font=("Consolas", 10, "bold"),
                           bd=1, relief="solid")
        od.pack(fill="x", pady=(0, 14))

        row2 = tk.Frame(od, bg=COLORS["bg_panel"])
        row2.pack(fill="x", padx=14, pady=12)

        self._d_dir_var = tk.StringVar(value=os.path.expanduser("~"))
        tk.Entry(row2, textvariable=self._d_dir_var,
                 bg=COLORS["bg_input"], fg=COLORS["text_primary"],
                 font=("Consolas", 10),
                 insertbackground=COLORS["blue"],
                 relief="flat", bd=4).pack(
                     side="left", fill="x", expand=True, ipady=5)

        StyledButton(row2, "Choose…",
                     command=lambda: self._d_dir_var.set(
                         filedialog.askdirectory(
                             title="Select output folder") or
                         self._d_dir_var.get()),
                     color=COLORS["blue"], width=110, height=34).pack(
                         side="left", padx=(8,0))

        # Action
        act = tk.Frame(outer, bg=COLORS["bg_dark"])
        act.pack(fill="x", pady=(0,14))

        self._d_decompress_btn = StyledButton(
            act, "⬆  DECOMPRESS FILE",
            command=self._do_decompress,
            color=COLORS["blue"], width=230, height=46)
        self._d_decompress_btn.pack(side="left")

        prog_f = tk.Frame(act, bg=COLORS["bg_dark"])
        prog_f.pack(side="left", fill="x", expand=True, padx=20)

        self._d_progress = ProgressBar(prog_f, width=480, height=8,
                                        color=COLORS["blue"])
        self._d_progress.pack(fill="x", pady=(12,4))

        self._d_prog_lbl = tk.Label(prog_f, text="",
                                     bg=COLORS["bg_dark"],
                                     fg=COLORS["text_sec"],
                                     font=("Consolas", 9))
        self._d_prog_lbl.pack(anchor="w")

        # Results
        res_f = tk.LabelFrame(outer, text=" 3.  RESULTS ",
                               bg=COLORS["bg_panel"], fg=COLORS["blue"],
                               font=("Consolas", 10, "bold"),
                               bd=1, relief="solid")
        res_f.pack(fill="both", expand=True)

        cards_row = tk.Frame(res_f, bg=COLORS["bg_panel"])
        cards_row.pack(fill="x", padx=14, pady=14)

        self._d_cards = {}
        card_defs = [
            ("Compressed Size",   "—", "",    COLORS["text_sec"]),
            ("Restored Size",     "—", "",    COLORS["blue"]),
            ("Compression Ratio", "—", ":1",  COLORS["accent"]),
            ("Algorithm Used",    "—", "",    COLORS["orange"]),
            ("Time Taken",        "—", "sec", COLORS["yellow"]),
            ("Output File",       "—", "",    COLORS["accent_dim"]),
        ]
        for label, val, unit, color in card_defs:
            c = MetricCard(cards_row, label, val, unit, color=color)
            c.pack(side="left", fill="both", expand=True, padx=4)
            self._d_cards[label] = c

    def _browse_decompress(self):
        path = filedialog.askopenfilename(
            title="Select a .fudmc file to decompress",
            filetypes=[("FUDMC files", f"*{COMPRESSED_EXT}"),
                       ("All files", "*.*")]
        )
        if path:
            self._d_path_var.set(path)
            size = os.path.getsize(path)
            self._d_info_lbl.config(
                text=f"  {os.path.basename(path)}    │    Size: {human_size(size)}",
                fg=COLORS["text_sec"]
            )

    def _do_decompress(self):
        src = self._d_path_var.get().strip()
        if not src or not os.path.isfile(src):
            messagebox.showerror("No File", "Please select a .fudmc file.")
            return
        dst_dir = self._d_dir_var.get().strip()
        if not dst_dir or not os.path.isdir(dst_dir):
            messagebox.showerror("No Folder", "Please select a valid output folder.")
            return
        if self._busy:
            return

        self._busy = True
        self._d_decompress_btn.configure_state(False)

        def run():
            try:
                def cb(pct, msg):
                    self.after(0, self._d_progress.set_progress, pct)
                    self.after(0, self._d_prog_lbl.config, {"text": msg})
                    self.after(0, self._status.set, msg)

                metrics = CompressionEngine.decompress_file(src, dst_dir, cb)
                metrics["operation"] = "decompress"
                self._history.add(metrics)
                self.after(0, self._show_decompress_metrics, metrics)
            except Exception as ex:
                self.after(0, messagebox.showerror, "Decompression Error", str(ex))
            finally:
                self._busy = False
                self.after(0, self._d_decompress_btn.configure_state, True)

        threading.Thread(target=run, daemon=True).start()

    def _show_decompress_metrics(self, m: dict):
        self._d_cards["Compressed Size"].set(human_size(m["compressed_size"]))
        self._d_cards["Restored Size"].set(human_size(m["original_size"]))
        self._d_cards["Compression Ratio"].set(f"{m['ratio']:.2f}")
        self._d_cards["Algorithm Used"].set(m["algorithm"])
        self._d_cards["Time Taken"].set(f"{m['decompress_time']:.4f}")
        self._d_cards["Output File"].set(os.path.basename(m["dst_path"]))

        self._d_prog_lbl.config(
            text=f"✔  Restored to: {m['dst_path']}")
        self._status.set(
            f"Decompressed  {human_size(m['compressed_size'])}  →  "
            f"{human_size(m['original_size'])}  via {m['algorithm']}"
        )
        self._refresh_history()

    # ─── HISTORY TAB ─────────────────────────────────────────────────────
    def _build_history_tab(self):
        outer = tk.Frame(self._tab_history, bg=COLORS["bg_dark"])
        outer.pack(fill="both", expand=True, padx=24, pady=20)

        # Top controls
        ctl = tk.Frame(outer, bg=COLORS["bg_dark"])
        ctl.pack(fill="x", pady=(0, 10))

        tk.Label(ctl, text="SESSION HISTORY",
                 bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
                 font=("Consolas", 12, "bold")).pack(side="left")

        StyledButton(ctl, "Export CSV",
                     command=self._export_history,
                     color=COLORS["blue"], width=130, height=34).pack(
                         side="right", padx=4)
        StyledButton(ctl, "Clear",
                     command=self._clear_history,
                     color=COLORS["red"], width=90, height=34).pack(
                         side="right", padx=4)

        # Treeview
        cols = ("Timestamp", "Op", "Algorithm",
                "Original", "Compressed", "Ratio", "Saved%", "File")
        style = ttk.Style()
        style.configure("Dark.Treeview",
                         background=COLORS["bg_card"],
                         foreground=COLORS["text_primary"],
                         fieldbackground=COLORS["bg_card"],
                         rowheight=26,
                         font=("Consolas", 9))
        style.configure("Dark.Treeview.Heading",
                         background=COLORS["bg_panel"],
                         foreground=COLORS["accent"],
                         font=("Consolas", 9, "bold"),
                         relief="flat")
        style.map("Dark.Treeview",
                  background=[("selected", COLORS["bg_input"])],
                  foreground=[("selected", COLORS["accent"])])

        tree_frame = tk.Frame(outer, bg=COLORS["border"])
        tree_frame.pack(fill="both", expand=True)

        self._hist_tree = ttk.Treeview(tree_frame, columns=cols,
                                        show="headings",
                                        style="Dark.Treeview")
        col_widths = [130, 80, 190, 90, 90, 70, 70, 180]
        for col, w in zip(cols, col_widths):
            self._hist_tree.heading(col, text=col)
            self._hist_tree.column(col, width=w, anchor="center"
                                   if col not in ("File",) else "w",
                                   stretch=(col == "File"))

        sb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self._hist_tree.yview)
        self._hist_tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._hist_tree.pack(fill="both", expand=True)

    def _refresh_history(self):
        for item in self._hist_tree.get_children():
            self._hist_tree.delete(item)
        for r in self._history.all():
            op = r.get("operation", "?")
            tag = "compress" if op == "compress" else "decompress"
            time_key = "compress_time" if op == "compress" else "decompress_time"
            self._hist_tree.insert("", "end", values=(
                r.get("timestamp", ""),
                op.upper(),
                r.get("algorithm", ""),
                human_size(r.get("original_size", 0)),
                human_size(r.get("compressed_size", 0)),
                f"{r.get('ratio', 0):.2f}",
                f"{r.get('saving_pct', 0):.1f}%" if op == "compress" else "—",
                os.path.basename(r.get("src_path", "")),
            ), tags=(tag,))
        self._hist_tree.tag_configure("compress",   foreground=COLORS["accent"])
        self._hist_tree.tag_configure("decompress", foreground=COLORS["blue"])

    def _export_history(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")],
            initialfile="compression_history.csv"
        )
        if path:
            self._history.export_csv(path)
            messagebox.showinfo("Exported",
                                f"History saved to:\n{path}")

    def _clear_history(self):
        if messagebox.askyesno("Clear History",
                               "Clear all session history?"):
            self._history.clear()
            self._refresh_history()

    # ─── ABOUT TAB ───────────────────────────────────────────────────────
    def _build_about_tab(self):
        outer = tk.Frame(self._tab_about, bg=COLORS["bg_dark"])
        outer.pack(fill="both", expand=True)

        # Centred card
        card = tk.Frame(outer, bg=COLORS["bg_panel"],
                        highlightbackground=COLORS["accent"],
                        highlightthickness=1)
        card.place(relx=0.5, rely=0.5, anchor="center")

        def lbl(text, fg=None, font=None, pady=2):
            tk.Label(card, text=text,
                     bg=COLORS["bg_panel"],
                     fg=fg or COLORS["text_primary"],
                     font=font or ("Consolas", 11)).pack(pady=pady)

        tk.Label(card, text="◈", bg=COLORS["bg_panel"],
                 fg=COLORS["accent"],
                 font=("Consolas", 36, "bold")).pack(pady=(30,4))
        lbl("DataCompressor", fg=COLORS["accent"],
            font=("Consolas", 20, "bold"))
        lbl(f"Version {APP_VERSION}  ·  FUDM 2025/2026",
            fg=COLORS["text_sec"])

        tk.Frame(card, bg=COLORS["border"], height=1,
                 width=400).pack(pady=16)

        lbl("DANJUMA JOSHUA AUDU", fg=COLORS["text_primary"],
            font=("Consolas", 13, "bold"))
        lbl("CSA/2023/27539", fg=COLORS["blue"])
        lbl("Dept. of Computer Science & Information Technology",
            fg=COLORS["text_sec"])
        lbl("Faculty of Computing", fg=COLORS["text_sec"])
        lbl("Federal University Dutsin-Ma, Katsina State", fg=COLORS["text_sec"])

        tk.Frame(card, bg=COLORS["border"], height=1,
                 width=400).pack(pady=16)

        lbl("Supervisor: Mr. STEPHEN LUKA", fg=COLORS["text_sec"])

        tk.Frame(card, bg=COLORS["border"], height=1,
                 width=400).pack(pady=16)

        lbl("Algorithms Implemented", fg=COLORS["accent"],
            font=("Consolas", 10, "bold"))
        lbl("Huffman Coding  ·  Run-Length Encoding  ·  Lempel-Ziv-Welch",
            fg=COLORS["text_sec"])

        lbl("Supported Formats", fg=COLORS["accent"],
            font=("Consolas", 10, "bold"), pady=(10,2))
        lbl(".txt  .csv  .log  .py  .html  .xml  .json  .bmp  .wav  + any binary",
            fg=COLORS["text_sec"])

        tk.Frame(card, bg=COLORS["border"], height=1,
                 width=400).pack(pady=16)

        lbl("Built entirely in Python (stdlib only). No third-party packages.",
            fg=COLORS["text_muted"], font=("Consolas", 9))
        lbl("Run: python DataCompressor_DANJUMA_CSA2023_27539.py",
            fg=COLORS["yellow"], font=("Consolas", 9))
        tk.Label(card, text="", bg=COLORS["bg_panel"]).pack(pady=10)


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = DataCompressorApp()
    # Centre window on screen
    app.update_idletasks()
    w, h = 980, 720
    x = (app.winfo_screenwidth()  - w) // 2
    y = (app.winfo_screenheight() - h) // 2
    app.geometry(f"{w}x{h}+{x}+{y}")
    app.mainloop()
