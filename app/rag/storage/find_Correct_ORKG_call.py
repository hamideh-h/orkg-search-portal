import requests

ORKG_SANDBOX_API = "https://sandbox.orkg.org/api"

def debug_print_contribution_statements(contribution_id: str) -> None:
    url = f"{ORKG_SANDBOX_API}/statements"
    params = {
        "subject_id": contribution_id,  # <-- this is the key you need
        "size": 200,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    print("Status:", resp.status_code)
    page = data.get("page", {})
    print("Total elements:", page.get("total_elements"))
    print("Total pages:", page.get("total_pages"))

    for s in data.get("content", []):
        subj = s["subject"]
        pred = s["predicate"]
        obj = s["object"]
        print(
            "Subject:", subj["id"],
            "| Predicate:", pred["id"], pred["label"],
            "-> Object:", obj.get("label") or obj.get("id"),
            "| Object class:", obj.get("_class"),
        )

if __name__ == "__main__":
    debug_print_contribution_statements("R874725")
