import { useEffect, useState } from "react";
import { api } from "../api/client.js";
import { useToast } from "../components/toastContext.jsx";
import PurgeModal from "../components/PurgeModal.jsx";

export default function ConfigPage({ user }) {
  const [retention, setRetention] = useState(30);
  const [retDays, setRetDays] = useState(30);
  const [ocr, setOcr] = useState(null);
  const [tpl, setTpl] = useState({ template_dir: "", default_template: null, available: [] });
  const [purgeOpen, setPurgeOpen] = useState(false);
  const notify = useToast();

  useEffect(() => {
    let alive = true;
    api("/system/retention").then((r) => {
      if (alive) { setRetention(r.retention_days); setRetDays(r.retention_days); }
    }).catch(() => {});
    api("/system/ocr").then((o) => { if (alive) setOcr(o); }).catch(() => {});
    api("/system/templates").then((t) => { if (alive) setTpl(t); }).catch(() => {});
    return () => { alive = false; };
  }, []);

  async function saveRetention() {
    try {
      const r = await api("/system/retention", { method: "PUT", body: { days: Number(retDays) || 1 } });
      setRetention(r.retention_days); setRetDays(r.retention_days);
      notify(`Retention window saved: ${r.retention_days} days`, "success");
    } catch (e) { notify(e.message, "error"); }
  }

  function openPurge() {
    if (!user.mfa_enabled) {
      notify("Enable MFA in Account settings before purging evidence.", "error");
      return;
    }
    setPurgeOpen(true);
  }

  async function changeOcr(backend) {
    try {
      await api("/system/ocr", { method: "PUT", body: { backend } });
      setOcr((o) => ({ ...o, backend }));
      notify(`OCR engine switched to ${backend}`, "success");
    } catch (e) { notify(e.message, "error"); }
  }

  async function saveTemplates() {
    try {
      await api("/system/templates/settings", {
        method: "PUT",
        body: { template_dir: tpl.template_dir, default_template: tpl.default_template },
      });
      setTpl(await api("/system/templates"));
      notify("Template settings saved", "success");
    } catch (e) { notify(e.message, "error"); }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-2xl font-black text-slate-800">Configuration</h1>

      <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <h2 className="font-bold text-slate-800 mb-1">🗑️ Storage Retention</h2>
        <p className="text-sm text-slate-500 mb-4">
          Finalized violations older than this window are auto-purged every 24h.
          Pending evidence is never auto-destroyed. Current: <b>{retention} days</b>.
        </p>
        <div className="flex items-center gap-3">
          <input type="number" min="1" max="3650" value={retDays}
            onChange={(e) => {
              const raw = e.target.value;
              setRetDays(raw === "" ? "" : String(Math.max(1, Math.min(3650, Number(raw)))));
            }}
            className="w-32 border rounded-lg px-3 py-2 font-mono" />
          <button onClick={saveRetention}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700">Save</button>
          <button onClick={openPurge}
            className="px-4 py-2 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700">Purge Now</button>
        </div>
      </section>

      <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <h2 className="font-bold text-slate-800 mb-1">🧠 OCR Engine</h2>
        <p className="text-sm text-slate-500 mb-4">Hot-swap the plate recognition backend without redeploying.</p>
        {ocr && (
          <select value={ocr.backend} onChange={(e) => changeOcr(e.target.value)}
            className="border rounded-lg px-3 py-2 bg-white font-mono">
            {ocr.options.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        )}
      </section>

      <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <h2 className="font-bold text-slate-800 mb-1">📄 Report Template Engine</h2>
        <p className="text-sm text-slate-500 mb-4">
          Directory of custom .docx templates using {"{{plate}}"}, {"{{event_id}}"} placeholders.
        </p>
        <label className="text-sm font-semibold text-slate-600 block mb-1">Template Directory</label>
        <input value={tpl.template_dir} onChange={(e) => setTpl({ ...tpl, template_dir: e.target.value })}
          className="w-full border rounded-lg px-3 py-2 mb-3 font-mono text-sm" />
        <label className="text-sm font-semibold text-slate-600 block mb-1">Default Template</label>
        <select value={tpl.default_template ?? ""}
          onChange={(e) => setTpl({ ...tpl, default_template: e.target.value || null })}
          className="w-full border rounded-lg px-3 py-2 mb-3 bg-white">
          <option value="">-- Legacy hardcoded report --</option>
          {tpl.available.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <button onClick={saveTemplates}
          className="px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700">
          Save Template Settings
        </button>
      </section>

      {purgeOpen && <PurgeModal retentionDays={retention} onClose={() => setPurgeOpen(false)} />}
    </div>
  );
}