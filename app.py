import streamlit as st
import json
import pandas as pd
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="HAR Performance Analyzer", layout="wide")

st.title("📊 HAR Performance Analyzer")
st.markdown("""
Analisis performa web otomatis dari file **.HAR** (HTTP Archive).  
Menampilkan metrik teknis, perbandingan **Desktop vs Mobile**, grafik **timeline waterfall**, serta skor performa dan deteksi **bottleneck**.
""")

uploaded_file = st.file_uploader("📁 Upload HAR file", type=["har"])

# ========== Fungsi Ekstraksi ==========
def extract_metrics(har_data):
    entries = har_data["log"]["entries"]
    rows = []

    for e in entries:
        timings = e["timings"]
        url = e["request"]["url"]
        start_time = e["startedDateTime"]
        total_time = e["time"]

        # deteksi user-agent
        headers = e["request"].get("headers", [])
        user_agent = ""
        for h in headers:
            if h["name"].lower() == "user-agent":
                user_agent = h["value"]
                break

        device_type = "Mobile" if "Mobile" in user_agent or "Android" in user_agent else "Desktop"

        dns = max(timings.get("dns", 0), 0)
        connect = max(timings.get("connect", 0), 0)
        ssl = max(timings.get("ssl", 0), 0)
        wait = max(timings.get("wait", 0), 0)
        receive = max(timings.get("receive", 0), 0)

        rows.append({
            "url": url.split("?")[0],
            "device": device_type,
            "dns": dns,
            "connect": connect,
            "ssl": ssl,
            "ttfb": wait,
            "receive": receive,
            "total": total_time,
            "startedDateTime": start_time
        })

    df = pd.DataFrame(rows)
    df["startedDateTime"] = pd.to_datetime(df["startedDateTime"])
    df["end_time"] = df["startedDateTime"] + pd.to_timedelta(df["total"], unit='ms')
    return df

# ========== Fungsi Deskripsi Perbandingan ==========
def describe_comparison(df):
    summary = df.groupby("device").mean(numeric_only=True)
    if len(summary) < 2:
        return "⚠️ Hanya satu jenis device terdeteksi (Desktop atau Mobile). Tidak bisa dibandingkan."

    desktop, mobile = summary.loc["Desktop"], summary.loc["Mobile"]
    ratio = desktop["total"] / mobile["total"] if mobile["total"] > 0 else np.nan
    desc = f"""
⚡ **Rata-rata total waktu Desktop:** {desktop['total']:.2f} ms  
⚡ **Rata-rata total waktu Mobile:** {mobile['total']:.2f} ms  

👉 Secara keseluruhan, **Mobile {ratio:.2f}x lebih cepat dibanding Desktop.**

### 📊 Detail Perbedaan Tiap Komponen:
"""
    for col in ["dns", "connect", "ssl", "ttfb", "receive", "total"]:
        diff = desktop[col] - mobile[col]
        faster = "Mobile" if diff > 0 else "Desktop"
        desc += f"- {col.upper()} pada **{faster}** lebih cepat {abs(diff):.2f} ms.\n"

    return desc

# ========== Fungsi Skor Performa ==========
def performance_score(df):
    avg_total = df["total"].mean()
    if avg_total <= 300: score, grade = 95, "A"
    elif avg_total <= 600: score, grade = 85, "B"
    elif avg_total <= 1000: score, grade = 70, "C"
    elif avg_total <= 2000: score, grade = 55, "D"
    else: score, grade = 40, "E"
    return score, grade

# ========== Fungsi Bottleneck Detection ==========
def find_bottlenecks(df):
    slowest = df.sort_values("total", ascending=False).head(5)
    domain_slowest = df.copy()
    domain_slowest["domain"] = domain_slowest["url"].apply(lambda x: x.split("/")[2] if "//" in x else x)
    domain_avg = domain_slowest.groupby("domain")["total"].mean().sort_values(ascending=False).head(5)
    return slowest, domain_avg

# ========== Main Logic ==========
if uploaded_file:
    har_data = json.load(uploaded_file)
    df = extract_metrics(har_data)

    st.subheader("📋 Data Ekstraksi")
    st.dataframe(df, use_container_width=True)

    # Grafik bar perbandingan
    st.subheader("📈 Perbandingan Komponen (Desktop vs Mobile)")
    avg_df = df.groupby("device")[["dns", "connect", "ssl", "ttfb", "receive", "total"]].mean().reset_index()
    fig = px.bar(
        avg_df.melt(id_vars=["device"], value_vars=["dns", "connect", "ssl", "ttfb", "receive", "total"]),
        x="variable", y="value", color="device",
        barmode="group",
        labels={"variable": "Metrik", "value": "Waktu (ms)"},
        title="Rata-rata Waktu Komponen Desktop vs Mobile"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Waterfall chart
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

    # Skor performa
    st.subheader("🏁 Skor Performa")
    score, grade = performance_score(df)
    st.metric("Performance Score", f"{score}/100", f"Grade {grade}")

    # Bottleneck detection
    st.subheader("⚠️ Deteksi Bottleneck")
    slowest, domain_avg = find_bottlenecks(df)
    st.markdown("### ⏱️ Top 5 Request Paling Lambat:")
    st.dataframe(slowest[["url", "total", "ttfb", "receive"]])

    st.markdown("### 🌐 Domain dengan Waktu Rata-rata Paling Lambat:")
    st.dataframe(domain_avg)

    # Insight tambahan
    st.subheader("📊 Insight Tambahan")
    domain_counts = df["url"].apply(lambda x: x.split("/")[2] if "//" in x else x).value_counts()
    top_domain = domain_counts.index[0]
    st.markdown(f"🔹 Domain paling sering diakses: **{top_domain}** ({domain_counts.iloc[0]} kali).")
    st.markdown(f"🔹 Total request: **{len(df)}** entries.")

else:
    st.info("⬆️ Upload file HAR untuk memulai analisis performa.")

st.markdown("---")
st.caption("Version Dev v.1.0001")
