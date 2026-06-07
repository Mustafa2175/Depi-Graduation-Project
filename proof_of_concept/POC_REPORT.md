# Proof of Concept — Real Pipeline Run

_Generated 2026-06-07 03:28 from live data scraped from Egyptian job boards._

This is a genuine end-to-end run: data was **scraped live**, cleaned,
loaded into the PostgreSQL star schema, and transformed by dbt into the
analytics marts below. Numbers are real.

## Pipeline volumes

| Stage | Count |
| --- | --- |
| Bronze — raw scraped records | 155 |
| Silver — cleaned rows | 155 |
| Gold — unique postings (deduped) | 151 |
| dim_company | 99 |
| dim_location | 19 |
| dim_skill | 52 |
| bridge_job_skill (skill links) | 20 |

### Raw records by source

| source | raw_records |
| --- | --- |
| forasna | 20 |
| wuzzuf | 135 |

### Loaded postings by source

| source | postings |
| --- | --- |
| Wuzzuf | 132 |
| Forasna | 19 |

**Salary signal:** 6 postings carried a salary; average mid-point ≈ **9481 EGP** (range 175–25000).

## Sample analytics (from the dbt marts)

### Most in-demand roles

| category_name | postings | hiring_companies | avg_salary_mid | remote_postings | demand_share_pct | postings_per_company | demand_rank |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Other | 107 | 75 | 7659 | 0 | 70.86 | 1.43 | 1 |
| Backend Development | 11 | 9 |  | 2 | 7.28 | 1.22 | 2 |
| Full Stack Development | 9 | 8 |  | 0 | 5.96 | 1.13 | 3 |
| Mobile Development | 7 | 6 |  | 1 | 4.64 | 1.17 | 4 |
| Frontend Development | 5 | 5 |  | 0 | 3.31 | 1.00 | 5 |
| Project & Product Management | 4 | 2 |  | 0 | 2.65 | 2.00 | 6 |
| QA & Testing | 4 | 4 |  | 0 | 2.65 | 1.00 | 6 |
| IT Support & Networking | 2 | 2 |  | 0 | 1.32 | 1.00 | 8 |

### Top in-demand skills

| skill_name | skill_category | category_name | postings | total_postings | overall_skill_rank |
| --- | --- | --- | --- | --- | --- |
| .NET | framework | Backend Development | 4 | 4 | 1 |
| Flutter | framework | Mobile Development | 4 | 4 | 2 |
| Laravel | framework | Backend Development | 3 | 3 | 3 |
| Oracle | db | Other | 3 | 3 | 4 |
| Angular | framework | Frontend Development | 2 | 2 | 5 |
| Java | language | Other | 1 | 2 | 6 |
| Java | language | Frontend Development | 1 | 2 | 6 |
| Python | language | Full Stack Development | 1 | 2 | 8 |
| Python | language | Other | 1 | 2 | 8 |

### Top hiring companies

| company_name | postings | distinct_categories | distinct_governorates | avg_salary_mid | remote_postings | top_category | top_governorate | hiring_rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Confidential | 24 | 6 | 5 |  | 0 | Other | Cairo | 1 |
| Egypt Africa | 9 | 1 | 5 |  | 0 | Other | Cairo | 2 |
| Etisalat Egypt | 3 | 1 | 1 |  | 0 | Other | Cairo | 3 |
| SIPES | 3 | 1 | 1 |  | 0 | Other | Cairo | 3 |
| Vertex Technologies | 3 | 2 | 1 |  | 0 | Backend Development | Cairo | 3 |
| iBrokerage Ltd. | 3 | 2 | 1 |  | 3 | Backend Development | Cairo | 3 |
| الجبر للصناعه والاعمال | 2 | 1 | 1 |  | 0 | Other | Cairo | 7 |
| iucon Egypt | 2 | 1 | 1 |  | 0 | Full Stack Development | Giza | 7 |

### Geographic distribution

| region | governorate | postings | cities | hiring_companies | avg_salary_mid | remote_postings | postings_share_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Greater Cairo | Cairo | 102 | 8 | 69 | 8897 | 3 | 67.55 |
| Greater Cairo | Giza | 27 | 6 | 20 | 10650 | 0 | 17.88 |
| Coastal | Alexandria | 10 | 2 | 8 |  | 0 | 6.62 |
| Unknown | Egypt | 10 | 1 | 8 |  | 0 | 6.62 |
| Delta | Dakahlia | 1 | 1 | 1 |  | 0 | 0.66 |
| Delta | Sharqia | 1 | 1 | 1 |  | 0 | 0.66 |

### Work mode & employment type

| facet | value | postings | share_pct |
| --- | --- | --- | --- |
| employment_type | full-time | 145 | 96.03 |
| employment_type | internship | 5 | 3.31 |
| employment_type | contract | 1 | 0.66 |
| work_mode | on-site | 148 | 98.01 |
| work_mode | remote | 3 | 1.99 |

## Artifacts in this folder

- `marts/*.csv` — full export of every dbt mart
- `samples/raw_sample.json` — real raw records as scraped

## Honest notes / limitations

- Live scrapers run here: **Wuzzuf** and **Forasna** (pure `requests`).
  Bayt/Indeed/Jobzella need a real browser (Selenium/anti-bot) and were
  not run in this environment.
- Listing pages carry no full job description, so **skills** are derived
  from titles only — coverage is sparser than it would be with detail-page
  scraping. Salaries are present where the board exposes them.
- Volumes were intentionally capped (env `MAX_JOBS` / `MAX_PAGES`) to be
  polite to the sites; the pipeline scales to far larger runs (see
  `warehouse/stress_test.py`).
