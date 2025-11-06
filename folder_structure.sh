#!/bin/bash

set -e

# Sumber data
SOURCE_DIRS=("/mnt/share_drive01" "/mnt/share_drive02")

# Tujuan
TARGET_BASE="./files"

# ================================
# 1. Buat struktur untuk REANALISIS dan OBSERVASI (dengan variabel iklim)
# ================================
main_dirs=("REANALYSIS" "OBSERVASI")
declare -A climate_vars
climate_vars["CH"]="CH"
climate_vars["TT"]="T"
climate_vars["WIND"]="WIND"
climate_vars["RADS"]="RADS"
#climate_vars["SST"]="SST"

for main in "${main_dirs[@]}"; do
    for var in "${!climate_vars[@]}"; do
        mkdir -p "$TARGET_BASE/$main/$var"
    done
done

# ================================
# 2. Buat struktur untuk PROYEKSI: hanya CMIP5 dan CMIP6
# ================================
mkdir -p "$TARGET_BASE/PROJECTION/CMIP5"
mkdir -p "$TARGET_BASE/PROJECTION/CMIP6"

# ================================
# 3. Buat folder DOWNSCALLING (tanpa subfolder)
# ================================
mkdir -p "$TARGET_BASE/DOWNSCALLING"

# ================================
# 4. Link data REANALISIS & OBSERVASI
# ================================
for source_dir in "${SOURCE_DIRS[@]}"; do
    if [ ! -d "$source_dir" ]; then continue; fi
    for main in "${main_dirs[@]}"; do
        for var in "${!climate_vars[@]}"; do
            suffix="${climate_vars[$var]}"
            pattern="${main}_${suffix}*"
            target_dir="$TARGET_BASE/$main/$var"
            while IFS= read -r -d '' item; do
                target_link="$target_dir/$(basename "$item")"
                if [ -e "$target_link" ]; then continue; fi
                ln -sf "$item" "$target_link"
            done < <(find "$source_dir" -maxdepth 1 -name "$pattern" -print0 2>/dev/null)
        done
    done
done

# ================================
# 5. Link data PROYEKSI → ke CMIP5 atau CMIP6
# ================================
for source_dir in "${SOURCE_DIRS[@]}"; do
    if [ ! -d "$source_dir" ]; then continue; fi
    
    # CMIP5
    while IFS= read -r -d '' item; do
        target_link="$TARGET_BASE/PROJECTION/CMIP5/$(basename "$item")"
        if [ -e "$target_link" ]; then continue; fi
        ln -sf "$item" "$target_link"
    done < <(find "$source_dir" -maxdepth 1 -name "PROJECTION_CMIP5_*" -print0 2>/dev/null)
    
    # CMIP6
    while IFS= read -r -d '' item; do
        target_link="$TARGET_BASE/PROJECTION/CMIP6/$(basename "$item")"
        if [ -e "$target_link" ]; then continue; fi
        ln -sf "$item" "$target_link"
    done < <(find "$source_dir" -maxdepth 1 -name "PROJECTION_CMIP6_*" -print0 2>/dev/null)
done

# ================================
# 6. Link semua DOWNSCALLING_* langsung ke ./files/DOWNSCALLING/
# ================================
for source_dir in "${SOURCE_DIRS[@]}"; do
    if [ ! -d "$source_dir" ]; then continue; fi
    while IFS= read -r -d '' item; do
        target_link="$TARGET_BASE/DOWNSCALLING/$(basename "$item")"
        if [ -e "$target_link" ]; then continue; fi
        ln -sf "$item" "$target_link"
    done < <(find "$source_dir" -maxdepth 1 -name "DOWNSCALLING_*" -print0 2>/dev/null)
done

echo -e "\n✅ Selesai!"
echo "   - REANALISIS & OBSERVASI: tetap dengan subfolder CH/TT/WIND/RADS/SST"
echo "   - PROYEKSI: hanya CMIP5 dan CMIP6 (semua variabel masuk ke masing-masing folder)"
echo "   - DOWNSCALLING: tanpa subfolder, semua file langsung di root"