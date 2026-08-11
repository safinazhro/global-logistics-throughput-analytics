"""
app.py

Global Logistics Throughput & Labor Analytics

Dashboard Streamlit interaktif untuk menganalisis bottleneck operasional pada
fasilitas warehouse logistik: alokasi tenaga kerja, dwell time, dan denda
demurrage lintas shift, zona, dan jenis kargo.

Struktur dashboard (4 halaman, dipilih lewat sidebar):
1. Overview
2. Shift and Labor Analysis
3. Cargo Risk Breakdown
4. Financial Impact and Recommendation

Catatan teknis:
- Tidak menggunakan HTML/CSS kustom (st.markdown selalu tanpa
  unsafe_allow_html) sesuai kebutuhan stabilitas deployment.
- Menggunakan parameter width="stretch" pada seluruh elemen lebar-penuh
  (st.dataframe, st.plotly_chart) karena use_container_width sudah dihapus
  dari versi Streamlit terbaru.
- st.metric dipanggil hanya dengan argumen yang didukung versi stabil
  saat ini (label, value, delta, delta_color, help).
- Tampilan visual profesional diatur lewat .streamlit/config.toml (tema resmi
  Streamlit) dan palet warna konsisten pada seluruh chart Plotly, bukan lewat
  CSS/HTML kustom.
- page_icon menggunakan Material icon (":material/...:"), bukan karakter
  emoji literal.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st


# KONFIGURASI HALAMAN

st.set_page_config(
    page_title="Global Logistics Throughput and Labor Analytics",
    page_icon=":material/local_shipping:",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = "warehouse_operations.csv"

SHIFT_ORDER = [
    "Shift 1 (06:00-14:00)",
    "Shift 2 (14:00-22:00)",
    "Shift 3 (22:00-06:00)",
]

CARGO_ORDER = ["Standard Dry", "Refrigerated", "Hazardous"]

# PALET WARNA PROFESIONAL (konsisten di seluruh chart)
# Skema warna terinspirasi industri maritim/logistik. Shift 2 sengaja diberi
# warna aksen (merah bata) di seluruh dashboard karena secara konsisten
# menjadi shift dengan kontribusi bottleneck tertinggi -- pewarnaan ini
# membantu audiens langsung mengenali pola tanpa harus membaca angka.

COLOR_NAVY = "#0A2540"
COLOR_STEEL_BLUE = "#1B6B93"
COLOR_TEAL = "#2A9D8F"
COLOR_SLATE_GRAY = "#6C757D"
COLOR_AMBER = "#E9A93B"
COLOR_ALERT_RED = "#C1443C"

SHIFT_COLOR_MAP = {
    "Shift 1 (06:00-14:00)": COLOR_STEEL_BLUE,
    "Shift 2 (14:00-22:00)": COLOR_ALERT_RED,
    "Shift 3 (22:00-06:00)": COLOR_SLATE_GRAY,
}

CARGO_COLOR_MAP = {
    "Standard Dry": COLOR_SLATE_GRAY,
    "Refrigerated": COLOR_STEEL_BLUE,
    "Hazardous": COLOR_AMBER,
}

SEQUENTIAL_BLUE_SCALE = [COLOR_NAVY, COLOR_STEEL_BLUE, "#A9C6D8", "#F4F6F8"][::-1]

PLOTLY_LAYOUT_DEFAULTS = dict(
    font=dict(family="Arial, sans-serif", color=COLOR_NAVY, size=13),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)


def apply_professional_layout(fig):
    """Menerapkan gaya visual konsisten pada semua chart Plotly di dashboard."""
    fig.update_layout(**PLOTLY_LAYOUT_DEFAULTS)
    return fig


# DATA LOADING

@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        parse_dates=[
            "date",
            "truck_arrival_time",
            "gate_in_time",
            "processing_start_time",
            "processing_end_time",
            "gate_out_time",
        ],
    )
    return df


try:
    raw_df = load_data(DATA_PATH)
except FileNotFoundError:
    st.error(
        f"File '{DATA_PATH}' tidak ditemukan. Pastikan file tersebut berada "
        "di folder yang sama dengan app.py, atau jalankan generate_dataset.py "
        "terlebih dahulu."
    )
    st.stop()


# SIDEBAR: NAVIGASI DAN FILTER GLOBAL

st.sidebar.markdown("### Global Logistics Throughput and Labor Analytics")
st.sidebar.caption("Business Data Analytics Portfolio Project")
st.sidebar.divider()

page = st.sidebar.radio(
    "Navigasi halaman",
    options=[
        "Overview",
        "Shift and Labor Analysis",
        "Cargo Risk Breakdown",
        "Financial Impact and Recommendation",
    ],
)

st.sidebar.divider()
st.sidebar.subheader("Filter Data")

min_date = raw_df["date"].min().date()
max_date = raw_df["date"].max().date()

date_range = st.sidebar.date_input(
    "Rentang tanggal",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

selected_shifts = st.sidebar.multiselect(
    "Shift",
    options=SHIFT_ORDER,
    default=SHIFT_ORDER,
)

selected_zones = st.sidebar.multiselect(
    "Zona gudang",
    options=sorted(raw_df["warehouse_zone"].unique().tolist()),
    default=sorted(raw_df["warehouse_zone"].unique().tolist()),
)

selected_cargo = st.sidebar.multiselect(
    "Jenis kargo",
    options=CARGO_ORDER,
    default=CARGO_ORDER,
)

# Normalisasi date_input: bisa berupa satu tanggal atau rentang
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered_df = raw_df[
    (raw_df["date"].dt.date >= start_date)
    & (raw_df["date"].dt.date <= end_date)
    & (raw_df["shift"].isin(selected_shifts))
    & (raw_df["warehouse_zone"].isin(selected_zones))
    & (raw_df["cargo_type"].isin(selected_cargo))
].copy()

if filtered_df.empty:
    st.warning("Tidak ada data yang cocok dengan filter yang dipilih. Silakan ubah filter di sidebar.")
    st.stop()


# FUNGSI BANTUAN

def format_usd(value: float) -> str:
    return f"USD {value:,.0f}"


def order_categorical(df: pd.DataFrame, column: str, order: list[str]) -> pd.DataFrame:
    present_order = [item for item in order if item in df[column].unique()]
    df = df.copy()
    df[column] = pd.Categorical(df[column], categories=present_order, ordered=True)
    return df.sort_values(column)


# HALAMAN 1: OVERVIEW

if page == "Overview":
    st.title("Overview")
    st.caption(
        "Ringkasan kinerja operasional fasilitas warehouse berdasarkan filter "
        "yang dipilih di sidebar."
    )

    total_trucks = len(filtered_df)
    total_demurrage = filtered_df["demurrage_penalty_usd"].sum()
    avg_dwell = filtered_df["dwell_time_hours"].mean()
    pct_affected = (filtered_df["demurrage_penalty_usd"] > 0).mean() * 100

    kpi_data = [
        ("Total Truk Diproses", f"{total_trucks:,}"),
        ("Total Denda Demurrage", format_usd(total_demurrage)),
        ("Rata-rata Dwell Time", f"{avg_dwell:.2f} jam"),
        ("Persentase Pengiriman Terdampak Denda", f"{pct_affected:.1f}%"),
    ]
    kpi_cols = st.columns(4)
    for col, (label, value) in zip(kpi_cols, kpi_data):
        with col:
            with st.container(border=True):
                st.metric(label, value)

    st.divider()

    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("Volume Truk per Shift")
        volume_by_shift = (
            filtered_df.groupby("shift", observed=True).size().reset_index(name="total_trucks")
        )
        volume_by_shift = order_categorical(volume_by_shift, "shift", SHIFT_ORDER)
        fig_volume = px.bar(
            volume_by_shift,
            x="shift",
            y="total_trucks",
            color="shift",
            color_discrete_map=SHIFT_COLOR_MAP,
            labels={"shift": "Shift", "total_trucks": "Jumlah Truk"},
        )
        fig_volume.update_layout(showlegend=False)
        apply_professional_layout(fig_volume)
        st.plotly_chart(fig_volume, width="stretch")

    with right_col:
        st.subheader("Tren Denda Demurrage Harian")
        daily_demurrage = (
            filtered_df.groupby(filtered_df["date"].dt.date)["demurrage_penalty_usd"]
            .sum()
            .reset_index()
        )
        daily_demurrage.columns = ["date", "demurrage_penalty_usd"]
        fig_trend = px.line(
            daily_demurrage,
            x="date",
            y="demurrage_penalty_usd",
            labels={"date": "Tanggal", "demurrage_penalty_usd": "Total Denda (USD)"},
            color_discrete_sequence=[COLOR_STEEL_BLUE],
        )
        apply_professional_layout(fig_trend)
        st.plotly_chart(fig_trend, width="stretch")

    st.subheader("Distribusi Kargo yang Diproses")
    cargo_dist = (
        filtered_df.groupby("cargo_type", observed=True).size().reset_index(name="total_shipments")
    )
    fig_cargo_dist = px.pie(
        cargo_dist,
        names="cargo_type",
        values="total_shipments",
        color="cargo_type",
        color_discrete_map=CARGO_COLOR_MAP,
        hole=0.4,
    )
    st.plotly_chart(fig_cargo_dist, width="stretch")


# HALAMAN 2: SHIFT AND LABOR ANALYSIS

elif page == "Shift and Labor Analysis":
    st.title("Shift and Labor Analysis")
    st.caption(
        "Menyelidiki apakah alokasi tenaga kerja saat ini proporsional dengan "
        "beban operasional pada setiap shift."
    )

    shift_summary = (
        filtered_df.groupby("shift", observed=True)
        .agg(
            total_trucks=("record_id", "count"),
            avg_labor_assigned=("labor_assigned_shift", "mean"),
            avg_congestion_index=("shift_congestion_index", "mean"),
            avg_dwell_hours=("dwell_time_hours", "mean"),
            total_demurrage_usd=("demurrage_penalty_usd", "sum"),
        )
        .reset_index()
    )
    shift_summary["trucks_per_worker"] = (
        shift_summary["total_trucks"] / shift_summary["avg_labor_assigned"]
    )
    shift_summary = order_categorical(shift_summary, "shift", SHIFT_ORDER)

    st.subheader("Ringkasan Beban Kerja per Shift")
    display_summary = shift_summary.copy()
    display_summary["avg_labor_assigned"] = display_summary["avg_labor_assigned"].round(1)
    display_summary["avg_congestion_index"] = display_summary["avg_congestion_index"].round(2)
    display_summary["avg_dwell_hours"] = display_summary["avg_dwell_hours"].round(2)
    display_summary["trucks_per_worker"] = display_summary["trucks_per_worker"].round(2)
    display_summary["total_demurrage_usd"] = display_summary["total_demurrage_usd"].round(2)
    st.dataframe(display_summary, width="stretch", hide_index=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Truk per Pekerja (Indikator Beban Kerja)")
        fig_ratio = px.bar(
            shift_summary,
            x="shift",
            y="trucks_per_worker",
            color="shift",
            color_discrete_map=SHIFT_COLOR_MAP,
            labels={"shift": "Shift", "trucks_per_worker": "Truk per Pekerja"},
        )
        fig_ratio.update_layout(showlegend=False)
        apply_professional_layout(fig_ratio)
        st.plotly_chart(fig_ratio, width="stretch")

    with col2:
        st.subheader("Indeks Kongesti Rata-rata per Shift")
        fig_congestion = px.bar(
            shift_summary,
            x="shift",
            y="avg_congestion_index",
            color="shift",
            color_discrete_map=SHIFT_COLOR_MAP,
            labels={"shift": "Shift", "avg_congestion_index": "Indeks Kongesti"},
        )
        fig_congestion.update_layout(showlegend=False)
        fig_congestion.add_hline(
            y=1.0,
            line_dash="dash",
            line_color=COLOR_SLATE_GRAY,
            annotation_text="Batas ideal (kapasitas seimbang)",
        )
        apply_professional_layout(fig_congestion)
        st.plotly_chart(fig_congestion, width="stretch")

    st.subheader("Hubungan Indeks Kongesti terhadap Dwell Time")
    sample_size = min(3000, len(filtered_df))
    scatter_sample = filtered_df.sample(sample_size, random_state=42)
    fig_scatter = px.scatter(
        scatter_sample,
        x="shift_congestion_index",
        y="dwell_time_hours",
        color="shift",
        color_discrete_map=SHIFT_COLOR_MAP,
        opacity=0.5,
        labels={
            "shift_congestion_index": "Indeks Kongesti",
            "dwell_time_hours": "Dwell Time (Jam)",
        },
    )
    apply_professional_layout(fig_scatter)
    st.plotly_chart(fig_scatter, width="stretch")

    st.subheader("Distribusi Dwell Time per Shift")
    fig_box = px.box(
        order_categorical(filtered_df, "shift", SHIFT_ORDER),
        x="shift",
        y="dwell_time_hours",
        color="shift",
        color_discrete_map=SHIFT_COLOR_MAP,
        labels={"shift": "Shift", "dwell_time_hours": "Dwell Time (Jam)"},
    )
    fig_box.update_layout(showlegend=False)
    apply_professional_layout(fig_box)
    st.plotly_chart(fig_box, width="stretch")


# HALAMAN 3: CARGO RISK BREAKDOWN

elif page == "Cargo Risk Breakdown":
    st.title("Cargo Risk Breakdown")
    st.caption(
        "Menganalisis tingkat risiko keterlambatan dan denda berdasarkan jenis "
        "kargo yang ditangani."
    )

    cargo_summary = (
        filtered_df.groupby("cargo_type", observed=True)
        .agg(
            total_shipments=("record_id", "count"),
            avg_dwell_hours=("dwell_time_hours", "mean"),
            avg_processing_minutes=("processing_duration_minutes", "mean"),
            total_demurrage_usd=("demurrage_penalty_usd", "sum"),
            avg_demurrage_usd=("demurrage_penalty_usd", "mean"),
        )
        .reset_index()
    )
    cargo_summary["pct_shipments_delayed"] = (
        filtered_df.groupby("cargo_type", observed=True)["demurrage_penalty_usd"]
        .apply(lambda x: (x > 0).mean() * 100)
        .values
    )
    cargo_summary = order_categorical(cargo_summary, "cargo_type", CARGO_ORDER)

    display_cargo = cargo_summary.copy()
    for col in ["avg_dwell_hours", "avg_processing_minutes", "total_demurrage_usd", "avg_demurrage_usd", "pct_shipments_delayed"]:
        display_cargo[col] = display_cargo[col].round(2)
    st.dataframe(display_cargo, width="stretch", hide_index=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Total Denda per Jenis Kargo")
        fig_total_demurrage = px.bar(
            cargo_summary,
            x="cargo_type",
            y="total_demurrage_usd",
            color="cargo_type",
            color_discrete_map=CARGO_COLOR_MAP,
            labels={"cargo_type": "Jenis Kargo", "total_demurrage_usd": "Total Denda (USD)"},
        )
        fig_total_demurrage.update_layout(showlegend=False)
        apply_professional_layout(fig_total_demurrage)
        st.plotly_chart(fig_total_demurrage, width="stretch")

    with col2:
        st.subheader("Persentase Pengiriman Terdampak Denda")
        fig_pct_delayed = px.bar(
            cargo_summary,
            x="cargo_type",
            y="pct_shipments_delayed",
            color="cargo_type",
            color_discrete_map=CARGO_COLOR_MAP,
            labels={"cargo_type": "Jenis Kargo", "pct_shipments_delayed": "Persentase Terdampak (%)"},
        )
        fig_pct_delayed.update_layout(showlegend=False)
        apply_professional_layout(fig_pct_delayed)
        st.plotly_chart(fig_pct_delayed, width="stretch")

    st.subheader("Demurrage per Kombinasi Shift dan Jenis Kargo")
    heatmap_data = filtered_df.pivot_table(
        index="cargo_type",
        columns="shift",
        values="demurrage_penalty_usd",
        aggfunc="mean",
    )
    heatmap_data = heatmap_data.reindex(
        index=[c for c in CARGO_ORDER if c in heatmap_data.index],
        columns=[s for s in SHIFT_ORDER if s in heatmap_data.columns],
    )
    fig_heatmap = px.imshow(
        heatmap_data,
        text_auto=".1f",
        labels=dict(x="Shift", y="Jenis Kargo", color="Rata-rata Denda (USD)"),
        aspect="auto",
        color_continuous_scale=SEQUENTIAL_BLUE_SCALE,
    )
    apply_professional_layout(fig_heatmap)
    st.plotly_chart(fig_heatmap, width="stretch")


# HALAMAN 4: FINANCIAL IMPACT AND RECOMMENDATION

elif page == "Financial Impact and Recommendation":
    st.title("Financial Impact and Recommendation")
    st.caption(
        "Estimasi dampak finansial dari bottleneck operasional dan simulasi "
        "sederhana untuk mendukung rekomendasi kebijakan staffing."
    )

    total_demurrage = filtered_df["demurrage_penalty_usd"].sum()
    num_days = max(1, (filtered_df["date"].max() - filtered_df["date"].min()).days + 1)
    daily_avg_demurrage = total_demurrage / num_days
    projected_annual = daily_avg_demurrage * 365

    top_kpi_data = [
        ("Total Denda pada Periode Terpilih", format_usd(total_demurrage)),
        ("Rata-rata Denda per Hari", format_usd(daily_avg_demurrage)),
        ("Proyeksi Denda per Tahun", format_usd(projected_annual)),
    ]
    top_kpi_cols = st.columns(3)
    for col, (label, value) in zip(top_kpi_cols, top_kpi_data):
        with col:
            with st.container(border=True):
                st.metric(label, value)

    st.divider()
    st.subheader("Simulasi: Dampak Penambahan Tenaga Kerja pada Shift Tertentu")
    st.write(
        "Simulasi ini bersifat estimasi arah (directional estimate), berguna untuk "
        "mendukung diskusi kebijakan staffing, bukan sebagai angka final operasional."
    )

    sim_shift = st.selectbox("Pilih shift yang ingin disimulasikan", options=SHIFT_ORDER, index=1)
    labor_increase_pct = st.slider(
        "Persentase penambahan tenaga kerja",
        min_value=0,
        max_value=100,
        value=20,
        step=5,
    )

    sim_df = filtered_df[filtered_df["shift"] == sim_shift].copy()

    if sim_df.empty or labor_increase_pct == 0:
        st.info("Pilih shift dengan data tersedia dan persentase penambahan lebih dari 0 persen untuk melihat hasil simulasi.")
    else:
        labor_factor = 1 + (labor_increase_pct / 100)
        sim_df["new_labor_assigned"] = sim_df["labor_assigned_shift"] * labor_factor
        sim_df["new_congestion_index"] = (
            sim_df["shift_congestion_index"] * sim_df["labor_assigned_shift"] / sim_df["new_labor_assigned"]
        )

        cargo_free_time = {"Standard Dry": 4.0, "Refrigerated": 3.0, "Hazardous": 3.5}
        cargo_demurrage_rate = {"Standard Dry": 15.0, "Refrigerated": 40.0, "Hazardous": 32.0}

        old_multiplier = 1.0 + (sim_df["shift_congestion_index"] - 1.0).clip(lower=0) * 0.5
        new_multiplier = 1.0 + (sim_df["new_congestion_index"] - 1.0).clip(lower=0) * 0.5
        ratio = new_multiplier / old_multiplier.replace(0, np.nan)
        ratio = ratio.fillna(1.0)

        sim_df["new_dwell_time_hours"] = sim_df["dwell_time_hours"] * ratio
        sim_df["free_time_allowance"] = sim_df["cargo_type"].map(cargo_free_time)
        sim_df["demurrage_rate"] = sim_df["cargo_type"].map(cargo_demurrage_rate)
        sim_df["new_excess_hours"] = (
            sim_df["new_dwell_time_hours"] - sim_df["free_time_allowance"]
        ).clip(lower=0)
        sim_df["new_demurrage_usd"] = sim_df["new_excess_hours"] * sim_df["demurrage_rate"]

        old_total = sim_df["demurrage_penalty_usd"].sum()
        new_total = sim_df["new_demurrage_usd"].sum()
        savings = old_total - new_total
        savings_pct = (savings / old_total * 100) if old_total > 0 else 0.0

        sim_kpi_data = [
            (f"Denda Saat Ini ({sim_shift})", format_usd(old_total), None),
            ("Estimasi Denda Setelah Penambahan Tenaga Kerja", format_usd(new_total), None),
            ("Estimasi Penghematan", format_usd(savings), f"{savings_pct:.1f}%"),
        ]
        sim_kpi_cols = st.columns(3)
        for col, (label, value, delta) in zip(sim_kpi_cols, sim_kpi_data):
            with col:
                with st.container(border=True):
                    st.metric(label, value, delta=delta)

        comparison_df = pd.DataFrame(
            {
                "Skenario": ["Kondisi Saat Ini", "Setelah Penambahan Tenaga Kerja"],
                "Total Denda (USD)": [old_total, new_total],
            }
        )
        fig_comparison = px.bar(
            comparison_df,
            x="Skenario",
            y="Total Denda (USD)",
            color="Skenario",
            color_discrete_sequence=[COLOR_ALERT_RED, COLOR_TEAL],
        )
        fig_comparison.update_layout(showlegend=False)
        apply_professional_layout(fig_comparison)
        st.plotly_chart(fig_comparison, width="stretch")

    st.divider()
    st.subheader("Ringkasan Rekomendasi")
    st.write(
        "Berdasarkan analisis pada halaman sebelumnya, rekomendasi utama adalah "
        "melakukan rebalancing alokasi tenaga kerja, dengan prioritas pada shift "
        "dengan indeks kongesti tertinggi dan pada penanganan kargo Refrigerated "
        "serta Hazardous yang membutuhkan waktu proses lebih lama. Langkah ini "
        "berpotensi menurunkan denda demurrage secara signifikan tanpa memerlukan "
        "penambahan kapasitas gudang secara fisik."
    )
