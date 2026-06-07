-- =====================================================================
-- Job Market Tracker  ·  Phase 4 — Seed / Reference Data
-- Idempotent: every INSERT uses ON CONFLICT DO NOTHING / DO UPDATE.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Egyptian governorates (must exist before dim_location FK is satisfied)
-- Includes the loader's fallbacks: 'Egypt' (unknown gov) is allowed.
-- ---------------------------------------------------------------------
INSERT INTO ref_governorate (governorate, region) VALUES
    ('Cairo',       'Greater Cairo'),
    ('Giza',        'Greater Cairo'),
    ('Qalyubia',    'Greater Cairo'),
    ('Alexandria',  'Coastal'),
    ('Dakahlia',    'Delta'),
    ('Gharbia',     'Delta'),
    ('Sharqia',     'Delta'),
    ('Monufia',     'Delta'),
    ('Beheira',     'Delta'),
    ('Kafr El Sheikh','Delta'),
    ('Damietta',    'Delta'),
    ('Port Said',   'Canal'),
    ('Ismailia',    'Canal'),
    ('Suez',        'Canal'),
    ('Faiyum',      'Upper Egypt'),
    ('Beni Suef',   'Upper Egypt'),
    ('Minya',       'Upper Egypt'),
    ('Asyut',       'Upper Egypt'),
    ('Sohag',       'Upper Egypt'),
    ('Qena',        'Upper Egypt'),
    ('Luxor',       'Upper Egypt'),
    ('Aswan',       'Upper Egypt'),
    ('Red Sea',     'Coastal'),
    ('Matrouh',     'Coastal'),
    ('North Sinai', 'Canal'),
    ('South Sinai', 'Coastal'),
    ('New Valley',  'Upper Egypt'),
    ('Egypt',       'Unknown')              -- fallback bucket for unmapped locations
ON CONFLICT (governorate) DO NOTHING;

-- ---------------------------------------------------------------------
-- Sources (the five scrapers in scraping/)
-- ---------------------------------------------------------------------
INSERT INTO dim_source (source_name, display_name, base_url) VALUES
    ('wuzzuf',   'Wuzzuf',   'https://wuzzuf.net'),
    ('bayt',     'Bayt',     'https://www.bayt.com'),
    ('indeed',   'Indeed',   'https://eg.indeed.com'),
    ('forasna',  'Forasna',  'https://forasna.com'),
    ('jobzella', 'Jobzella', 'https://www.jobzella.com')
ON CONFLICT (source_name) DO UPDATE
    SET display_name = EXCLUDED.display_name,
        base_url     = EXCLUDED.base_url;

-- ---------------------------------------------------------------------
-- Job categories. `keywords` is matched (case-insensitive, substring)
-- against title_clean by the loader to assign category_key.
-- Order matters conceptually but the loader scores all and picks the
-- best match; 'Other' is the catch-all when nothing matches.
-- ---------------------------------------------------------------------
INSERT INTO dim_job_category (category_name, keywords, description) VALUES
    ('Data Engineering',
        ARRAY['data engineer','etl','airflow','dbt','spark','pipeline','warehouse','big data'],
        'Building and maintaining data pipelines and platforms'),
    ('Data Science & Analytics',
        ARRAY['data scientist','data analyst','analytics','machine learning','ml engineer','ai engineer','bi ','business intelligence','power bi','tableau'],
        'Analysis, modelling and insight generation'),
    ('Backend Development',
        ARRAY['backend','back-end','back end','django','flask','fastapi','spring','node','.net','laravel','php developer','golang','rails'],
        'Server-side application development'),
    ('Frontend Development',
        ARRAY['frontend','front-end','front end','react','angular','vue','ui developer','javascript developer'],
        'Client-side / UI application development'),
    ('Full Stack Development',
        ARRAY['full stack','full-stack','fullstack','mern','mean'],
        'Combined frontend and backend development'),
    ('Mobile Development',
        ARRAY['mobile','android','ios','flutter','react native','kotlin developer','swift'],
        'Mobile application development'),
    ('DevOps & Cloud',
        ARRAY['devops','sre','site reliability','cloud engineer','aws','azure','gcp','kubernetes','docker','infrastructure'],
        'Infrastructure, deployment and reliability'),
    ('QA & Testing',
        ARRAY['qa','quality assurance','tester','test engineer','automation engineer','sdet'],
        'Software quality assurance and testing'),
    ('Cybersecurity',
        ARRAY['security','cyber','penetration','soc analyst','infosec'],
        'Information and application security'),
    ('Database Administration',
        ARRAY['dba','database administrator','sql server','oracle dba','postgres'],
        'Database administration and tuning'),
    ('UI/UX Design',
        ARRAY['ux','ui/ux','product designer','figma','graphic designer'],
        'Product and experience design'),
    ('IT Support & Networking',
        ARRAY['it support','help desk','helpdesk','system administrator','sysadmin','network engineer','technical support'],
        'IT operations, support and networking'),
    ('Project & Product Management',
        ARRAY['project manager','product manager','scrum master','product owner','program manager'],
        'Delivery and product management'),
    ('Other',
        ARRAY[]::TEXT[],
        'Uncategorised / catch-all')
ON CONFLICT (category_name) DO UPDATE
    SET keywords    = EXCLUDED.keywords,
        description = EXCLUDED.description;

-- ---------------------------------------------------------------------
-- Reference skills. The loader detects these as substrings of
-- title_clean and links them via bridge_job_skill. (Once the Silver
-- layer adds a dedicated skills field, the same dimension is reused.)
-- ---------------------------------------------------------------------
INSERT INTO dim_skill (skill_name, skill_category) VALUES
    ('Python','language'), ('Java','language'), ('JavaScript','language'),
    ('TypeScript','language'), ('C#','language'), ('C++','language'),
    ('Go','language'), ('PHP','language'), ('Kotlin','language'),
    ('Swift','language'), ('Ruby','language'), ('SQL','language'),
    ('Scala','language'),
    ('Django','framework'), ('Flask','framework'), ('FastAPI','framework'),
    ('Spring','framework'), ('Laravel','framework'), ('.NET','framework'),
    ('React','framework'), ('Angular','framework'), ('Vue','framework'),
    ('Node.js','framework'), ('Next.js','framework'), ('Flutter','framework'),
    ('Spark','framework'), ('Airflow','tool'), ('dbt','tool'),
    ('Docker','tool'), ('Kubernetes','tool'), ('Terraform','tool'),
    ('Git','tool'), ('Tableau','tool'), ('Power BI','tool'),
    ('PostgreSQL','db'), ('MySQL','db'), ('MongoDB','db'),
    ('Redis','db'), ('Oracle','db'), ('SQL Server','db'),
    ('AWS','cloud'), ('Azure','cloud'), ('GCP','cloud'),
    ('Pandas','framework'), ('NumPy','framework'), ('TensorFlow','framework'),
    ('PyTorch','framework'), ('Machine Learning','tool'), ('REST API','tool'),
    ('GraphQL','tool'), ('Linux','tool'), ('Excel','tool')
ON CONFLICT (skill_name) DO NOTHING;
