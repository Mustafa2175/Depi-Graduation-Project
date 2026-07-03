"""
Job Market Tracker — FastAPI Backend

Exposes the 7 dbt mart tables as read-only JSON endpoints.
Run locally with:  uvicorn api.main:app --reload --port 8000
"""

from typing import List, Optional

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.database import get_db, engine
from api.models import (
    SalaryIntelligence,
    InDemandRole,
    CompanyInsight,
    GeographicDistribution,
    SkillDemand,
    HiringTrend,
    WorkModeBreakdown,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Job Market Tracker API",
    description=(
        "Read-only REST API over the Egyptian Job Market Tracker analytics "
        "warehouse. Data is refreshed every 6 hours by Airflow."
    ),
    version="1.0.0",
)

# Allow the React frontend (localhost:3000) and Swagger UI to make requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper: clamp limit to [1, 1000]
# ---------------------------------------------------------------------------
def _clamp_limit(limit: int) -> int:
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be >= 1")
    return min(limit, 1000)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health", tags=["Health"])
def health_check():
    """Quick check that the database is reachable."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"DB unreachable: {exc}")


# ---------------------------------------------------------------------------
# 1. Salary Intelligence
# ---------------------------------------------------------------------------
@app.get(
    "/api/salary-intelligence",
    response_model=List[SalaryIntelligence],
    tags=["Salary Intelligence"],
)
def get_salary_intelligence(
    category: Optional[str] = Query(None, description="Filter by category_name (case-insensitive substring match)"),
    seniority: Optional[str] = Query(None, description="Filter by seniority level"),
    governorate: Optional[str] = Query(None, description="Filter by governorate"),
    skip: int = Query(0, ge=0, description="Rows to skip (pagination)"),
    limit: int = Query(100, ge=1, le=1000, description="Max rows to return"),
    db: Session = Depends(get_db),
):
    query = "SELECT * FROM marts.mart_salary_intelligence WHERE 1=1"
    params: dict = {}

    if category:
        query += " AND category_name ILIKE :category"
        params["category"] = f"%{category}%"
    if seniority:
        query += " AND seniority ILIKE :seniority"
        params["seniority"] = f"%{seniority}%"
    if governorate:
        query += " AND governorate ILIKE :governorate"
        params["governorate"] = f"%{governorate}%"

    query += " ORDER BY postings_with_salary DESC NULLS LAST"
    query += " OFFSET :skip LIMIT :limit"
    params["skip"] = skip
    params["limit"] = _clamp_limit(limit)

    rows = db.execute(text(query), params).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 2. In-Demand Roles
# ---------------------------------------------------------------------------
@app.get(
    "/api/in-demand-roles",
    response_model=List[InDemandRole],
    tags=["In-Demand Roles"],
)
def get_in_demand_roles(
    limit: int = Query(100, ge=1, le=1000, description="Top N roles by demand_rank"),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = (
        "SELECT * FROM marts.mart_in_demand_roles "
        "ORDER BY demand_rank ASC NULLS LAST "
        "OFFSET :skip LIMIT :limit"
    )
    rows = db.execute(
        text(query), {"skip": skip, "limit": _clamp_limit(limit)}
    ).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 3. Company Insights
# ---------------------------------------------------------------------------
@app.get(
    "/api/company-insights",
    response_model=List[CompanyInsight],
    tags=["Company Insights"],
)
def get_company_insights(
    limit: int = Query(100, ge=1, le=1000, description="Top N companies by hiring_rank"),
    governorate: Optional[str] = Query(None, description="Filter by top_governorate"),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = "SELECT * FROM marts.mart_company_insights WHERE 1=1"
    params: dict = {}

    if governorate:
        query += " AND top_governorate ILIKE :governorate"
        params["governorate"] = f"%{governorate}%"

    query += " ORDER BY hiring_rank ASC NULLS LAST"
    query += " OFFSET :skip LIMIT :limit"
    params["skip"] = skip
    params["limit"] = _clamp_limit(limit)

    rows = db.execute(text(query), params).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 4. Geographic Distribution
# ---------------------------------------------------------------------------
@app.get(
    "/api/geographic-distribution",
    response_model=List[GeographicDistribution],
    tags=["Geographic Distribution"],
)
def get_geographic_distribution(
    region: Optional[str] = Query(None, description="Filter by region"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = "SELECT * FROM marts.mart_geographic_distribution WHERE 1=1"
    params: dict = {}

    if region:
        query += " AND region ILIKE :region"
        params["region"] = f"%{region}%"

    query += " ORDER BY postings DESC NULLS LAST"
    query += " OFFSET :skip LIMIT :limit"
    params["skip"] = skip
    params["limit"] = _clamp_limit(limit)

    rows = db.execute(text(query), params).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 5. Skill Demand
# ---------------------------------------------------------------------------
@app.get(
    "/api/skill-demand",
    response_model=List[SkillDemand],
    tags=["Skill Demand"],
)
def get_skill_demand(
    category: Optional[str] = Query(None, description="Filter by category_name"),
    limit: int = Query(100, ge=1, le=1000, description="Top N skills"),
    skip: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = "SELECT * FROM marts.mart_skill_demand WHERE 1=1"
    params: dict = {}

    if category:
        query += " AND category_name ILIKE :category"
        params["category"] = f"%{category}%"

    query += " ORDER BY overall_skill_rank ASC NULLS LAST"
    query += " OFFSET :skip LIMIT :limit"
    params["skip"] = skip
    params["limit"] = _clamp_limit(limit)

    rows = db.execute(text(query), params).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 6. Hiring Trends
# ---------------------------------------------------------------------------
@app.get(
    "/api/hiring-trends",
    response_model=List[HiringTrend],
    tags=["Hiring Trends"],
)
def get_hiring_trends(
    category: Optional[str] = Query(None, description="Filter by category_name"),
    year: Optional[int] = Query(None, description="Filter by year"),
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = "SELECT * FROM marts.mart_hiring_trends WHERE 1=1"
    params: dict = {}

    if category:
        query += " AND category_name ILIKE :category"
        params["category"] = f"%{category}%"
    if year:
        query += " AND year = :year"
        params["year"] = year

    query += " ORDER BY year ASC, month ASC"
    query += " OFFSET :skip LIMIT :limit"
    params["skip"] = skip
    params["limit"] = _clamp_limit(limit)

    rows = db.execute(text(query), params).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# 7. Work Mode Breakdown
# ---------------------------------------------------------------------------
@app.get(
    "/api/work-mode-breakdown",
    response_model=List[WorkModeBreakdown],
    tags=["Work Mode Breakdown"],
)
def get_work_mode_breakdown(
    facet: Optional[str] = Query(None, description="Filter by facet (work_mode or employment_type)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = "SELECT * FROM marts.mart_work_mode_breakdown WHERE 1=1"
    params: dict = {}

    if facet:
        query += " AND facet ILIKE :facet"
        params["facet"] = f"%{facet}%"

    query += " ORDER BY postings DESC NULLS LAST"
    query += " OFFSET :skip LIMIT :limit"
    params["skip"] = skip
    params["limit"] = _clamp_limit(limit)

    rows = db.execute(text(query), params).mappings().all()
    return [dict(r) for r in rows]
