from ultralytics import YOLO

# Load your trained model
model = YOLO('runs/detect/train-13/weights/best.pt')

# Export to ONNX (optimized for RK3588 NPU)
model.export(
    format='onnx',
    imgsz=640,
    opset=12,          # RK3588 works best with opset 12
    simplify=True,     # Fuse operations for better NPU performance
    dynamic=False      # Fixed batch size for faster inference
)

print("✅ ONNX export complete: best.onnx")