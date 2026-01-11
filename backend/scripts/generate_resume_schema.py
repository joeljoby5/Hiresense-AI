"""Write the frontend editor schema from the canonical validation model."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.resume.models import ResumeDocument

target = Path(__file__).resolve().parents[2] / "frontend/src/features/resumes/resume-schema.json"
schema = json.dumps(ResumeDocument.model_json_schema(), indent=2, ensure_ascii=False) + "\n"
if "--check" in sys.argv:
    if not target.exists() or target.read_text(encoding="utf-8") != schema:
        raise SystemExit("Resume editor schema is stale. Run backend/scripts/generate_resume_schema.py.")
else:
    target.write_text(schema, encoding="utf-8")
