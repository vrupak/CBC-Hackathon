#!/bin/bash
# Start the FastAPI backend server
cd "$(dirname "$0")"
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

