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

# ── Minimal custom CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-label { font-size: 0.75rem; color: #8B949E; }
.metric-value { font-size: 1.6rem; font-weight: 700; color: #00D084; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
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

tab_compress, tab_decompress, tab_about = st.tabs(["⬇ Compress", "⬆ Decompress", "ℹ About"])


# ── COMPRESS TAB ──────────────────────────────────────────────────────────────
with tab_compress:
    st.subheader("1. Upload a file")
    uploaded = st.file_uploader("Choose any file", key="c_upload",
                                label_visibility="collapsed")

    if uploaded:
        raw = uploaded.read()
        if len(raw) > 10 * 1024 * 1024:
            st.error("File too large. Maximum allowed size is 10 MB.")
            st.stop()
        st.session_state["c_raw"] = raw
        st.session_state["c_name"] = uploaded.name
        ent = entropy_bits(raw[:8192])
        st.caption(
            f"**{uploaded.name}** · {human_size(len(raw))} · "
            f"Entropy: {ent:.3f} bits/byte"
        )

    st.subheader("2. Choose algorithm")
    algo = st.radio("Algorithm", ALGO_OPTIONS, horizontal=True, key="c_algo",
                    label_visibility="collapsed")
    st.caption(ALGO_DESCS[algo])

    if st.button("⬇ Compress", type="primary", disabled=not uploaded):
        raw = st.session_state.get("c_raw", b"")
        with st.spinner(f"Compressing with {algo}…"):
            compressed, m = CompressionEngine.compress_bytes(raw, algo)

        st.success(
            f"Done · {human_size(m['original_size'])} → "
            f"{human_size(m['compressed_size'])} · "
            f"{m['saving_pct']:.1f}% saved · "
            f"Algorithm: **{m['algorithm']}** · "
            f"{m['compress_time']:.4f}s"
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Original",   human_size(m["original_size"]))
        col2.metric("Compressed", human_size(m["compressed_size"]))
        col3.metric("Ratio",      f"{m['ratio']:.2f}:1")
        col4.metric("Saved",      f"{m['saving_pct']:.1f}%")

        out_name = uploaded.name + COMPRESSED_EXT
        st.download_button(
            "⬇ Download compressed file",
            data=compressed,
            file_name=out_name,
            mime="application/octet-stream",
        )


# ── DECOMPRESS TAB ────────────────────────────────────────────────────────────
with tab_decompress:
    st.subheader("1. Upload a .fudmc file")
    uploaded_d = st.file_uploader(f"Choose a {COMPRESSED_EXT} file", key="d_upload",
                                  label_visibility="collapsed")

    if uploaded_d:
        st.caption(f"**{uploaded_d.name}** · {human_size(uploaded_d.size)}")

    if st.button("⬆ Decompress", type="primary", disabled=not uploaded_d):
        raw_d = uploaded_d.read()
        try:
            with st.spinner("Decompressing…"):
                data, orig_filename, m = CompressionEngine.decompress_bytes(raw_d)

            st.success(
                f"Done · {human_size(m['compressed_size'])} → "
                f"{human_size(m['original_size'])} · "
                f"Algorithm: **{m['algorithm']}** · "
                f"{m['decompress_time']:.4f}s"
            )

            col1, col2, col3 = st.columns(3)
            col1.metric("Compressed",  human_size(m["compressed_size"]))
            col2.metric("Restored",    human_size(m["original_size"]))
            col3.metric("Ratio",       f"{m['ratio']:.2f}:1")

            out_name = orig_filename or uploaded_d.name.removesuffix(COMPRESSED_EXT)
            st.download_button(
                "⬇ Download restored file",
                data=data,
                file_name=out_name,
                mime="application/octet-stream",
            )
        except ValueError as e:
            st.error(str(e))


# ── ABOUT TAB ─────────────────────────────────────────────────────────────────
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
