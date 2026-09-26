const COLORS = {
  pending: "bg-amber-100 text-amber-800 border-amber-300",
  finalized: "bg-emerald-100 text-emerald-800 border-emerald-300",
  deleted: "bg-red-100 text-red-700 border-red-300",
};

export default function StatusBadge({ status }) {
  return (
    <span className={`px-2 py-0.5 rounded-full border text-xs font-semibold uppercase ${COLORS[status] || "bg-gray-100 text-gray-700 border-gray-300"}`}>
      {status}
    </span>
  );
}