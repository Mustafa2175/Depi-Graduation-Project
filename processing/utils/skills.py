"""Skill / technology extraction (keyword-matching NLP).

Scans free text (job title + description + requirements) for known
technologies and returns a deduplicated list of *canonical* skill names.
The canonical names match the warehouse `dim_skill` seed exactly, so the
Silver layer and the star schema stay aligned.

Matching is case-insensitive and boundary-aware so that, e.g., "go"
matches "Go developer" but not "category", and "java" does not match
"javascript".
"""
import re


def _w(word: str) -> str:
    """Boundary-wrapped pattern for a plain keyword."""
    return r"(?<![a-z0-9])" + re.escape(word.lower()) + r"(?![a-z0-9])"


# canonical skill name -> list of regex alias patterns (lowercase)
_LEXICON = {
    # languages
    "Python":     [_w("python")],
    "Java":       [r"(?<![a-z0-9])java(?!script)(?![a-z0-9])"],
    "JavaScript": [_w("javascript")],
    "TypeScript": [_w("typescript")],
    "C#":         [r"(?<![a-z0-9])c#", _w("csharp")],
    "C++":        [r"(?<![a-z0-9])c\+\+"],
    "Go":         [r"(?<![a-z0-9])go(?:lang)?(?![a-z0-9])"],
    "PHP":        [_w("php")],
    "Kotlin":     [_w("kotlin")],
    "Swift":      [_w("swift")],
    "Ruby":       [_w("ruby")],
    "SQL":        [_w("sql")],
    "Scala":      [_w("scala")],
    # frameworks / libraries
    "Django":     [_w("django")],
    "Flask":      [_w("flask")],
    "FastAPI":    [_w("fastapi"), _w("fast api")],
    "Spring":     [_w("spring boot"), _w("spring")],
    "Laravel":    [_w("laravel")],
    ".NET":       [r"(?<![a-z0-9])\.net(?![a-z0-9])", _w("dotnet"), _w("asp.net")],
    "React":      [_w("react")],
    "Angular":    [_w("angular")],
    "Vue":        [_w("vue.js"), _w("vue")],
    "Node.js":    [_w("node.js"), _w("nodejs"), _w("node js"), _w("node")],
    "Next.js":    [_w("next.js"), _w("nextjs")],
    "Flutter":    [_w("flutter")],
    "Spark":      [_w("pyspark"), _w("spark")],
    "Pandas":     [_w("pandas")],
    "NumPy":      [_w("numpy")],
    "TensorFlow": [_w("tensorflow")],
    "PyTorch":    [_w("pytorch")],
    "Machine Learning": [_w("machine learning"), _w("deep learning")],
    # tools / platforms
    "Airflow":    [_w("airflow")],
    "dbt":        [_w("dbt")],
    "Docker":     [_w("docker")],
    "Kubernetes": [_w("kubernetes"), _w("k8s")],
    "Terraform":  [_w("terraform")],
    "Git":        [_w("github"), _w("gitlab"), _w("git")],
    "Tableau":    [_w("tableau")],
    "Power BI":   [_w("power bi"), _w("powerbi")],
    "REST API":   [_w("restful"), _w("rest api"), _w("rest")],
    "GraphQL":    [_w("graphql")],
    "Linux":      [_w("linux")],
    "Excel":      [_w("excel")],
    # databases
    "PostgreSQL": [_w("postgresql"), _w("postgres")],
    "MySQL":      [_w("mysql")],
    "MongoDB":    [_w("mongodb"), _w("mongo")],
    "Redis":      [_w("redis")],
    "Oracle":     [_w("oracle")],
    "SQL Server": [_w("sql server"), _w("mssql")],
    # cloud
    "AWS":        [_w("aws"), _w("amazon web services")],
    "Azure":      [_w("azure")],
    "GCP":        [_w("gcp"), _w("google cloud")],
}

# pre-compile for speed: canonical -> single combined regex
_COMPILED = {
    name: re.compile("|".join(f"(?:{p})" for p in patterns))
    for name, patterns in _LEXICON.items()
}


def extract_skills(*texts: str) -> list:
    """Return canonical skills found in any of the given texts (deduped, ordered)."""
    blob = " ".join(t for t in texts if t).lower()
    if not blob:
        return []
    return [name for name, rx in _COMPILED.items() if rx.search(blob)]


def extract_skills_str(*texts: str, sep: str = "|") -> str:
    """Convenience: skills as a single delimited string for CSV storage."""
    return sep.join(extract_skills(*texts))
