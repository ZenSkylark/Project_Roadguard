import os
import shutil
import yaml
from pathlib import Path

# --- DYNAMIC PATHS: Uses the folder this script lives in ---
BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw_datasets"
OUT_DIR = BASE_DIR / "sorted_images"
VEH_DIR = OUT_DIR / "vehicles"
VIO_DIR = OUT_DIR / "violations"

VEH_DIR.mkdir(parents=True, exist_ok=True)
VIO_DIR.mkdir(parents=True, exist_ok=True)

# Categories
VEHICLE_CLASSES = ['motorcycle', 'car', 'jeepney', 'bus', 'mini_bus', 'truck', 'mini_truck']
VIOLATION_CLASSES = ['no_helmet', 'triple_riding', 'red_light', 'green_light', 'yellow_light', 'license_plate']

ALIAS_MAP = {
    'motorbike': 'motorcycle', 'bike': 'motorcycle', 'rider': 'motorcycle',
    'plate': 'license_plate', 'number_plate': 'license_plate',
    'red': 'red_light', 'green': 'green_light', 'yellow': 'yellow_light',
}

def normalize(name):
    return ALIAS_MAP.get(name.lower().strip(), name.lower().strip())

def process_dataset(source_dir):
    yaml_path = source_dir / "data.yaml"
    if not yaml_path.exists():
        yaml_path = source_dir / "data.yml"
    if not yaml_path.exists():
        print(f"  ⚠️ No data.yaml in {source_dir.name}, skipping")
        return

    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    names = data.get('names', [])

    for split in ['train', 'valid', 'val', 'test']:
        img_dir = source_dir / "images" / split
        lbl_dir = source_dir / "labels" / split
        if not img_dir.exists():
            img_dir = source_dir / split / "images"
            lbl_dir = source_dir / split / "labels"
        if not img_dir.exists():
            continue

        for img_path in img_dir.iterdir():
            if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png']:
                continue

            lbl_path = lbl_dir / f"{img_path.stem}.txt"
            classes = set()
            if lbl_path.exists():
                with open(lbl_path) as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            idx = int(parts[0])
                            if idx < len(names):
                                classes.add(normalize(names[idx]))

            new_name = f"{source_dir.name}_{split}_{img_path.name}"
            is_veh = bool(classes & set(VEHICLE_CLASSES))
            is_vio = bool(classes & set(VIOLATION_CLASSES))

            if is_vio:
                shutil.copy2(img_path, VIO_DIR / new_name)
            if is_veh:
                shutil.copy2(img_path, VEH_DIR / new_name)

    print(f"  ✅ Processed {source_dir.name}")

if __name__ == '__main__':
    print("🚀 Extracting and sorting images...")
    datasets = [d for d in RAW_DIR.iterdir() if d.is_dir()]
    if not datasets:
        print("❌ No datasets found in raw_datasets!")
    else:
        for ds in datasets:
            process_dataset(ds)

    print(f"\n🎉 DONE! Check: {OUT_DIR}")
    print(f"   🚗 Vehicles: {len(list(VEH_DIR.iterdir()))} images")
    print(f"   🚨 Violations: {len(list(VIO_DIR.iterdir()))} images")