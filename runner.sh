
#!/bin/bash

set -e

# Activate virtual environment only if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 portfolio_signals.py mongodb+srv://bhandekunal16:SppcHRFdBS74An8v@cluster0.xxevqv7.mongodb.net
