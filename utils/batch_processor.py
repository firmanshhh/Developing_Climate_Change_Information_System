import os
import pandas as pd
import zipfile
from datetime import datetime
from .climpact_processor import process_climpact_data

def process_batch(station_files, start_year=None, end_year=None, output_dir=None):
    """
    Proses banyak file stasiun sekaligus.
    Mengembalikan:
        - path ke ZIP hasil
        - path ke summary CSV
    """
    if output_dir is None:
        output_dir = f"uploads/batch_{int(datetime.now().timestamp())}"
    os.makedirs(output_dir, exist_ok=True)

    all_summaries = []
    zip_path = os.path.join(output_dir, "hasil_batch_stasiun.zip")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file in station_files:
            try:
                # Simpan file sementara
                filename = os.path.basename(file.filename)
                filepath = os.path.join(output_dir, filename)
                file.save(filepath)

                # Proses satu stasiun
                result_df, metadata = process_climpact_data(filepath, start_year, end_year)

                # Simpan hasil per stasiun ke ZIP
                csv_name = f"{metadata['station_name'].replace(' ', '_')}_indices.csv"
                csv_path = os.path.join(output_dir, csv_name)
                result_df.to_csv(csv_path)
                zf.write(csv_path, arcname=csv_name)

                # Tambahkan ke ringkasan
                summary = {
                    'station_name': metadata['station_name'],
                    'latitude': metadata['latitude'],
                    'longitude': metadata['longitude'],
                    'period_start': metadata['base_period_start'],
                    'period_end': metadata['base_period_end'],
                    'total_years': metadata['total_years']
                }

                # Ambil rata-rata indeks
                for col in result_df.columns:
                    summary[f"avg_{col}"] = result_df[col].mean()

                all_summaries.append(summary)

            except Exception as e:
                # Jika gagal, catat error dan lanjut
                error_summary = {
                    'station_name': getattr(file, 'filename', 'unknown'),
                    'latitude': None,
                    'longitude': None,
                    'period_start': None,
                    'period_end': None,
                    'total_years': 0,
                    'error': str(e)
                }
                all_summaries.append(error_summary)

    # Buat summary CSV
    summary_df = pd.DataFrame(all_summaries)
    summary_path = os.path.join(output_dir, "summary_all_stations.csv")
    summary_df.to_csv(summary_path, index=False)

    return zip_path, summary_path