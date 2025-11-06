import streamlit as st
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="HAR Analyzer - Desktop vs Mobile", layout="wide")

st.title("📊 HAR Analyzer - Perbandingan Desktop vs Mobile")
st.markdown("""
Upload dua file HAR (Desktop dan Mobile) untuk menganalisis performa dan membandingkan komponen waktu (DNS, Connect, SSL, TTFB, Receive, dan Total Time).
""")

# --- Upload section
col1, col2 = st.columns(2)
with col1:
    har_desktop = st.file_uploader("💻 Upload HAR Desktop", type=["har"])
with col2:
    har_mobile = st.file_uploader("📱 Upload HAR Mobile", type=["har"])

if har_desktop and har_mobile:
    def extract_timings(har_file):
        har_data = json.load(har_file)
        entries = har_data["log"]["entries"]
        timing_data = []
        for e in entries:
            t = e["timings"]
            total_time = sum(v for v in t.values() if isinstance(v, (int, float)) and v >= 0)
            timing_data.append({
                "DNS": t.get("dns", 0),
                "Connect": t.get("connect", 0),
                "SSL": t.get("ssl", 0),
                "TTFB": t.get("wait", 0),
                "Receive": t.get("receive", 0),
                "TotalTime": total_time
            })
        return pd.DataFrame(timing_data).mean()

    df_desktop = extract_timings(har_desktop)
    df_mobile = extract_timings(har_mobile)

    # Combine
    df_compare = pd.DataFrame({
        "Desktop (ms)": df_desktop,
        "Mobile (ms)": df_mobile
    })
    df_compare["Perbedaan (Desktop - Mobile)"] = df_compare["Desktop (ms)"] - df_compare["Mobile (ms)"]

    st.subheader("📋 Rata-rata Waktu Tiap Komponen")
    st.dataframe(df_compare.style.format("{:.2f}"))

    # --- Chart
    st.subheader("📈 Perbandingan Visual")
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(df_compare.index))
    ax.bar(x - 0.2, df_compare["Desktop (ms)"], width=0.4, label="Desktop")
    ax.bar(x + 0.2, df_compare["Mobile (ms)"], width=0.4, label="Mobile")
    ax.set_xticks(x)
    ax.set_xticklabels(df_compare.index)
    ax.set_ylabel("Rata-rata waktu (ms)")
    ax.legend()
    st.pyplot(fig)

    # --- Analisis otomatis
    st.subheader("🧠 Analisis & Interpretasi Otomatis")

    total_d = df_desktop["TotalTime"]
    total_m = df_mobile["TotalTime"]

    ratio = total_d / total_m if total_m else 1
    faster = "Mobile" if total_m < total_d else "Desktop"

    st.markdown(f"""
    ⚡ **Perbandingan Umum**  
    - Rata-rata total waktu **Desktop**: {total_d:.2f} ms  
    - Rata-rata total waktu **Mobile**: {total_m:.2f} ms  
    👉 Secara keseluruhan, **{faster} {ratio:.1f}× lebih cepat** dibanding lainnya.
    """)

    desc_lines = []
    for comp in df_compare.index:
        diff = df_compare.loc[comp, "Perbedaan (Desktop - Mobile)"]
        if diff > 0:
            desc_lines.append(f"- {comp} pada **Mobile** lebih cepat {abs(diff):.2f} ms dibanding Desktop.")
        elif diff < 0:
            desc_lines.append(f"- {comp} pada **Desktop** lebih cepat {abs(diff):.2f} ms dibanding Mobile.")
        else:
            desc_lines.append(f"- {comp} memiliki waktu yang hampir sama di kedua perangkat.")

    st.markdown("### 📊 Detail Perbedaan Tiap Komponen")
    st.markdown("\n".join(desc_lines))

    st.success("✅ Analisis selesai! Scroll ke atas untuk melihat grafik dan tabel lengkap.")
else:
    st.info("⬆️ Silakan upload kedua file HAR (Desktop & Mobile) untuk memulai analisis.")
