"""
Pydantic response models — one per mart table.

These are used by FastAPI to auto-generate the Swagger docs and to
validate response shapes. Field names match the database columns exactly.
"""

from pydantic import BaseModel
from typing import Optional


class SalaryIntelligence(BaseModel):
    category_name: Optional[str] = None
    seniority: Optional[str] = None
    governorate: Optional[str] = None
    postings_with_salary: Optional[int] = None
    salary_floor: Optional[float] = None
    avg_salary_min: Optional[float] = None
    avg_salary_mid: Optional[float] = None
    avg_salary_max: Optional[float] = None
    salary_ceiling: Optional[float] = None
    median_salary_mid: Optional[float] = None
    currency: Optional[str] = None

    class Config:
        from_attributes = True


class InDemandRole(BaseModel):
    category_name: Optional[str] = None
    postings: Optional[int] = None
    hiring_companies: Optional[int] = None
    avg_salary_mid: Optional[float] = None
    remote_postings: Optional[int] = None
    demand_share_pct: Optional[float] = None
    postings_per_company: Optional[float] = None
    demand_rank: Optional[int] = None

    class Config:
        from_attributes = True


class CompanyInsight(BaseModel):
    company_name: Optional[str] = None
    postings: Optional[int] = None
    distinct_categories: Optional[int] = None
    distinct_governorates: Optional[int] = None
    avg_salary_mid: Optional[float] = None
    remote_postings: Optional[int] = None
    top_category: Optional[str] = None
    top_governorate: Optional[str] = None
    hiring_rank: Optional[int] = None

    class Config:
        from_attributes = True


class GeographicDistribution(BaseModel):
    region: Optional[str] = None
    governorate: Optional[str] = None
    postings: Optional[int] = None
    cities: Optional[int] = None
    hiring_companies: Optional[int] = None
    avg_salary_mid: Optional[float] = None
    remote_postings: Optional[int] = None
    postings_share_pct: Optional[float] = None

    class Config:
        from_attributes = True


class SkillDemand(BaseModel):
    skill_name: Optional[str] = None
    skill_category: Optional[str] = None
    category_name: Optional[str] = None
    postings: Optional[int] = None
    total_postings: Optional[float] = None
    overall_skill_rank: Optional[int] = None

    class Config:
        from_attributes = True


class HiringTrend(BaseModel):
    year: Optional[int] = None
    month: Optional[int] = None
    month_name: Optional[str] = None
    category_name: Optional[str] = None
    postings: Optional[int] = None
    hiring_companies: Optional[int] = None
    avg_salary_mid: Optional[float] = None

    class Config:
        from_attributes = True


class WorkModeBreakdown(BaseModel):
    facet: Optional[str] = None
    value: Optional[str] = None
    postings: Optional[int] = None
    share_pct: Optional[float] = None

    class Config:
        from_attributes = True
