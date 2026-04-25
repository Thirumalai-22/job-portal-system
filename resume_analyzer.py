"""
Lightweight resume analyzer using keyword matching.
Works without ML libraries — pure Python.
"""
import re
import os


COMMON_SKILLS = [
    "python", "java", "javascript", "react", "node", "flask", "django",
    "sql", "mysql", "postgresql", "mongodb", "html", "css", "bootstrap",
    "git", "docker", "aws", "machine learning", "deep learning", "tensorflow",
    "c++", "c#", "php", "laravel", "spring", "rest", "api", "agile", "scrum",
    "linux", "excel", "powerbi", "tableau", "communication", "leadership",
]


def extract_text_from_path(filepath):
    """Try to extract text from PDF/DOCX. Returns empty string if libs not available."""
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".pdf":
            from pdfminer.high_level import extract_text
            return extract_text(filepath)
        elif ext in (".doc", ".docx"):
            import docx
            doc = docx.Document(filepath)
            return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        pass
    return ""


def analyze_resume(resume_path, job_skills_str):
    """
    Compare resume text against job required skills.
    Returns dict with score, matched_skills, missing_skills.
    """
    if not resume_path:
        return {"score": 0, "matched": [], "missing": [], "error": "No resume uploaded"}

    upload_folder = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..", "static", "uploads", "resumes"
    )
    filepath = os.path.join(upload_folder, resume_path)

    resume_text = extract_text_from_path(filepath).lower()

    # Parse job required skills
    job_skills = [s.strip().lower() for s in re.split(r"[,;\n]", job_skills_str or "") if s.strip()]
    if not job_skills:
        job_skills = COMMON_SKILLS[:10]

    matched = [s for s in job_skills if s in resume_text]
    missing = [s for s in job_skills if s not in resume_text]

    score = int((len(matched) / len(job_skills)) * 100) if job_skills else 0

    return {
        "score": score,
        "matched": matched,
        "missing": missing,
        "total_required": len(job_skills),
        "error": None if resume_text else "Could not read resume file (install pdfminer.six / python-docx)",
    }


def recommend_jobs(student_skills_str, jobs):
    """
    Rank jobs by skill overlap with student skills.
    Returns list of (job, score) sorted descending.
    """
    student_skills = set(s.strip().lower() for s in re.split(r"[,;\n ]", student_skills_str or "") if s.strip())
    ranked = []
    for job in jobs:
        required = set(s.strip().lower() for s in re.split(r"[,;\n]", job["skills_required"] or "") if s.strip())
        if not required:
            score = 0
        else:
            score = int(len(student_skills & required) / len(required) * 100)
        ranked.append((job, score))
    ranked.sort(key=lambda x: x[1], reverse=True)
    return ranked
