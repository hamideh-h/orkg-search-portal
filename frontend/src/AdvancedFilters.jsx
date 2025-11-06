// javascript
import { useEffect, useState } from "react";

export default function AdvancedFilters({ onFilterResults }) {
  const [templateId, setTemplateId] = useState("");
  const [fields, setFields] = useState([]);
  const [selectedField, setSelectedField] = useState("");
  const [fieldValue, setFieldValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const id = templateId.trim();
    if (!id) {
      setFields([]);
      setSelectedField("");
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError("");

    fetch(`https://orkg.org/api/templates/${id}`, { signal: controller.signal })
      .then((r) => {
        if (!r.ok) throw new Error("Template not found");
        return r.json();
      })
      .then((data) => {
        const props = (Array.isArray(data?.properties) ? data.properties : []).map((p) => ({
          label: p?.path?.label || p?.label || "Unnamed field",
          predicate: p?.path?.id || p?.id || "",
        })).filter((p) => p.predicate);
        setFields(props);
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setError(err.message || String(err));
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [templateId]);

  const handleFieldSearch = async () => {
    if (!selectedField || !fieldValue) return;
    setLoading(true);
    setError("");

    try {
      const url = `https://orkg.org/api/statements/?predicate=${encodeURIComponent(
        selectedField
      )}&object__icontains=${encodeURIComponent(fieldValue)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Search failed: ${res.status}`);
      const json = await res.json();
      const ids = Array.isArray(json?.content)
        ? json.content.map((s) => s?.subject?.id).filter(Boolean)
        : [];
      onFilterResults(ids);
    } catch (err) {
      if (err.name === "AbortError") return;
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        border: "1px solid #ddd",
        borderRadius: 8,
        padding: 12,
        marginBottom: 16,
      }}
    >
      <h3 style={{ marginTop: 0 }}>Advanced (template-based) filters</h3>

      <input
        placeholder="Template ID (e.g. R108555)…"
        value={templateId}
        onChange={(e) => setTemplateId(e.target.value)}
        style={{
          width: "100%",
          padding: "8px 10px",
          border: "1px solid #ccc",
          borderRadius: 6,
          marginBottom: 8,
        }}
      />

      {loading && <div style={{ fontSize: 14 }}>Loading…</div>}
      {error && <div style={{ color: "crimson" }}>{error}</div>}

      {fields.length > 0 ? (
        <>
          <div
            style={{
              display: "flex",
              gap: 8,
              alignItems: "center",
              flexWrap: "wrap",
              marginBottom: 8,
            }}
          >
            <select
              value={selectedField}
              onChange={(e) => setSelectedField(e.target.value)}
              style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid #ccc" }}
            >
              <option value="">Select field…</option>
              {fields.map((f) => (
                <option key={f.predicate} value={f.predicate}>
                  {f.label}
                </option>
              ))}
            </select>

            <input
              placeholder="Value (e.g. BERT)"
              value={fieldValue}
              onChange={(e) => setFieldValue(e.target.value)}
              style={{
                padding: "6px 8px",
                border: "1px solid #ccc",
                borderRadius: 6,
                flex: "1 1 200px",
              }}
            />

            <button
              onClick={handleFieldSearch}
              disabled={loading || !selectedField || !fieldValue}
              style={{
                padding: "6px 10px",
                borderRadius: 6,
                border: "1px solid #999",
                background: "#f4f4f4",
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              Filter
            </button>
          </div>

          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {fields.map((f) => (
              <li key={f.predicate}>
                {f.label} <code>{f.predicate}</code>
              </li>
            ))}
          </ul>
        </>
      ) : (
        templateId.trim() && !loading && <div style={{ fontSize: 13 }}>No fields found for this template.</div>
      )}
    </div>
  );
}
