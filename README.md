# SENSE Web
[![Run Tests](https://github.com/skwort/sense-web/actions/workflows/run-tests.yaml/badge.svg)](https://github.com/skwort/sense-web/actions/workflows/run-tests.yaml)

`sense-web` is the cloud backend for the SENSE Core data logger, responsible
for managing CoAP requests from devices and exposing a RESTful API for remote
device management.

## Quick Start

```bash
# Create and activate venv
uv venv
source .venv/bin/activate

# Install all dev dependencies with the sense_web package linked/editable
uv pip install -e .[dev]

# Run dev server
uvicorn sense_web.main:app --reload
```
