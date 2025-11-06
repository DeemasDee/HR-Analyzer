import streamlit as st
import json
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import timedelta

st.set_page_config(page_title="HAR Performance Analyzer", layout="wide")

st.title("📊 HAR Performance Analyzer")
st.markdown("""
Analisis performa web otomatis dari dua file **.HAR** (Desktop & Mobile).  
Menampilkan metrik teknis, perbandingan **Desktop vs Mobile**, grafik **timeline waterfall**, serta deskripsi interpretatif untuk non-teknis.
""")

col1, col2 = st.columns(2)
with col1:
    desktop_file = st.file_uploader("💻 Upload HAR (Desktop)", type=["har"], key="desktop")
with col2:
    mobile_file = st.file_uploader("📱 Upload HAR (Mobile)", type=["har"], key="mobile")

# ========== Fungsi Ekstraksi ==========
def extract_metrics(har_data, device_label):
    entries = har_data["log"]["entries"]
    rows = []

    for e in entries:
        timings = e["timings"]
        url = e["request"]["url"]
        start_time = e["startedDateTime"]
        total_time = e["time"]

        dns = None if timings.get("dns", 0) < 0 else timings.get("dns", 0)
        connect = None if timings.get("connect", 0) < 0 else timings.get("connect", 0)
        ssl = None if timings.get("ssl", 0) < 0 else timings.get("ssl", 0)
        wait = max(timings.get("wait", 0), 0)
        receive = max(timings.get("receive", 0), 0)

        domain = url.split("/")[2] if "//" in url else url

        rows.append({
            "url": url.split("?")[0],
            "domain": domain,
            "device": device_label,
            "dns": dns,
            "connect": connect,
            "ssl": ssl,
            "ttfb": wait,
            "receive": receive,
            "total": total_time,
            "startedDateTime": start_time,
            "dns_reused": timings.get("dns", 0) < 0,
            "conn_reused": timings.get("connect", 0) < 0,
            "ssl_reused": timings.get("ssl", 0) < 0
        })

    df = pd.DataFrame(rows)
    df["startedDateTime"] = pd.to_datetime(df["startedDateTime"])
    df["end_time"] = df["startedDateTime"] + pd.to_timedelta(df["total"], unit='ms')
    return df

# ========== Fungsi Deskripsi ==========
def describe_comparison(df):
    summary = df.groupby("device").mean(numeric_only=True)
    if len(summary) < 2:
        return "⚠️ Diperlukan dua file HAR: satu Desktop dan satu Mobile."

    desktop, mobile = summary.loc["Desktop"], summary.loc["Mobile"]
    ratio = desktop["total"] / mobile["total"] if mobile["total"] > 0 else np.nan

    reuse_info = df.groupby("device")[["dns_reused", "conn_reused", "ssl_reused"]].mean() * 100

    desc = f"""
🧠 **Analisis & Interpretasi**
⚡ Rata-rata total waktu Desktop: **{desktop['total']:.2f} ms**  
⚡ Rata-rata total waktu Mobile: **{mobile['total']:.2f} ms**

👉 Secara keseluruhan, **Mobile {ratio:.2f}x lebih cepat dibanding Desktop.**

📊 **Detail Perbedaan Tiap Komponen:**
"""
    for col in ["dns", "connect", "ssl", "ttfb", "receive", "total"]:
        d_val, m_val = desktop[col], mobile[col]
        if pd.isna(d_val) or pd.isna(m_val):
            continue
        diff = d_val - m_val
        if diff > 0:
            desc += f"- **{col.upper()}** pada **Mobile** lebih cepat {abs(diff):.2f} ms.\n"
        elif diff < 0:
            desc += f"- **{col.upper()}** pada **Desktop** lebih cepat {abs(diff):.2f} ms.\n"
        else:
            desc += f"- **{col.upper()}** memiliki waktu yang sama di kedua perangkat.\n"

    desc += "\n♻️ **Reuse Connection / Cache:**"
    for dev in reuse_info.index:
        dns_reuse = reuse_info.loc[dev, "dns_reused"]
        conn_reuse = reuse_info.loc[dev, "conn_reused"]
        ssl_reuse = reuse_info.loc[dev, "ssl_reused"]
        desc += f"\n- **{dev}**: DNS reuse {dns_reuse:.1f}%, TCP reuse {conn_reuse:.1f}%, SSL reuse {ssl_reuse:.1f}%."

    desc += "\n\n💡 Nilai reuse tinggi menunjukkan browser berhasil memanfaatkan koneksi/persistent cache untuk mempercepat load."
    return desc

# ========== Fungsi Heatmap Bottleneck ==========
def plot_bottleneck_heatmap(df):
    st.subheader("⚠️ Heatmap Bottleneck (Top Domain per Komponen)")
    heat_df = (
        df.groupby(["domain", "device"])[["dns", "connect", "ssl", "ttfb", "receive", "total"]]
        .mean(numeric_only=True)
        .reset_index()
    )
    melted = heat_df.melt(id_vars=["domain", "device"], var_name="Komponen", value_name="Waktu (ms)")
    fig = px.density_heatmap(
        melted,
        x="Komponen", y="domain",
        z="Waktu (ms)",
        color_continuous_scale="RdYlGn_r",
        facet_col="device",
        title="Heatmap Bottleneck per Domain dan Komponen",
        nbinsx=6
    )
    st.plotly_chart(fig, use_container_width=True)

# ========== MAIN ==========
if desktop_file and mobile_file:
    desktop_data = json.load(desktop_file)
    mobile_data = json.load(mobile_file)

    df_desktop = extract_metrics(desktop_data, "Desktop")
    df_mobile = extract_metrics(mobile_data, "Mobile")
    df = pd.concat([df_desktop, df_mobile], ignore_index=True)

    st.subheader("📋 Data Ekstraksi")
    st.dataframe(df, use_container_width=True)

    avg_df = df.groupby("device")[["dns", "connect", "ssl", "ttfb", "receive", "total"]].mean(numeric_only=True).reset_index()

    # Grafik perbandingan
    st.subheader("📈 Perbandingan Komponen (Desktop vs Mobile)")
    fig = px.bar(
        avg_df.melt(id_vars=["device"], value_vars=["dns", "connect", "ssl", "ttfb", "receive", "total"]),
        x="variable", y="value", color="device",
        barmode="group",
        labels={"variable": "Metrik", "value": "Waktu (ms)"},
        title="Rata-rata Waktu Komponen Desktop vs Mobile"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Waterfall timeline
    st.subheader("🌊 Waterfall Timeline")
    df_timeline = df.sort_values("startedDateTime")
    fig2 = px.timeline(
        df_timeline,
        x_start="startedDateTime",
        x_end="end_time",
        y="url",
        color="device",
        title="Timeline Request (Waterfall Chart)"
    )
    fig2.update_yaxes(showticklabels=False)
    st.plotly_chart(fig2, use_container_width=True)

    # Analisis & interpretasi
    st.subheader("🧠 Analisis & Interpretasi")
    st.markdown(describe_comparison(df))

    # Heatmap bottleneck
    plot_bottleneck_heatmap(df)

else:
    st.info("⬆️ Upload dua file HAR (Desktop dan Mobile) untuk memulai analisis.")

st.markdown("---")
st.caption("Version Dev v2.1 — Dual HAR Comparison + Bottleneck Heatmap")
