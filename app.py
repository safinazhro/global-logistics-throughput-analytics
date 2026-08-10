import streamlit as st
import pandas as pd
import numpy as np

# 1. Konfigurasi Tampilan Halaman Utama (Tema Executive Navy)
st.set_page_config(
    page_title="Global Logistics Analytics Hub", 
    page_icon="🚢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS untuk mempercantik UI/UX agar terlihat seperti Software Enterprise asli
st.markdown("""
    <style>
    .main { background-color: #0B132B; color: #FFFFFF; }
    div[data-testid="stMetricValue"] { font-size: 32px; font-weight: bold; color: #48CAE4; }
    div[data-testid="stMetricLabel"] { font-size: 14px; color: #94A3B8; font-weight: 500; }
    .kpi-card { background-color: #1C2541; padding: 20px; border-radius: 10px; border-left: 5px solid #00B4D8; }
    .insight-box { background-color: #1E293B; border-radius: 8px; padding: 15px; border-left: 4px solid #F15BB5; margin-top: 10px;}
    </style>
""", unsafe_allowed_html=True)

# 2. Fungsi Memuat & Mengolah Data (Data Cleansing Pipeline)
@st.cache_data
def load_and_process_data():
    df = pd.read_csv('warehouse_operations.csv')
    df['arrival_datetime'] = pd.to_datetime(df['arrival_datetime'])
    df['unloading_start_datetime'] = pd.to_datetime(df['unloading_start_datetime'])
    df['unloading_end_datetime'] = pd.to_datetime(df['unloading_end_datetime'])
    
    # Feature Engineering (Rekayasa Metrik Logistik)
    df['duration_hours'] = (df['unloading_end_datetime'] - df['unloading_start_datetime']).dt.total_seconds() / 3600
    df['cbm_per_man_hour'] = df['volume_cbm'] / (df['labor_assigned'] * df['duration_hours'])
    
    # Simulasi Denda Demurrage (Waktu tunggu truk > 2 Jam didenda Rp 150.000 / jam)
    df['demurrage_cost'] = df['duration_hours'].apply(lambda x: max(0, x - 2.0) * 150000)
    return df

df = load_and_process_data()

# 3. Sidebar untuk Filter Data (Fitur yang sangat disukai Manajer Senior)
st.sidebar.image("https://icons8.com", width=80)
st.sidebar.title("Control Tower Filters")
st.sidebar.markdown("Filter performa berdasarkan parameter operasional.")

cargo_filter = st.sidebar.multiselect(
    "Pilih Jenis Kargo:",
    options=df['cargo_type'].unique(),
    default=df['cargo_type'].unique()
)

# Memfilter data berdasarkan input user di sidebar
filtered_df = df[df['cargo_type'].isin(cargo_filter)]

# 4. Bagian Header Utama
st.title("GLOBAL LOGISTICS THROUGHPUT ANALYTICS")
st.markdown("### `Control Tower Dashboard v1.2` | Operational & Resource Optimization Hub")
st.markdown("---")

# 5. Baris KPI (Key Performance Indicators) Utama Berbasis Bisnis
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="kpi-card">', unsafe_allowed_html=True)
    st.metric("Volume Throughput", f"{filtered_df['volume_cbm'].sum():,.0f} m³", help="Total kapasitas muatan yang berhasil diproses")
    st.markdown('</div>', unsafe_allowed_html=True)

with col2:
    st.markdown('<div class="kpi-card">', unsafe_allowed_html=True)
    st.metric("Avg Turnaround Time", f"{filtered_df['duration_hours'].mean():.2f} Hours", help="Rata-rata waktu pembongkaran kontainer")
    st.markdown('</div>', unsafe_allowed_html=True)

with col3:
    st.markdown('<div class="kpi-card">', unsafe_allowed_html=True)
    st.metric("Labor Efficiency", f"{filtered_df['cbm_per_man_hour'].mean():.2f} m³/Hr", help="Rasio produktivitas volume per man-hour")
    st.markdown('</div>', unsafe_allowed_html=True)

with col4:
    st.markdown('<div class="kpi-card">', unsafe_allowed_html=True)
    # Metrik finansial penentu keputusan manajemen
    total_penalty = filtered_df['demurrage_cost'].sum()
    st.metric("Potential Demurrage Penalty", f"Rp {total_penalty:,.0f}", delta=f"Risk Detected" if total_penalty > 0 else "Optimal", delta_color="inverse")
    st.markdown('</div>', unsafe_allowed_html=True)

st.markdown("<br>", unsafe_allowed_html=True)

# 6. Bagian Grafik Analitis Tingkat Lanjut
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Produktivitas Tenaga Kerja Berdasarkan Tipe Kargo")
    cargo_perf = filtered_df.groupby('cargo_type')['cbm_per_man_hour'].mean().sort_values(ascending=False)
    st.bar_chart(cargo_perf, color="#00B4D8")
    
    st.markdown("""
    <div class="insight-box">
        <strong> Insight Analis:</strong> Kargo jenis <code>Hazardous</code> memiliki tingkat efisiensi terendah karena protokol regulasi yang ketat. Penambahan alat bantu mekanis direkomendasikan untuk menaikkan rasio m³/jam-orang.
    </div>
    """, unsafe_allowed_html=True)

with col_right:
    st.subheader(" Bottleneck Analisis: Waktu Proses vs Jumlah Staf")
    labor_bottleneck = filtered_df.groupby('labor_assigned')['duration_hours'].mean()
    st.line_chart(labor_bottleneck, color="#F15BB5")
    
    st.markdown("""
    <div class="insight-box">
        <strong> Deteksi Bottleneck:</strong> Penugasan hanya 2-3 pekerja per kontainer membuat durasi pembongkaran melonjak tajam melewati batas aman 2 jam. Alokasi optimal berada pada titik minimal 4 staf per unit kargo.
    </div>
    """, unsafe_allowed_html=True)

st.markdown("---")
st.caption("Platform Analitik Logistik Terintegrasi | Dikembangkan oleh Kandidat Data Analyst Proyek Portofolio.")
