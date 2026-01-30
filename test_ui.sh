#!/bin/bash

cd test_ui

# Install dependencies
pip install -r requirements-playwright.txt
playwright install

python -m pytest 1_test_login_page_baseline.py -v 
python -m pytest 2_test_dashboard_page_baseline.py -v 
python -m pytest 3_test_compose_page_baseline.py -v 
python -m pytest 4_test_admin_page_baseline.py -v 
python -m pytest 5_test_history_page_baseline.py -v
