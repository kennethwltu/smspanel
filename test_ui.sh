#!/bin/bash

# Install dependencies
pip install -r requirements-playwright.txt
playwright install

python -m pytest test_ui/1_test_login_page_baseline.py -v 
python -m pytest test_ui/2_test_dashboard_page_baseline.py -v 
python -m pytest test_ui/3_test_compose_page_baseline.py -v 
python -m pytest test_ui/4_test_admin_page_baseline.py -v 
python -m pytest test_ui/5_test_history_page_baseline.py -v
