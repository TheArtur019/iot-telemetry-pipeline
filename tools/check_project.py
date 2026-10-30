import ast
import sys
from pathlib import Path
 
root = Path(__file__).resolve().parents[1]
required = [
    'manage.py',
    'requirements.txt',
    'Dockerfile',
    'compose.yaml',
    'config/__init__.py',
    'config/settings.py',
    'config/urls.py',
    'services/__init__.py',
    'services/common.py',
    'services/init_topics.py',
    'services/generator.py',
    'services/processor.py',
    'services/validation.py',
    'monitoring/__init__.py',
    'monitoring/models.py',
    'monitoring/ingestion.py',
    'monitoring/views.py',
    'monitoring/tests.py',
    'monitoring/migrations/__init__.py',
    'monitoring/management/__init__.py',
    'monitoring/management/commands/__init__.py',
    'monitoring/management/commands/consume_events.py',
    'monitoring/templates/monitoring/index.html',
]
missing = [name for name in required if not (root / name).is_file()]
if "--require-migrations" in sys.argv:
    if not (root / "monitoring/migrations/0001_initial.py").is_file():
        missing.append("monitoring/migrations/0001_initial.py")
if missing:
    raise SystemExit("Missing files:\n" + "\n".join(missing))
for path in root.rglob("*.py"):
    ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
print("Project files and Python syntax: OK")