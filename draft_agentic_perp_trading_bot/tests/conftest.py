"""Isolate CrewAI's local test storage from user data directories."""

import os


_TEST_STORAGE = f"/tmp/agentic-perp-crewai-tests-{os.getpid()}"
os.environ["XDG_DATA_HOME"] = _TEST_STORAGE
os.environ["CREWAI_STORAGE_DIR"] = _TEST_STORAGE
os.environ["CREWAI_DISABLE_TELEMETRY"] = "true"
os.environ["CREWAI_DISABLE_TRACKING"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"
