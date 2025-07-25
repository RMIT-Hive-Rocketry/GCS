#!/bin/bash

# Setup python virtual environment
python -m venv .venv
source .venv/bin/activate

# Install frontend requirements
python -m pip install -r ./frontend/requirements.txt
