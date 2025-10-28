#!/usr/bin/env bash

# Con set -o errexit, el script se detiene en el primer error, así es más fácil detectar el problema.
set -o errexit

# Modify this line as needed for your package manager (pip, poetry, etc.)
pip install -r requirements.txt

# Convert static asset files
python manage.py collectstatic --no-input

# Apply any outstanding database migrations
python manage.py migrate