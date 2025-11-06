import streamlit as st
import json
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
import numpy as np

# =============================
# ⚙️ Fungsi: Ekstraksi HAR Data
# =============================
def parse_har(file):
    data = json.load(file)
    entries = data["log"]["entries"]

    records = []
    for e in entries:
        timings = e["timings"]
        url = e["request"]["url"]

        total_time = e["time"]
        dns = max(timings.get("dns", 0), 0)
        connect = max(timings.get("connect", 0), 0)
        ssl = max(timings.get("ssl", 0), 0)
        wait = max(timings.get("wait", 0), 0)  # TTFB
        receive = max(timings.get("receive", 0), 0)
        blocked = max(timings.get("blocked", 0), 0)

        records.append({
            "URL": url,
            "TotalTime": total_time,
            "DNS": dns,
            "Connect": connect,
            "SSL": ssl,
            "TTFB": wait,
            "Receive": receive,
            "Blocked": blocked,
        })

    df = pd.DataFrame(records)
    return df


# =============================
# ⚙️ Analisis Statistik & ML
# =============================
def analyze_performance(df):
    summary = df.describe().T[["mean", "max", "min"]].round(2)

    # Deteksi anomali dengan Isolation Forest
    features = df[["TotalTime", "DNS", "Connect", "SSL", "TTFB", "Receive"]]
    model = IsolationForest(contamination=0.05, random_state=42)
    df["anomaly"] = model.fit_predict(features)
    anomalies = df[df["anomaly"] == -1]

    dominant_phase = summary["mean"].idxmax()
    avg_total = summary.loc["TotalTime", "mean"]

    return summary, anomalies, dominant_phase, avg_total


# =============================
# 🎨 Visualisasi
# =============================
def plot_performance_comparison(df1, df2, label1, label2):
    metrics = ["DNS", "Connect", "SSL", "TTFB", "Receive", "TotalTime"]
    avg1 = df1[metrics].mean()
    avg2 = df2[metrics].mean()

    x = np.arange(len(metrics))
    width = 0.35

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - width/2, avg1, width, label=label1)
    ax.bar(x + width/2, avg2, width, label=label2)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylabel("Waktu (ms)")
    ax.set_title("Perbandingan Performansi Web")
    ax.legend()
    st.pyplot(fig)


# =============================
# 🧠 Deskripsi Perbandingan
# =============================
def generate_description(summary1, summary2, label1, label2):
    desc = []

    for metric in ["DNS", "Connect", "SSL", "TTFB", "Receive", "TotalTime"]:
        avg1 = summary1.loc[metric, "mean"]
        avg2 = summary2.loc[metric, "mean"]
        diff = avg2 - avg1
        if diff > 0:
            desc.append(f"- {metric} pada **{label2}** lebih lambat {diff:.1f} ms dibanding {label1}.")
        else:
            desc.append(f"- {metric} pada **{label2}** lebih cepat {abs(diff):.1f} ms dibanding {label1}.")

    total1 = summary1.loc["TotalTime", "mean"]
    total2 = summary2.loc["TotalTime", "mean"]

    faster = label1 if total1 < total2 else label2
    slower = label2 if faster == label1 else label1
    ratio = (max(total1, total2) / min(total1, total2))

    summary_text = f"""
    ⚡ **Perbandingan Umum**
    - Rata-rata total waktu {label1}: {total1:.2f} ms  
    - Rata-rata total waktu {label2}: {total2:.2f} ms  
    👉 Secara keseluruhan, **{faster}** {ratio:.1f}x lebih cepat dibanding **{slower}**.

    📊 **Detail Perbedaan Tiap Komponen:**
    """ + "\n".join(desc)

    return summary_text


# =============================
# 🚀 Streamlit App
# =============================
st.title("📈 Web Performance Comparison (Desktop vs Mobile)")
st.write("Unggah dua file `.har` untuk membandingkan performa situs (misalnya versi Desktop vs Mobile).")

col1, col2 = st.columns(2)
with col1:
    desktop_file = st.file_uploader("💻 File HAR - Desktop", type=["har"])
with col2:
    mobile_file = st.file_uploader("📱 File HAR - Mobile", type=["har"])

if desktop_file and mobile_file:
    st.success("✅ Kedua file berhasil diunggah!")

    df_desktop = parse_har(desktop_file)
    df_mobile = parse_har(mobile_file)

    # Analisis masing-masing
    summary_d, anomalies_d, dominant_d, avg_d = analyze_performance(df_desktop)
    summary_m, anomalies_m, dominant_m, avg_m = analyze_performance(df_mobile)

    st.subheader("📋 Ringkasan Statistik")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 💻 Desktop")
        st.dataframe(summary_d)
    with col2:
        st.markdown("### 📱 Mobile")
        st.dataframe(summary_m)

    st.subheader("📊 Grafik Perbandingan")
    plot_performance_comparison(df_desktop, df_mobile, "Desktop", "Mobile")

    st.subheader("🧠 Analisis & Interpretasi")
    description = generate_description(summary_d, summary_m, "Desktop", "Mobile")
    st.markdown(description)

    st.subheader("🚨 Deteksi Anomali (Outlier)")
    st.write("Request dengan waktu tidak normal (berpotensi bottleneck).")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 💻 Desktop Anomali")
        st.dataframe(anomalies_d[["URL", "TotalTime", "TTFB", "Receive"]].head(10))
    with col2:
        st.markdown("### 📱 Mobile Anomali")
        st.dataframe(anomalies_m[["URL", "TotalTime", "TTFB", "Receive"]].head(10))

else:
    st.info("Unggah dua file HAR (desktop & mobile) untuk memulai analisis.")
