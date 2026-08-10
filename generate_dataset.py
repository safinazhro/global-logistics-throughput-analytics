import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Mengunci baris acak agar data konsisten
np.random.seed(42)
total_records = 600

# Membuat basis data logistik umum
data = {
    'transaction_id': [f"TXN-{2000+i}" for i in range(total_records)],
    'container_id': [f"CNTR{np.random.randint(100000, 999999)}" for i in range(total_records)],
    'cargo_type': np.random.choice(['Standard Dry', 'Refrigerated', 'Hazardous'], size=total_records, p=[0.65, 0.20, 0.15]),
    'volume_cbm': np.round(np.random.uniform(25, 75, size=total_records), 2),
    'labor_assigned': np.random.choice([2, 4, 6, 8], size=total_records, p=[0.3, 0.4, 0.2, 0.1])
}

df = pd.DataFrame(data)

# Simulasi lini waktu kedatangan truk selama 2 bulan
base_date = datetime(2026, 1, 1)
arrival_times = [base_date + timedelta(days=int(np.random.randint(0, 60)), hours=int(np.random.randint(0, 24)), minutes=int(np.random.randint(0, 60))) for _ in range(total_records)]
df['arrival_datetime'] = sorted(arrival_times)

# Aturan durasi bongkar muat logistik realistis (Refrigerated & Hazardous butuh waktu penanganan lebih lama)
durations = []
for idx, row in df.iterrows():
    base_hours = row['volume_cbm'] / (row['labor_assigned'] * 3.5) # Kecepatan bongkar standar per jam
    if row['cargo_type'] == 'Hazardous':
        base_hours *= 1.6 # Protokol keamanan memperlambat proses
    elif row['cargo_type'] == 'Refrigerated':
        base_hours *= 1.3 # Pengecekan suhu memperlambat proses
    durations.append(timedelta(hours=base_hours))

df['unloading_start_datetime'] = df['arrival_datetime'] + timedelta(minutes=20) # Waktu tunggu gerbang standar 20 menit
df['unloading_end_datetime'] = df['unloading_start_datetime'] + durations

# Menyimpan ke file CSV netral
df.to_csv('warehouse_operations.csv', index=False)
print("Sukses! File 'warehouse_operations.csv' berhasil dibuat di folder Anda.")
