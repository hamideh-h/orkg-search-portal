// javascript
import {useEffect, useMemo, useState} from "react";
import {searchResources, searchPapers} from "./api";
import AdvancedFilters from "./AdvancedFilters";


const ALL_TYPES = ["Paper", "Software", "Dataset", "Code"];

export default function App() {
    // basic search + paging
    const [typedQ, setTypedQ] = useState("software");
    const [q, setQ] = useState("software");
    const [page, setPage] = useState(0);
    const [size, setSize] = useState(25);

    // resource types
    const [types, setTypes] = useState(["Paper", "Software", "Dataset", "Code"]);

    // paper-only filters
    const [author, setAuthor] = useState("");
    const [yearFrom, setYearFrom] = useState("");
    const [yearTo, setYearTo] = useState("");

    // data state
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [data, setData] = useState({total: 0, page: 0, size: 25, items: []});

    // --- debounce the keyword input ---
    useEffect(() => {
        const t = setTimeout(() => {
            setQ(typedQ.trim());
            setPage(0);
        }, 400);
        return () => clearTimeout(t);
    }, [typedQ]);

    // --- fetch data whenever inputs change ---
    useEffect(() => {
        if (!q) {
            setData({total: 0, page: 0, size, items: []});
            setLoading(false);
            return;
        }

        let cancelled = false;
        setLoading(true);
        setError("");

        const wantsPaperOnly = types.length === 1 && types[0] === "Paper";
        const hasPaperFilters = Boolean(author || yearFrom || yearTo);

        const fetchPromise =
            wantsPaperOnly && hasPaperFilters
                ? searchPapers(q, page, size, author, yearFrom, yearTo)
                : searchResources(q, page, size, types);

        Promise.resolve(fetchPromise)
            .then((res) => {
                if (cancelled) return;
                // basic validation of expected shape
                if (res && typeof res === "object" && Array.isArray(res.items) && typeof res.total === "number") {
                    setData(res);
                } else {
                    // fallback to a safe shape
                    setData({
                        total: Number(res?.total) || 0,
                        page: Number(res?.page) || page,
                        size: Number(res?.size) || size,
                        items: Array.isArray(res?.items) ? res.items : [],
                    });
                }
            })
            .catch((e) => {
                if (cancelled) return;
                setError(String(e));
            })
            .finally(() => {
                if (cancelled) return;
                setLoading(false);
            });

        return () => {
            cancelled = true;
        };
    }, [q, page, size, types, author, yearFrom, yearTo]);

    const totalPages = useMemo(() => {
        const total = data?.total ?? 0;
        const pageSize = data?.size || size;
        return total ? Math.max(1, Math.ceil(total / pageSize)) : 1;
    }, [data, size]);

    const toggleType = (t) => {
        setPage(0);
        setTypes((prev) =>
            prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
        );
    };

    const setAllTypes = () => setTypes([...ALL_TYPES]);
    const setNoTypes = () => setTypes([]);

    return (
        <div
            style={{
                maxWidth: 980,
                margin: "24px auto 80px",
                padding: "0 16px",
                fontFamily: "system-ui, Arial, Segue UI",
            }}
        >
            <h1 style={{marginBottom: 16}}>ORKG Search</h1>

            {/* Search + page size */}
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "1fr auto",
                    gap: 12,
                    marginBottom: 12,
                }}
            >
                <input
                    placeholder="Type keyword (searched in title/label)…"
                    value={typedQ}
                    onChange={(e) => setTypedQ(e.target.value)}
                    style={{
                        padding: "10px 12px",
                        fontSize: 16,
                        border: "1px solid #ccc",
                        borderRadius: 6,
                    }}
                />
                <select
                    value={size}
                    onChange={(e) => {
                        setSize(Number(e.target.value));
                        setPage(0);
                    }}
                    style={{
                        padding: "10px 12px",
                        fontSize: 14,
                        border: "1px solid #ccc",
                        borderRadius: 6,
                    }}
                >
                    {[10, 25, 50, 100].map((n) => (
                        <option key={n} value={n}>
                            {n}/page
                        </option>
                    ))}
                </select>
            </div>

            {/* Resource types */}
            <div
                style={{
                    display: "flex",
                    gap: 16,
                    alignItems: "center",
                    marginBottom: 12,
                    flexWrap: "wrap",
                }}
            >
                <strong>Resource types:</strong>
                {ALL_TYPES.map((t) => (
                    <label
                        key={t}
                        style={{display: "inline-flex", gap: 6, alignItems: "center"}}
                    >
                        <input
                            type="checkbox"
                            checked={types.includes(t)}
                            onChange={() => toggleType(t)}
                        />
                        {t}
                    </label>
                ))}
                <button
                    onClick={setAllTypes}
                    style={{
                        padding: "6px 10px",
                        borderRadius: 8,
                        border: "1px solid #999",
                        background: "#fff",
                        fontWeight: 600,
                    }}
                >
                    All
                </button>
                <button
                    onClick={setNoTypes}
                    style={{
                        padding: "6px 10px",
                        borderRadius: 8,
                        border: "1px solid #999",
                        background: "#fff",
                        fontWeight: 600,
                    }}
                >
                    None
                </button>
            </div>

            {/* Paper-only filters */}
            {types.includes("Paper") && (
                <div
                    style={{
                        display: "flex",
                        gap: 12,
                        alignItems: "center",
                        marginBottom: 12,
                        flexWrap: "wrap",
                    }}
                >
                    <strong>Paper filters:</strong>
                    <input
                        placeholder="Author contains…"
                        value={author}
                        onChange={(e) => {
                            setAuthor(e.target.value);
                            setPage(0);
                        }}
                        style={{padding: "6px 8px", border: "1px solid #ccc", borderRadius: 6}}
                    />
                    <input
                        placeholder="Year from"
                        inputMode="numeric"
                        value={yearFrom}
                        onChange={(e) => {
                            setYearFrom(e.target.value.replace(/\D/g, ""));
                            setPage(0);
                        }}
                        style={{width: 110, padding: "6px 8px", border: "1px solid #ccc", borderRadius: 6}}
                    />
                    <input
                        placeholder="Year to"
                        inputMode="numeric"
                        value={yearTo}
                        onChange={(e) => {
                            setYearTo(e.target.value.replace(/\D/g, ""));
                            setPage(0);
                        }}
                        style={{width: 110, padding: "6px 8px", border: "1px solid #ccc", borderRadius: 6}}
                    />
                    <span style={{fontSize: 12, opacity: 0.7}}>
            (Paper filters apply only when “Paper” is the <em>only</em> selected type)
          </span>
                </div>
            )}

            <AdvancedFilters
                onFilterResults={(ids) => {
                    setData((prev) => ({
                        ...prev,
                        items: prev.items.filter((item) => ids.includes(item.id)),
                        total: prev.items.filter((item) => ids.includes(item.id)).length,
                    }));
                }}
            />


            {/* Status / errors */}
            {loading && <div>Loading…</div>}
            {error && (
                <div style={{color: "crimson", whiteSpace: "pre-wrap", marginBottom: 8}}>
                    {error}
                </div>
            )}

            <div style={{marginBottom: 8}}>
                <strong>Total:</strong> {data.total ?? 0} &nbsp;|&nbsp;{" "}
                <strong>Page:</strong> {page + 1} / {totalPages} &nbsp;|&nbsp;{" "}
                <strong>Types:</strong> {types.length ? types.join(", ") : "—"}
            </div>

            {/* Results */}
            <ul style={{listStyle: "none", padding: 0, margin: 0}}>
                {(data.items || []).map((it) => (
                    <li
                        key={it.id}
                        style={{
                            padding: "12px 8px",
                            borderBottom: "1px solid #eee",
                        }}
                    >
                        <div style={{fontWeight: 600}}>
                            {it.label || "(no title)"}{" "}
                            <span style={{opacity: 0.6}}>
                •{" "}
                                <a
                                    href={`https://orkg.org/resource/${it.id}`}
                                    target="_blank"
                                    rel="noreferrer"
                                >
                  {it.id}
                </a>
              </span>
                        </div>
                        <div style={{marginTop: 4, fontSize: 14, opacity: 0.8}}>
                            {Array.isArray(it.classes) && it.classes.length
                                ? it.classes.join(", ")
                                : "—"}
                        </div>
                    </li>
                ))}
            </ul>

            {/* Pagination */}
            <div style={{display: "flex", gap: 8, marginTop: 16}}>
                <button disabled={page <= 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>
                    Prev
                </button>
                <button
                    disabled={page + 1 >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                >
                    Next
                </button>
            </div>

            <p style={{marginTop: 24, fontSize: 13, opacity: 0.7}}>
                Paper filters (author/year) trigger a paper-specific search when “Paper” is the only selected type.
            </p>
        </div>
    );
}
