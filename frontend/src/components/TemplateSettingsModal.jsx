import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function TemplateSettingsModal({ onClose }) {
  const [settings, setSettings] = useState({ template_dir: "", default_template: null, available: [] });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    api("/system/templates").then(setSettings).catch((e) => alert(e.message));
  }, []);

  async function save() {
    setBusy(true); setMsg("");
    try {
      await api("/system/templates/settings", {
        method: "PUT",
        body: {
          template_dir: settings.template_dir,
          default_template: settings.default_template
        }
      });
      setMsg("✅ Settings saved successfully!");
      setTimeout(onClose, 1500);
    } catch (e) {
      setMsg(`❌ Error: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 w-[500px] shadow-2xl">
        <h3 className="text-lg font-bold text-gray-800 mb-1">📄 Report Template Engine</h3>
        <p className="text-sm text-gray-500 mb-4">
          Configure the directory containing your custom <span className="font-mono">.docx</span> templates. 
          Use placeholders like <span className="font-mono bg-gray-100 px-1">{"{{plate}}"}</span>, <span className="font-mono bg-gray-100 px-1">{"{{event_id}}"}</span>, <span className="font-mono bg-gray-100 px-1">{"{{violation}}"}</span> in your Word document.
        </p>

        <label className="text-sm font-semibold text-slate-600 block mb-1">Template Directory Path</label>
        <input 
          type="text" 
          value={settings.template_dir}
          onChange={(e) => setSettings({...settings, template_dir: e.target.value})}
          placeholder="./templates or C:\Reports\Templates"
          className="w-full border rounded-lg px-3 py-2 mb-4 font-mono text-sm" 
        />

        <label className="text-sm font-semibold text-slate-600 block mb-1">Default Template</label>
        <select 
          value={settings.default_template || ""}
          onChange={(e) => setSettings({...settings, default_template: e.target.value || null})}
          className="w-full border rounded-lg px-3 py-2 mb-4 bg-white"
        >
          <option value="">-- Use Legacy Hardcoded Report --</option>
          {settings.available.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>

        {settings.available.length === 0 && settings.template_dir && (
          <p className="text-xs text-amber-600 mb-2">⚠️ No .docx files found in this directory.</p>
        )}

        {msg && <p className="text-sm mb-3">{msg}</p>}

        <div className="flex gap-2 mt-4">
          <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100">Cancel</button>
          <button onClick={save} disabled={busy} className="flex-1 px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50">
            {busy ? "Saving..." : "Save Configuration"}
          </button>
        </div>
      </div>
    </div>
  );
}