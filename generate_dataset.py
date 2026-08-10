"""
generate_dataset.py

Global Logistics Throughput & Labor Analytics
------------------------------------------------
Skrip ini menghasilkan dataset sintetis operasional warehouse logistik
(warehouse_operations.csv) yang meniru pola dunia nyata pada fasilitas
bongkar-muat kargo, termasuk bottleneck tersembunyi pada alokasi tenaga
kerja lintas shift yang berdampak pada dwell time dan denda demurrage.

Logika bisnis yang disimulasikan:
1. Tiga shift kerja dengan volume truk dan alokasi tenaga kerja yang
   TIDAK proporsional (Shift 2 paling padat, tetapi paling sedikit staf).
2. Tiga jenis kargo (Standard Dry, Refrigerated, Hazardous) dengan
   kebutuhan tenaga kerja dan waktu proses yang berbeda.
3. Tingkat kongesti per shift-hari dihitung dari rasio kebutuhan tenaga
   kerja terhadap tenaga kerja yang tersedia, yang kemudian memperlambat
   waktu proses dan antrean gerbang secara realistis (bukan acak murni).
4. Denda demurrage dihitung otomatis ketika dwell time melebihi batas
   waktu bebas (free time allowance) sesuai jenis kargo.

Menjalankan skrip ini akan membuat file: warehouse_operations.csv
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# 1. KONFIGURASI SIMULASI
# ---------------------------------------------------------------------------

RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

START_DATE = datetime(2026, 1, 1)
NUM_DAYS = 181  # 1 Januari - 30 Juni 2026

WAREHOUSE_ZONES = ["Zone A", "Zone B", "Zone C"]

SHIFTS = ["Shift 1 (06:00-14:00)", "Shift 2 (14:00-22:00)", "Shift 3 (22:00-06:00)"]
SHIFT_START_HOUR = {
    "Shift 1 (06:00-14:00)": 6,
    "Shift 2 (14:00-22:00)": 14,
    "Shift 3 (22:00-06:00)": 22,
}

# Proporsi volume truk per shift (Shift 2 sengaja dibuat paling padat)
SHIFT_VOLUME_WEIGHT = {
    "Shift 1 (06:00-14:00)": 0.33,
    "Shift 2 (14:00-22:00)": 0.42,
    "Shift 3 (22:00-06:00)": 0.25,
}

# Tenaga kerja yang dialokasikan per shift (Shift 2 sengaja understaffed).
# Inilah akar masalah tersembunyi yang harus "ditemukan" pada tahap EDA.
SHIFT_LABOR_ASSIGNED = {
    "Shift 1 (06:00-14:00)": 21,
    "Shift 2 (14:00-22:00)": 16,
    "Shift 3 (22:00-06:00)": 18,
}

CARGO_TYPES = ["Standard Dry", "Refrigerated", "Hazardous"]
CARGO_TYPE_PROBABILITY = [0.62, 0.26, 0.12]

# Kebutuhan "unit tenaga kerja" per truk berdasarkan jenis kargo
CARGO_LABOR_DEMAND_UNIT = {
    "Standard Dry": 1.0,
    "Refrigerated": 1.8,
    "Hazardous": 2.3,
}

# Waktu proses dasar (menit) sebelum efek kongesti
CARGO_BASE_PROCESSING_MINUTES = {
    "Standard Dry": 40,
    "Refrigerated": 70,
    "Hazardous": 85,
}

# Batas waktu bebas denda (jam) sesuai kontrak per jenis kargo
CARGO_FREE_TIME_ALLOWANCE_HOURS = {
    "Standard Dry": 4.0,
    "Refrigerated": 3.0,
    "Hazardous": 3.5,
}

# Tarif denda demurrage (USD per jam kelebihan waktu)
CARGO_DEMURRAGE_RATE_USD_PER_HOUR = {
    "Standard Dry": 15.0,
    "Refrigerated": 40.0,
    "Hazardous": 32.0,
}

TRUCKING_COMPANIES = [
    "Nusantara Freight Co",
    "Trans Java Logistics",
    "Borneo Cargo Lines",
    "Katulistiwa Hauliers",
    "Pelita Muatan Darat",
    "Samudra Land Transport",
]

DAILY_TRUCK_VOLUME_RANGE = (60, 95)  # total truk per hari, seluruh shift


# ---------------------------------------------------------------------------
# 2. FUNGSI BANTUAN
# ---------------------------------------------------------------------------

def generate_shift_congestion_index(shift: str, cargo_samples: np.ndarray) -> float:
    """
    Menghitung indeks kongesti untuk satu shift pada satu hari.

    Indeks > 1 berarti total kebutuhan tenaga kerja melebihi tenaga kerja
    yang tersedia pada shift tersebut (bottleneck aktif).
    """
    labor_demand_total = sum(CARGO_LABOR_DEMAND_UNIT[c] for c in cargo_samples)
    labor_available = SHIFT_LABOR_ASSIGNED[shift]
    if labor_available == 0:
        return 5.0
    return labor_demand_total / labor_available


def sample_cargo_types(n: int) -> np.ndarray:
    return rng.choice(CARGO_TYPES, size=n, p=CARGO_TYPE_PROBABILITY)


def build_records_for_shift(current_date: datetime, shift: str, n_trucks: int, dock_pool: list) -> list[dict]:
    records = []

    cargo_samples = sample_cargo_types(n_trucks)
    congestion_index = generate_shift_congestion_index(shift, cargo_samples)

    shift_start = current_date + timedelta(hours=SHIFT_START_HOUR[shift])

    for i in range(n_trucks):
        cargo_type = cargo_samples[i]
        zone = rng.choice(WAREHOUSE_ZONES)

        # Kedatangan truk tersebar acak sepanjang durasi shift (8 jam)
        arrival_offset_minutes = rng.uniform(0, 8 * 60)
        truck_arrival_time = shift_start + timedelta(minutes=arrival_offset_minutes)

        # Waktu antrean di gerbang, dipengaruhi tingkat kongesti shift
        base_queue_wait = rng.gamma(shape=2.2, scale=8.0)  # menit, distribusi realistis
        congestion_penalty_queue = max(0.0, congestion_index - 1.0) * rng.uniform(12, 28)
        queue_wait_minutes = base_queue_wait + congestion_penalty_queue
        gate_in_time = truck_arrival_time + timedelta(minutes=queue_wait_minutes)

        # Jeda penugasan dermaga (dock assignment)
        dock_assignment_delay = rng.uniform(2, 15)
        processing_start_time = gate_in_time + timedelta(minutes=dock_assignment_delay)

        # Waktu proses dipengaruhi jenis kargo + efek kongesti tenaga kerja
        base_minutes = CARGO_BASE_PROCESSING_MINUTES[cargo_type]
        congestion_multiplier = 1.0 + max(0.0, congestion_index - 1.0) * 0.5
        noise = rng.normal(loc=1.0, scale=0.2)
        processing_duration_minutes = max(10.0, base_minutes * congestion_multiplier * noise)

        processing_end_time = processing_start_time + timedelta(minutes=processing_duration_minutes)

        # Jeda keluar gerbang setelah proses selesai
        exit_buffer_minutes = rng.uniform(5, 20)
        gate_out_time = processing_end_time + timedelta(minutes=exit_buffer_minutes)

        dwell_time_hours = (gate_out_time - gate_in_time).total_seconds() / 3600.0

        free_time_allowance = CARGO_FREE_TIME_ALLOWANCE_HOURS[cargo_type]
        excess_hours = max(0.0, dwell_time_hours - free_time_allowance)
        demurrage_penalty_usd = round(excess_hours * CARGO_DEMURRAGE_RATE_USD_PER_HOUR[cargo_type], 2)

        cargo_weight_kg = float(np.round(rng.normal(loc=8500, scale=2200), 1))
        cargo_weight_kg = max(500.0, cargo_weight_kg)
        pallet_count = int(max(1, rng.poisson(lam=18)))

        dock_number = rng.choice(dock_pool)

        records.append(
            {
                "date": current_date.strftime("%Y-%m-%d"),
                "shift": shift,
                "warehouse_zone": zone,
                "cargo_type": cargo_type,
                "truck_id": f"TRK-{rng.integers(100000, 999999)}",
                "trucking_company": rng.choice(TRUCKING_COMPANIES),
                "truck_arrival_time": truck_arrival_time.strftime("%Y-%m-%d %H:%M:%S"),
                "gate_in_time": gate_in_time.strftime("%Y-%m-%d %H:%M:%S"),
                "dock_number": dock_number,
                "processing_start_time": processing_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "processing_end_time": processing_end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "gate_out_time": gate_out_time.strftime("%Y-%m-%d %H:%M:%S"),
                "labor_assigned_shift": SHIFT_LABOR_ASSIGNED[shift],
                "shift_congestion_index": round(congestion_index, 3),
                "cargo_weight_kg": cargo_weight_kg,
                "pallet_count": pallet_count,
                "queue_wait_minutes": round(queue_wait_minutes, 2),
                "processing_duration_minutes": round(processing_duration_minutes, 2),
                "dwell_time_hours": round(dwell_time_hours, 3),
                "free_time_allowance_hours": free_time_allowance,
                "demurrage_penalty_usd": demurrage_penalty_usd,
            }
        )

    return records


# ---------------------------------------------------------------------------
# 3. LOOP UTAMA SIMULASI
# ---------------------------------------------------------------------------

def generate_dataset() -> pd.DataFrame:
    all_records: list[dict] = []
    dock_pool = [f"D-{n:02d}" for n in range(1, 13)]

    for day_offset in range(NUM_DAYS):
        current_date = START_DATE + timedelta(days=day_offset)

        daily_total_trucks = rng.integers(DAILY_TRUCK_VOLUME_RANGE[0], DAILY_TRUCK_VOLUME_RANGE[1])

        for shift in SHIFTS:
            n_trucks_shift = int(round(daily_total_trucks * SHIFT_VOLUME_WEIGHT[shift]))
            n_trucks_shift = max(1, n_trucks_shift)

            shift_records = build_records_for_shift(current_date, shift, n_trucks_shift, dock_pool)
            all_records.extend(shift_records)

    df = pd.DataFrame(all_records)
    df.insert(0, "record_id", range(1, len(df) + 1))

    # Menyuntikkan sedikit missing value pada kolom non-kritikal agar
    # dataset terasa realistis (data operasional dunia nyata jarang bersih 100%).
    missing_mask_company = rng.random(len(df)) < 0.015
    df.loc[missing_mask_company, "trucking_company"] = np.nan

    missing_mask_weight = rng.random(len(df)) < 0.01
    df.loc[missing_mask_weight, "cargo_weight_kg"] = np.nan

    return df


if __name__ == "__main__":
    dataset = generate_dataset()
    output_path = "warehouse_operations.csv"
    dataset.to_csv(output_path, index=False)

    print(f"Dataset berhasil dibuat: {output_path}")
    print(f"Jumlah baris: {len(dataset):,}")
    print(f"Jumlah kolom: {dataset.shape[1]}")
    print("\nRingkasan cepat (bukan analisis final, hanya verifikasi pola):")
    summary = dataset.groupby("shift")[["demurrage_penalty_usd", "dwell_time_hours"]].mean().round(2)
    print(summary)
