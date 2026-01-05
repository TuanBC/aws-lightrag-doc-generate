"""AWS Lambda handler using Mangum adapter for FastAPI."""

# CRITICAL: Set PATH before ANY imports to ensure GitPython can find git
# GitPython checks for git at module import time, so this must happen first
import os

# Ensure /usr/bin is in PATH for git (Lambda base image installs git there)
current_path = os.environ.get("PATH", "")
if "/usr/bin" not in current_path:
    os.environ["PATH"] = f"/usr/bin:{current_path}"

# Set other git-related environment variables for Lambda compatibility
os.environ.setdefault("HOME", "/tmp")
os.environ.setdefault("TMPDIR", "/tmp")
os.environ.setdefault("GIT_PYTHON_GIT_EXECUTABLE", "/usr/bin/git")
os.environ.setdefault("GIT_CONFIG_NOSYSTEM", "1")

# Now safe to import the rest
from mangum import Mangum  # noqa: E402

from app.main import app  # noqa: E402

# Mangum wraps FastAPI for Lambda/API Gateway
handler = Mangum(app, lifespan="off")
