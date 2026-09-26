import os
from pathlib import Path
from ultralytics import YOLO

if __name__ == '__main__':
    # Load the pre-trained YOLOv8 Small model (For Optimal Run)
    model = YOLO('yolov8s.pt')

    print("🚀 Starting Roadguard Training on AMD RX 9070 XT...")

    # 1. Dynamically get the folder where this script is located
    # This makes the code work on ANY computer or folder with any AMD!
    base_dir = Path(__file__).parent
    
    # Search for either .yaml or .yml in any subfolder of the current directory
    yaml_files = list(base_dir.rglob("data.yaml")) + list(base_dir.rglob("data.yml"))
    
    if not yaml_files:
        raise FileNotFoundError("❌ Could not find data.yaml or data.yml. Please check your folder names.")
    
    # Use the first one it finds
    data_path = str(yaml_files[0])
    print(f"✅ Found dataset config at: {data_path}")

    # 2. Train the model
    model.train(
        data=data_path,         # Uses the automatically found path!
        epochs=100,           
        imgsz=640,            
        device=0,               # Force AMD GPU
        batch=32,             
        workers=2,            
        amp=True,             
        cache=True,           
        patience=20,          
        save_period=10,       
        name='roadguard_violations' 
    )
    
    print("\n✅ Training complete!")