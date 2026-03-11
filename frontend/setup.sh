#!/bin/bash

# Setup python virtual environment
python -m venv .venv
source .venv/bin/activate

# Install frontend requirements
python -m pip install -r ./frontend/requirements.txt

# Make scripts executable
chmod +x ./frontend/scripts/tailwind.sh
