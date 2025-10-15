#!/bin/bash
# Run kvs-infer with proper PYTHONPATH

# Set the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH}"

# Run the application
python3.11 -m kvs_infer.app "$@"
