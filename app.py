import streamlit as st
import pandas as pd
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest

st.set_page_config(page_title="HAR Performance Analyzer", layout="wide")

st.title("📊 HAR Performance Analyzer (Machine Learning Edition)")
st.markdown("Upload file `.har` dari Chrome DevTools untuk menganalisis performa request secara detail.")

uploaded_file = st.file_uploader("Unggah file HAR", type=["har"])

if uploaded_file:
    try:
        har_data = json.load(uploaded_file)
        entries = har_data["log"]["entries"]

        rows = []
        for e in entries:
            t = e["timings"]
            url = e["request"]["url"]
            domain = url.split("/")[2] if "://" in url else url

            dns = max(t.get("dns", 0), 0)
            connect = max(t.get("connect", 0), 0)
            ssl = max(t.get("ssl", 0), 0)
            send = max(t.get("send", 0), 0)
            wait = max(t.get("wait", 0), 0)
            receive = max(t.get("receive", 0), 0)
            total = dns + connect + ssl + send + wait + receive

            rows.append({
                "domain": domain,
                "dns": dns,
                "connect": connect,
                "ssl": ssl,
                "send": send,
                "ttfb": wait,
                "receive": receive,
                "total": total,
                "method": e["request"]["method"],
                "status": e["response"]["status"],
                "mimeType": e["response"]["content"].get("mimeType", "")
            })

        df = pd.DataFrame(rows)

        st.subheader("📋 Preview Data")
        st.dataframe(df.head(20))

        # --- Analisis ---
        X = df[["dns", "connect", "ssl", "ttfb", "receive", "total"]].fillna(0)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        kmeans = KMeans(n_clusters=3, random_state=42, n_init="auto")
        df["cluster"] = kmeans.fit_predict(X_scaled)

        iso = IsolationForest(contamination=0.1, random_state=42)
        df["anomaly"] = iso.fit_predict(X_scaled)
        df["anomaly"] = df["anomaly"].map({1: "Normal", -1: "Anomali"})

        # --- Statistik umum ---
        st.subheader("📈 Statistik Rata-rata per Cluster")
        cluster_stats = df.groupby("cluster")[["dns", "connect", "ssl", "ttfb", "receive", "total"]].mean()
        st.dataframe(cluster_stats)

        fig, ax = plt.subplots(figsize=(8,4))
        cluster_stats.plot(kind="bar", ax=ax)
        plt.title("Rata-rata Waktu Tiap Cluster (ms)")
        plt.ylabel("Waktu (ms)")
        plt.xlabel("Cluster")
        st.pyplot(fig)

        # --- Scatter plot ---
        st.subheader("📉 Scatter Plot: TTFB vs Total Load")
        fig2, ax2 = plt.subplots(figsize=(8,5))
        scatter = ax2.scatter(df["ttfb"], df["total"], 
                              c=(df["anomaly"]=="Anomali"), cmap="coolwarm", alpha=0.7)
        ax2.set_xlabel("TTFB (ms)")
        ax2.set_ylabel("Total Load (ms)")
        plt.title("Deteksi Anomali Berdasarkan TTFB vs Total Load")
        st.pyplot(fig2)

        # --- Deteksi anomali ---
        st.subheader("🚨 Request dengan Performa Buruk (Anomali)")
        st.dataframe(df[df["anomaly"]=="Anomali"][["domain", "ttfb", "total", "status", "mimeType"]])

        # --- Unduh hasil ---
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Unduh Hasil Analisis (CSV)", csv, "har_analysis_result.csv", "text/csv")

        st.success("✅ Analisis selesai! Gunakan grafik dan tabel di atas untuk evaluasi performa request.")

    except Exception as e:
        st.error(f"Gagal membaca file HAR: {e}")
else:
    st.info("Unggah file `.har` untuk memulai analisis.")
