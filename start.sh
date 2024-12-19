#!/bin/bash
echo "Current directory: $(pwd)"
echo "Listing files:"
ls -la
echo "Installing requirements..."
pip install -r requirements.txt
echo "Starting bot..."
python3 app.py 