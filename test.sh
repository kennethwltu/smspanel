#!/bin/bash

echo "=== Running pytest with coverage ==="
pytest --cov=src --cov-report=term-missing

echo "=== Running ruff check ==="
ruff check .

echo "=== Installing Playwright dependencies ==="
if [ -f "test_ui/requirements-playwright.txt" ]; then
    pip install -r test_ui/requirements-playwright.txt
    playwright install
else
    echo "Warning: test_ui/requirements-playwright.txt not found"
fi

echo "=== Running UI tests ==="
python -m pytest test_ui/1_test_login_page_baseline.py -v 
python -m pytest test_ui/2_test_dashboard_page_baseline.py -v 
python -m pytest test_ui/3_test_compose_page_baseline.py -v 
python -m pytest test_ui/4_test_admin_page_baseline.py -v 
python -m pytest test_ui/5_test_history_page_baseline.py -v
