# 🚀 How to Run the Job Market Tracker Project

This guide explains how to spin up the Egyptian Job Market Tracker database, pipelines, API, web frontend, and Airflow scheduler.

---

## 🏗️ Architecture & Component Ports
The system consists of the following components:
*   **Web Frontend (React + Vite + Tailwind + Motion):** `http://localhost:3000`
    *   **Landing Page:** `http://localhost:3000/` (Root)
    *   **Analytics Dashboard:** `http://localhost:3000/dashboard`
*   **FastAPI Backend (API):** `http://localhost:8000` (Docs/Swagger at `/docs`)
*   **Airflow Webserver (Scheduler/DAGs):** `http://localhost:8080` (Username/Password: `airflow` / `airflow`)
*   **PostgreSQL Warehouse:** `localhost:5432`

---

## 🐳 Option 1: Docker (Recommended - Zero Local Dependencies)

Make sure you have Docker Desktop running.

### 1. Run App + Database + API + Frontend
To launch the user-facing application (React frontend + FastAPI backend + Postgres database):
```bash
docker compose -f docker-compose.yml -f docker-compose.app.yml up --build -d
```
*   **API:** Go to `http://localhost:8000/docs` to test read-only endpoints.
*   **Frontend:** Go to `http://localhost:3000` to see the Landing Page and click "Explore the Dashboard" to see the charts!

### 2. Run Airflow Pipelines (Scheduler & Airflow Webserver)
To run the automated ETL pipelines (scraping, cleaning, postgres loading, and dbt models) orchestrated by Airflow:
```bash
docker compose -f docker-compose.yml -f docker-compose.airflow.yml up --build -d
```
*   Go to `http://localhost:8080` (credentials: `airflow` / `airflow`) to see the scheduled ingestion and dbt DAGs.

### 3. Stop Everything and Clean Up
To stop the running containers and release resources:
```bash
docker compose down -v
```
*(The `-v` flag removes the Postgres volume if you want to wipe the database and start fresh).*

---

## 🐍 Option 2: Run Locally (Python & Node.js)

### Prerequisites
*   Python 3.12+ (managed with `uv` or `venv`)
*   Node.js (for frontend)
*   A running PostgreSQL instance on port `5432` with a database named `job_market_tracker`.

### 1. System Setup
1.  **Configure Environment Variables:**
    Copy the `.env.example` to `.env` and fill in the values:
    ```bash
    cp .env.example .env
    ```
2.  **Install Python dependencies and setup local database schema:**
    ```bash
    make setup
    make bootstrap
    ```

### 2. Run the Data Pipeline Steps Manually
You can execute individual pipeline stages using `make`:
*   **Scrape jobs:** `make scrape` (runs all scrapers) or `make scrape SOURCES="wuzzuf forasna"` (runs specific ones).
*   **Clean and Standardize:** `make pipeline` (bronze to silver CSV cleaning, maps cities, extracts skills).
*   **Load to Postgres:** `make load` (silver CSV to Postgres DB staging schema).
*   **Build DBT Marts:** `make dbt` (runs dbt to compile analytics tables).
*   **Run Test Suite:** `make test` (runs unit and data-quality tests).

### 3. Spin Up Developer Servers Locally
*   **Start Backend API:**
    ```bash
    cd api
    uvicorn main:app --reload --port 8000
    ```
*   **Start React Frontend Dev Server:**
    ```bash
    cd frontend
    npm install
    npm run dev
    ```
    Then visit `http://localhost:5173` (or the port Vite prints in your console).

---

## 🛠️ Common Makefile Commands Reference

| Command | Action |
|:---|:---|
| `make up` | Rebuilds and launches Postgres + Core pipelines in Docker |
| `make down` | Shuts down docker containers and removes database volume |
| `make db-up` | Launches only the Postgres database container |
| `make scrape` | Runs scrapers on Wuzzuf, Forasna, Jobzella, Bayt, and Indeed |
| `make pipeline` | Runs local Python cleaning pipeline on raw scraped datasets |
| `make load` | Runs python loader script to dump clean CSV files into Postgres |
| `make dbt` | Re-compiles all intermediate staging views into final analytics marts |
| `make test` | Runs data quality validation checks and pipeline test suite |
