#!/bin/bash

# Setup python virtual environment in parent directory
cd ..
python -m venv .venv
source .venv/bin/activate

# Install requirements
python -m pip install -r requirements.txt

# Note: If this fails, comment out lgpio from the requirements.txt, since
# that package should only be installed on a Linux Single Board Computer and
# isn't necessary for frontend development