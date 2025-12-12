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



