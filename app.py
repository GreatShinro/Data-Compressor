"""
DataCompressor — Streamlit Web App
DANJUMA JOSHUA AUDU · CSA/2023/27539
Federal University Dutsin-Ma
"""

import streamlit as st
from compressor import (
    CompressionEngine, ALGO_MAP, APP_VERSION,
    human_size, entropy_bits, COMPRESSED_EXT,
)

st.set_page_config(
    page_title="DataCompressor",
    page_icon="◈",
    layout="wide",
)

st.markdown("""
<style>
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

st.markdown("## ◈ DataCompressor &nbsp; `v" + APP_VERSION + "`")
st.caption("DANJUMA JOSHUA AUDU · CSA/2023/27539 · Federal University Dutsin-Ma")
st.divider()

ALGO_OPTIONS = ["Auto (Best Fit)"] + list(ALGO_MAP.keys())
ALGO_DESCS = {
    "Auto (Best Fit)":             "Benchmarks all three algorithms on a sample and picks the best.",
    "Huffman Coding":              "Variable-length entropy encoding. Best for text-heavy files.",
    "Run-Length Encoding (RLE)":   "Replaces repeated byte runs with (count, byte) pairs. Very fast.",
    "Lempel-Ziv-Welch (LZW)":     "Dictionary-based compression. Best for structured/repetitive data.",
}

tab_compress, tab_decompress, tab_history, tab_about = st.tabs(["⬇ Compress", "⬆ Decompress", "🕓 History", "ℹ About"])

# ── COMPRESS ──────────────────────────────────────────────────────────────────
with tab_compress:
    uploaded = st.file_uploader("Choose any file", key="c_upload")

    if uploaded:
        raw = uploaded.read()
        if len(raw) > 10 * 1024 * 1024:
            st.error("File too large. Maximum allowed size is 10 MB.")
            st.session_state.pop("c_raw", None)
        else:
            st.session_state["c_raw"] = raw
            st.session_state["c_name"] = uploaded.name
            st.session_state.pop("c_result", None)
            ent = entropy_bits(raw[:8192])
            st.caption(f"**{uploaded.name}** · {human_size(len(raw))} · Entropy: {ent:.3f} bits/byte")

    algo = st.selectbox("Algorithm", ALGO_OPTIONS, key="c_algo")
    st.caption(ALGO_DESCS[algo])

    if st.button("⬇ Compress", type="primary", disabled="c_raw" not in st.session_state):
        with st.spinner(f"Compressing with {algo}…"):
            compressed, m = CompressionEngine.compress_bytes(st.session_state["c_raw"], algo)
        st.session_state["c_result"] = (compressed, m, st.session_state["c_name"])

    if "c_result" in st.session_state:
        compressed, m, fname = st.session_state["c_result"]
        st.success(
            f"Done · {human_size(m['original_size'])} → {human_size(m['compressed_size'])} · "
            f"{m['saving_pct']:.1f}% saved · Algorithm: **{m['algorithm']}** · {m['compress_time']:.4f}s"
        )
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Original",   human_size(m["original_size"]))
        col2.metric("Compressed", human_size(m["compressed_size"]))
        col3.metric("Ratio",      f"{m['ratio']:.2f}:1")
        col4.metric("Saved",      f"{m['saving_pct']:.1f}%")
        st.download_button(
            "⬇ Download compressed file",
            data=compressed,
            file_name=fname + COMPRESSED_EXT,
            mime="application/octet-stream",
        )

# ── DECOMPRESS ────────────────────────────────────────────────────────────────
with tab_decompress:
    uploaded_d = st.file_uploader(f"Choose a {COMPRESSED_EXT} file", key="d_upload")

    if uploaded_d:
        raw_d = uploaded_d.read()
        st.session_state["d_raw"] = raw_d
        st.session_state["d_name"] = uploaded_d.name
        st.session_state.pop("d_result", None)
        st.caption(f"**{uploaded_d.name}** · {human_size(len(raw_d))}")

    if st.button("⬆ Decompress", type="primary", disabled="d_raw" not in st.session_state):
        try:
            with st.spinner("Decompressing…"):
                data, orig_filename, m = CompressionEngine.decompress_bytes(st.session_state["d_raw"])
            st.session_state["d_result"] = (data, orig_filename, m, st.session_state["d_name"])
        except ValueError as e:
            st.error(str(e))

    if "d_result" in st.session_state:
        data, orig_filename, m, dname = st.session_state["d_result"]
        st.success(
            f"Done · {human_size(m['compressed_size'])} → {human_size(m['original_size'])} · "
            f"Algorithm: **{m['algorithm']}** · {m['decompress_time']:.4f}s"
        )
        col1, col2, col3 = st.columns(3)
        col1.metric("Compressed", human_size(m["compressed_size"]))
        col2.metric("Restored",   human_size(m["original_size"]))
        col3.metric("Ratio",      f"{m['ratio']:.2f}:1")
        st.download_button(
            "⬇ Download restored file",
            data=data,
            file_name=orig_filename or dname.removesuffix(COMPRESSED_EXT),
            mime="application/octet-stream",
        )

# ── HISTORY ───────────────────────────────────────────────────────────────────
with tab_history:
    import pandas as pd

    mock_history = [
        {"Timestamp": "2026-05-21 08:10:02", "File": "report.txt",    "Algorithm": "Huffman Coding",            "Original": "128 KB", "Compressed": "74 KB",  "Saved": "42.2%", "Time (s)": 0.0031, "Action": "Compress"},
        {"Timestamp": "2026-05-21 07:55:14", "File": "data.csv",      "Algorithm": "Lempel-Ziv-Welch (LZW)",    "Original": "512 KB", "Compressed": "198 KB", "Saved": "61.3%", "Time (s)": 0.0089, "Action": "Compress"},
        {"Timestamp": "2026-05-21 07:40:33", "File": "image.bmp",     "Algorithm": "Run-Length Encoding (RLE)", "Original": "2.1 MB", "Compressed": "1.8 MB", "Saved": "14.3%", "Time (s)": 0.0012, "Action": "Compress"},
        {"Timestamp": "2026-05-21 07:30:05", "File": "report.txt",    "Algorithm": "Huffman Coding",            "Original": "128 KB", "Compressed": "74 KB",  "Saved": "42.2%", "Time (s)": 0.0028, "Action": "Decompress"},
        {"Timestamp": "2026-05-20 22:15:47", "File": "archive.log",   "Algorithm": "Auto (Best Fit)",           "Original": "340 KB", "Compressed": "112 KB", "Saved": "67.1%", "Time (s)": 0.0154, "Action": "Compress"},
        {"Timestamp": "2026-05-20 21:03:19", "File": "source.py",     "Algorithm": "Huffman Coding",            "Original": "18 KB",  "Compressed": "11 KB",  "Saved": "38.9%", "Time (s)": 0.0009, "Action": "Compress"},
        {"Timestamp": "2026-05-20 20:48:52", "File": "config.json",   "Algorithm": "Lempel-Ziv-Welch (LZW)",   "Original": "6 KB",   "Compressed": "3 KB",   "Saved": "50.0%", "Time (s)": 0.0004, "Action": "Compress"},
        {"Timestamp": "2026-05-20 19:22:11", "File": "audio.wav",     "Algorithm": "Run-Length Encoding (RLE)","Original": "4.4 MB", "Compressed": "4.1 MB", "Saved": "6.8%",  "Time (s)": 0.0021, "Action": "Compress"},
    ]

    df = pd.DataFrame(mock_history)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Operations", len(df))
    col_b.metric("Files Compressed", len(df[df["Action"] == "Compress"]))
    col_c.metric("Files Decompressed", len(df[df["Action"] == "Decompress"]))

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption("⚠ Mock data — live history tracking not yet implemented.")

# ── ABOUT ─────────────────────────────────────────────────────────────────────
with tab_about:
    st.markdown(f"""
**DataCompressor** `v{APP_VERSION}`

| | |
|---|---|
| **Student** | DANJUMA JOSHUA AUDU |
| **MatNo** | CSA/2023/27539 |
| **Department** | Computer Science & Information Technology |
| **University** | Federal University Dutsin-Ma, Katsina State |
| **Supervisor** | Mr. STEPHEN LUKA |
| **Year** | 2025 / 2026 |

**Algorithms implemented from scratch:**
- Huffman Coding — variable-length entropy encoding
- Run-Length Encoding (RLE) — sequential repeat compression
- Lempel-Ziv-Welch (LZW) — dictionary-based compression

**Supported file types:** `.txt` `.csv` `.log` `.py` `.html` `.xml` `.json` `.bmp` `.wav` and any binary file.

Built entirely in Python (stdlib + Streamlit). No other third-party packages.
""")
