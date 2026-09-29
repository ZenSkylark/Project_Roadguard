import json
from pathlib import Path
from docx import Document
from ..config import settings

# Persistent settings file inside the storage root
SETTINGS_FILE = Path(settings.STORAGE_ROOT) / "system_settings.json"

def load_ui_settings() -> dict:
    """Loads persistent UI settings (template dir, default template)."""
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    return {"template_dir": "./templates", "default_template": None}

def save_ui_settings(data: dict):
    """Saves settings to disk so they survive server reboots."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, indent=2))

def list_templates() -> list[str]:
    """Returns a list of .docx filenames in the configured directory."""
    s = load_ui_settings()
    t_dir = Path(s.get("template_dir", "./templates"))
    if not t_dir.exists():
        return []
    return sorted([f.name for f in t_dir.glob("*.docx")])

def fill_template(template_name: str, violation_data: dict, output_path: str):
    """Loads a .docx template, replaces placeholders, and saves the result."""
    s = load_ui_settings()
    t_dir = Path(s.get("template_dir", "./templates"))
    template_path = t_dir / template_name
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template '{template_name}' not found in {t_dir}")

    doc = Document(str(template_path))
    
    # Map of placeholders to actual data
    replacements = {
        "{{plate}}": violation_data.get("plate_text") or "N/A",
        "{{event_id}}": violation_data.get("event_id") or "N/A",
        "{{violation}}": violation_data.get("violation_type") or "N/A",
        "{{date}}": str(violation_data.get("captured_at", "N/A")),
        "{{status}}": violation_data.get("status") or "N/A",
        "{{confidence}}": str(violation_data.get("confidence", "N/A")),
        "{{officer}}": violation_data.get("officer_id") or "System",
    }

    # Replace in paragraphs
    for para in doc.paragraphs:
        for key, val in replacements.items():
            if key in para.text:
                # Note: This works best if the placeholder isn't split by formatting changes
                para.text = para.text.replace(key, str(val))
                
    # Replace in tables (if the user puts placeholders in table cells)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    for key, val in replacements.items():
                        if key in para.text:
                            para.text = para.text.replace(key, str(val))

    doc.save(output_path)