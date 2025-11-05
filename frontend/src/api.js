const API_BASE = import.meta.env.VITE_API_BASE || "https://orkg-search-portal.onrender.com";

export async function searchResources(q, page = 0, size = 25, classes = []) {
  const url = new URL("/api/search", API_BASE);
  url.searchParams.set("q", q);
  url.searchParams.set("page", String(page));
  url.searchParams.set("size", String(size));
  if (Array.isArray(classes) && classes.length) {
    url.searchParams.set("classes", classes.join(","));
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error(`[${res.status}] ${await res.text()}`);
  return res.json();
}

export async function searchPapers(q, page = 0, size = 25, author = "", yearFrom = "", yearTo = "") {
  const url = new URL("/api/search", API_BASE);
  url.searchParams.set("q", q);
  url.searchParams.set("page", String(page));
  url.searchParams.set("size", String(size));
  url.searchParams.set("classes", "Paper");
  if (author)    url.searchParams.set("author", author);
  if (yearFrom)  url.searchParams.set("year_from", String(yearFrom));
  if (yearTo)    url.searchParams.set("year_to", String(yearTo));
  const res = await fetch(url);
  if (!res.ok) throw new Error(`[${res.status}] ${await res.text()}`);
  return res.json();
}
