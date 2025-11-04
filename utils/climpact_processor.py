import pandas as pd
import numpy as np
from datetime import datetime
import os

# --- Fungsi Indeks Suhu ---
def idxTemp(df, tave, tmax, tmin):
    df = df.copy()
    df["DTR"] = df[tmax] - df[tmin]

    # Hitung persentil global (seluruh data)
    p10_tmin = df[tmin].quantile(0.10)
    p90_tmax = df[tmax].quantile(0.90)

    TN10p = df.groupby('YEAR')[tmin].apply(
        lambda x: np.nan if x.isna().all() else (x < p10_tmin).sum() / len(x) * 100
    )
    TX90p = df.groupby('YEAR')[tmax].apply(
        lambda x: np.nan if x.isna().all() else (x > p90_tmax).sum() / len(x) * 100
    )

    TMm = df.groupby('YEAR')[tave].mean()
    TMx = df.groupby('YEAR')[tave].max()
    TMn = df.groupby('YEAR')[tave].min()

    TXm = df.groupby('YEAR')[tmax].mean()
    TXx = df.groupby('YEAR')[tmax].max()
    TXn = df.groupby('YEAR')[tmax].min()

    TNx = df.groupby('YEAR')[tmin].max()
    TNn = df.groupby('YEAR')[tmin].min()
    TNm = df.groupby('YEAR')[tmin].mean()

    DTR_year = df.groupby('YEAR')["DTR"].mean()
    ETR = TXx - TNn

    INDEK_T = pd.DataFrame({
        'TMm': TMm.round(3),
        'TMx': TMx.round(3),
        'TMn': TMn.round(3),
        'TXm': TXm.round(3),
        'TXx': TXx.round(3),
        'TXn': TXn.round(3),
        'TNx': TNx.round(3),
        'TNn': TNn.round(3),
        'TNm': TNm.round(3),
        'DTR': DTR_year.round(3),
        'ETR': ETR.round(3),
        'TN10p': TN10p.round(3),
        'TX90p': TX90p.round(3)
    })
    return INDEK_T


# --- Fungsi Indeks Curah Hujan ---
def idxRain(df, ch):
    def HHnMM(data, threshold):
        if data.isna().all() or data.empty:
            return np.nan
        return (data >= threshold).sum()

    def FHnMM(numerator, denominator):
        result = np.where(
            (denominator == 0) & (numerator == 0), np.nan,
            np.where(
                (numerator == 0) & (denominator != 0), 0.0,
                np.where(
                    (denominator != 0) & (numerator != 0),
                    (numerator / denominator * 100).round(2),
                    np.nan
                )
            )
        )
        return result

    def cdd(data, threshold=1):
        if data.isna().all() or data.empty:
            return np.nan
        max_cdd = current = 0
        for val in data:
            if pd.isna(val):
                continue
            if val < threshold:
                current += 1
                max_cdd = max(max_cdd, current)
            else:
                current = 0
        return max_cdd

    def cwd(data, threshold=1):
        if data.isna().all() or data.empty:
            return np.nan
        max_cwd = current = 0
        for val in data:
            if pd.isna(val):
                continue
            if val >= threshold:
                current += 1
                max_cwd = max(max_cwd, current)
            else:
                current = 0
        return max_cwd

    def RxNDay(data, windows):
        if data.isna().all() or data.empty:
            return np.nan
        if windows == 1:
            return data.max()
        if len(data) < windows:
            return data.sum() if not data.isna().all() else np.nan
        rolling_sums = [data.iloc[i:i+windows].sum() for i in range(len(data) - windows + 1)]
        return np.nanmax(rolling_sums) if rolling_sums else np.nan

    def RqP(data, q):
        valid = data[data > 1]
        if valid.empty:
            return np.nan
        threshold = valid.quantile(q)
        return valid[valid > threshold].sum()

    def RqPtot(numerator, denominator):
        return np.where(
            (denominator == 0) & (numerator == 0), np.nan,
            np.where(
                (denominator != 0) & (numerator != 0),
                (numerator * 100 / denominator).round(2),
                np.nan
            )
        )

    yearly = df.groupby('YEAR')[ch]

    PRECTOT = yearly.sum()
    HH = yearly.apply(lambda x: HHnMM(x, 1))
    HH20MM = yearly.apply(lambda x: HHnMM(x, 20))
    HH50MM = yearly.apply(lambda x: HHnMM(x, 50))
    HH100MM = yearly.apply(lambda x: HHnMM(x, 100))
    HH150MM = yearly.apply(lambda x: HHnMM(x, 150))

    FH20 = FHnMM(HH20MM, HH)
    FH50 = FHnMM(HH50MM, HH)
    FH100 = FHnMM(HH100MM, HH)
    FH150 = FHnMM(HH150MM, HH)

    CDD = yearly.apply(lambda x: cdd(x, 1))
    CWD = yearly.apply(lambda x: cwd(x, 1))
    SDII = yearly.apply(lambda x: x[x >= 1].sum() / len(x[x >= 1]) if len(x[x >= 1]) > 0 else np.nan)

    RX1DAY = yearly.apply(lambda x: RxNDay(x, 1))
    RX5DAY = yearly.apply(lambda x: RxNDay(x, 5))
    RX7DAY = yearly.apply(lambda x: RxNDay(x, 7))
    RX10DAY = yearly.apply(lambda x: RxNDay(x, 10))

    R95P = yearly.apply(lambda x: RqP(x, 0.95))
    R99P = yearly.apply(lambda x: RqP(x, 0.99))
    R95Ptot = RqPtot(R95P, PRECTOT)
    R99Ptot = RqPtot(R99P, PRECTOT)

    INDEK_CH = pd.DataFrame({
        'PRECTOT': PRECTOT.round(1),
        'HH': HH.round(1),
        'HH20MM': HH20MM.round(1),
        'HH50MM': HH50MM.round(1),
        'HH100MM': HH100MM.round(1),
        'HH150MM': HH150MM.round(1),
        'FH20': FH20,
        'FH50': FH50,
        'FH100': FH100,
        'FH150': FH150,
        'R50': HH50MM.round(1),
        'CDD': CDD.round(1),
        'CWD': CWD.round(1),
        'SDII': SDII.round(1),
        'RX1DAY': RX1DAY.round(1),
        'RX5DAY': RX5DAY.round(1),
        'RX7DAY': RX7DAY.round(1),
        'RX10DAY': RX10DAY.round(1),
        'R95P': R95P.round(1),
        'R99P': R99P.round(1),
        'R95Ptot': R95Ptot,
        'R99Ptot': R99Ptot
    })

    INDEK_CH = INDEK_CH.replace([np.inf, -np.inf], np.nan)
    return INDEK_CH


# --- Fungsi Utama Pemrosesan Data ---
def process_climpact_data(file_path, start_year=None, end_year=None):
    """
    Proses file data stasiun dan hitung indeks ekstrem lengkap (suhu & curah hujan).
    Jika start_year/end_year diberikan, batasi data ke periode tersebut.
    """
    try:
        df = pd.read_csv(file_path, sep=';')
    except Exception as e:
        raise ValueError(f"Error membaca file: {e}")

    # Validasi kolom wajib
    required_cols = ['DATA_TIMESTAMP', 'NAME', 'CURRENT_LATITUDE', 'CURRENT_LONGITUDE', 'YEAR']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Kolom '{col}' tidak ditemukan dalam file.")

    # Validasi format tanggal
    try:
        df['date'] = pd.to_datetime(df['DATA_TIMESTAMP'], format='%d/%m/%Y', errors='coerce')
    except Exception:
        raise ValueError("Format tanggal DATA_TIMESTAMP tidak valid. Harus DD/MM/YYYY.")
    if df['date'].isnull().any():
        raise ValueError("Format tanggal tidak valid pada beberapa baris.")

    # Ambil metadata dari baris pertama
    first_row = df.iloc[0]
    station_name = str(first_row['NAME']).strip()
    lat = float(first_row['CURRENT_LATITUDE'])
    lon = float(first_row['CURRENT_LONGITUDE'])

    if not (-90 <= lat <= 90):
        raise ValueError("Latitude harus antara -90 dan 90.")
    if not (-180 <= lon <= 180):
        raise ValueError("Longitude harus antara -180 dan 180.")

    # Tentukan rentang tahun
    data_min_year = int(df['YEAR'].min())
    data_max_year = int(df['YEAR'].max())

    use_start = int(start_year) if start_year not in (None, '') else None
    use_end = int(end_year) if end_year not in (None, '') else None

    if use_start is not None and use_end is not None:
        if use_start > use_end:
            raise ValueError("Start Year tidak boleh lebih besar dari End Year.")
        if use_start < data_min_year or use_end > data_max_year:
            raise ValueError(
                f"Periode manual ({use_start}–{use_end}) harus dalam rentang data ({data_min_year}–{data_max_year})."
            )
        final_start, final_end = use_start, use_end
    else:
        final_start, final_end = data_min_year, data_max_year

    # Filter data
    df = df[(df['YEAR'] >= final_start) & (df['YEAR'] <= final_end)].copy()
    if df.empty:
        raise ValueError("Tidak ada data dalam periode yang ditentukan.")

    # Hitung indeks
    result_temp = None
    result_rain = None

    if all(col in df.columns for col in ['tave', 'tmax', 'tmin']):
        result_temp = idxTemp(df, 'tave', 'tmax', 'tmin')
    if 'ch' in df.columns:
        result_rain = idxRain(df, 'ch')

    if result_temp is None and result_rain is None:
        raise ValueError("Tidak ada kolom suhu (tave,tmax,tmin) atau curah hujan (ch) untuk diproses.")

    # Gabungkan hasil
    if result_temp is not None and result_rain is not None:
        indices = pd.merge(
            result_temp.reset_index(),
            result_rain.reset_index(),
            on='YEAR',
            how='outer'
        ).set_index('YEAR')
    else:
        indices = result_temp if result_temp is not None else result_rain

    # Metadata
    metadata = {
        'station_name': station_name,
        'latitude': lat,
        'longitude': lon,
        'base_period_start': final_start,
        'base_period_end': final_end,
        'processed_on': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_years': len(indices),
        'data_start_year': data_min_year,
        'data_end_year': data_max_year,
        'used_manual_period': (use_start is not None and use_end is not None)
    }

    return indices, metadata