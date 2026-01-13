### Status: Work in Progress (Active Development)

This repository is under active development and not yet production-ready. 
The core architecture and main functionality are implemented; stability,
evaluation, and documentation are still evolving.


# ORKG Search Portal

A lightweight web interface for semantic search over research knowledge graphs.

### Live Demo
👉 https://hamideh-h.github.io/orkg-search-portal/

### Backend
Deployed at: https://orkg-search-portal.onrender.com  


# ORKG Search Portal

A lightweight full-stack web application that provides a simple search interface for the **Open Research Knowledge Graph (ORKG)**.  
The project consists of a **JavaScript frontend** and a **Python backend**, designed to demonstrate clean API integration, data processing, and modular architecture.

---


## Architecture Overview

The application is split into two independent components:

Frontend (JavaScript) ←→ Backend (Python) ←→ ORKG REST API

### 🔹 Frontend (JavaScript)

The frontend is a client-side JavaScript application. It is responsible for:

- Rendering the search interface  
- Collecting user queries  
- Sending requests to the backend  
- Displaying the processed ORKG results  

It **never talks directly** to the ORKG API. Everything goes through the backend.



## Extracting paper annotations and summary

A small CLI helper was added to extract structured annotations from an ORKG paper and generate a short paragraph summary.

Files:
- `app/rag/scripts/extract_paper_summary.py` — main implementation and CLI entrypoint.

Usage (PowerShell / CMD):

- Run with a paper id (for example R874684):

  python -m app.rag.scripts.extract_paper_summary R874684

  or

  python app\rag\scripts\extract_paper_summary.py R874684

- If you omit the paper id the script will default to `R874684`.

What it does:
- Calls the project's ORKG extraction runner to collect annotations (contributions, statements, related entities).
- Saves a machine-readable JSON file named `orkg_template_agnostic_<paper_id>.json` in the current working directory.
- Prints a small human-readable paragraph summary and a count of extracted contributions.

Output files and example:
- `orkg_template_agnostic_R874684.json` — contains the extracted bundle (JSON). This file is what downstream scripts expect.

Return value (programmatic):
- The script returns a tuple `(out_path, bundle, paragraph)` when called from Python.

If you want the script to always use a specific id from code, call it like:

    from app.rag.scripts.extract_paper_summary import main
    main(["R874684"])
