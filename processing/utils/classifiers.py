"""Job-type classification for the cleaning layer.

Standardizes two facets the plan calls for ("Classify job types:
full-time, part-time, remote, hybrid, contract"):

* work_mode        -> 'remote' | 'hybrid' | 'on-site'
* employment_type  -> 'full-time' | 'part-time' | 'contract' | 'internship' | 'freelance'

Both default to the most common convention when no signal is present
(on-site / full-time), so downstream analytics always have a value.
"""

VALID_WORK_MODES = ("remote", "hybrid", "on-site")
VALID_EMPLOYMENT_TYPES = ("full-time", "part-time", "contract", "internship", "freelance")


def classify_work_mode(*texts: str) -> str:
    t = " ".join(x for x in texts if x).lower()
    if "hybrid" in t:
        return "hybrid"
    if "remote" in t or "work from home" in t or "wfh" in t or "عن بعد" in t:
        return "remote"
    return "on-site"


def classify_employment_type(*texts: str) -> str:
    t = " ".join(x for x in texts if x).lower()
    if "intern" in t or "تدريب" in t:
        return "internship"
    if "part-time" in t or "part time" in t or "دوام جزئي" in t:
        return "part-time"
    if "freelance" in t or "freelancer" in t:
        return "freelance"
    if "contract" in t or "temporary" in t or "عقد" in t:
        return "contract"
    return "full-time"
