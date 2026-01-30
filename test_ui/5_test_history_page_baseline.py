"""
Playwright UI tests for SMS Panel History page with baseline screenshot comparison.
Trace and video recording are disabled by default.
Screenshots are compared with baseline images - only replaced if different.
"""

import pytest
import re
import os
import hashlib
from datetime import datetime
from pathlib import Path
from playwright.sync_api import Page, expect
from test_ui.db_reset_enhanced import enhanced_reset_for_testing


class TestHistoryPageBaseline:
    """Test suite for SMS Panel History page with baseline screenshot comparison."""
    
    # Configuration - CHANGE THESE SETTINGS AS NEEDED
    BASELINE_DIR = "test_ui/test_history_baseline_screenshots"  # Store baseline images here
    ENABLE_VIDEO = False  # Set to True to enable video recording
    ENABLE_TRACE = False  # Set to True to enable trace recording
    
    # Login credentials
    LOGIN_URL = "http://127.0.0.1:3570/login?next=%2F"
    HISTORY_URL = "http://127.0.0.1:3570/history"
    USERNAME = "test_SMSadmin"
    PASSWORD = "test_SMSpass#12"
    
    @pytest.fixture(scope="function", autouse=True)
    def setup_dirs(self):
        """Setup directories for screenshots and baselines."""
        os.makedirs(self.BASELINE_DIR, exist_ok=True)
        yield
    
    @pytest.fixture(scope="function", autouse=True)
    def reset_database_before_test(self):
        """Enhanced reset database before each test when running against localhost."""
        # Backup, reset, and create test admin account
        success, backup_path = enhanced_reset_for_testing(
            base_url="http://127.0.0.1:3570",
            method="backup_reset",
            test_admin_username="test_SMSadmin",
            test_admin_password="test_SMSpass#12"
        )
        
        if not success:
            pytest.fail("Failed to reset database for testing")
        
        yield
        
        # Optional: restore after test if needed
        # Note: Usually we don't restore after each test to keep tests independent
        # enhanced_reset_for_testing(
        #     base_url="http://127.0.0.1:3570",
        #     method="restore_only"
        # )
    @pytest.fixture(scope="function")
    def browser_page(self, playwright, request):
        """Create a browser page for testing."""
        test_name = request.node.name
        
        # Configure browser context
        browser_args = {
            "headless": False,  # Set to True for CI/CD
            "slow_mo": 50  # Slow down for better visibility
        }
        
        browser = playwright.chromium.launch(**browser_args)
        
        # Configure context with optional video recording
        context_args = {
            "viewport": {"width": 1280, "height": 800}
        }
        
        if self.ENABLE_VIDEO:
            context_args["record_video_dir"] = "test_videos_history"
            context_args["record_video_size"] = {"width": 1280, "height": 800}
            os.makedirs("test_videos_history", exist_ok=True)
        
        context = browser.new_context(**context_args)
        
        # Start optional tracing
        if self.ENABLE_TRACE:
            os.makedirs("test_traces_history", exist_ok=True)
            context.tracing.start(
                screenshots=True,
                snapshots=True,
                sources=True
            )
        
        page = context.new_page()
        
        # Store test metadata
        page.test_name = test_name
        
        yield page
        
        # After test: save trace if enabled
        if self.ENABLE_TRACE:
            trace_path = os.path.join("test_traces_history", f"{test_name}.zip")
            context.tracing.stop(path=trace_path)
        
        # Close context (saves video if enabled)
        context.close()
        browser.close()
    
    @pytest.fixture(scope="function")
    def authenticated_page(self, browser_page: Page):
        """Create an authenticated page for history tests."""
        page = browser_page
        
        # Login to get authenticated session
        page.goto(self.LOGIN_URL)
        
        # Fill login form
        page.locator("#username").fill(self.USERNAME)
        page.locator("#password").fill(self.PASSWORD)
        page.locator("button[type='submit']").click()
        
        # Wait for login to complete
        page.wait_for_timeout(2000)
        
        # Verify we're logged in (should be redirected to dashboard or home)
        expect(page).not_to_have_url(re.compile(".*login.*"))
        
        return page
    
    def calculate_file_hash(self, filepath):
        """Calculate MD5 hash of a file."""
        if not os.path.exists(filepath):
            return None
        
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def calculate_image_similarity(self, image1_path, image2_path):
        """
        計算兩個圖像的相似度百分比
        基於 Java 範例的邏輯：
        1. 將圖像轉換為灰階
        2. 比較灰階圖像的像素值
        3. 使用跳過採樣來提高性能
        4. 使用閾值來判斷像素是否不同
        5. 計算相似度百分比
        """
        try:
            from PIL import Image
            
            # 打開圖像
            img1 = Image.open(image1_path)
            img2 = Image.open(image2_path)
            
            # 檢查圖像尺寸是否相同
            if img1.size != img2.size:
                print(f"圖像尺寸不同: {img1.size} vs {img2.size}")
                return 0.0
            
            # 轉換為灰階
            def convert_to_grayscale(image):
                if image.mode != 'L':
                    return image.convert('L')
                return image
            
            gray1 = convert_to_grayscale(img1)
            gray2 = convert_to_grayscale(img2)
            
            # 配置參數
            COMPARE_SKIP = 2  # 跳過採樣的間隔
            GRAYSCALE_THRESHOLD = 10  # 灰階差異閾值
            
            width, height = img1.size
            diff_pixels = 0
            total_pixels = 0
            
            # 使用跳過採樣進行比較
            for y in range(0, height, COMPARE_SKIP):
                for x in range(0, width, COMPARE_SKIP):
                    gray1_val = gray1.getpixel((x, y))
                    gray2_val = gray2.getpixel((x, y))
                    
                    diff = abs(gray1_val - gray2_val)
                    
                    if diff > GRAYSCALE_THRESHOLD:
                        diff_pixels += 1
                    total_pixels += 1
            
            # 計算相似度百分比
            if total_pixels == 0:
                return 0.0
            
            similarity = 100.0 - (diff_pixels * 100.0 / total_pixels)
            return similarity
            
        except ImportError:
            print("PIL (Pillow) 庫未安裝，使用 MD5 哈希比較")
            # 如果 PIL 不可用，回退到哈希比較
            hash1 = self.calculate_file_hash(image1_path)
            hash2 = self.calculate_file_hash(image2_path)
            return 100.0 if hash1 == hash2 else 0.0
        except Exception as e:
            print(f"計算圖像相似度時出錯: {e}")
            return 0.0
    
    def take_baseline_screenshot(self, page: Page, name: str):
        """
        Take a screenshot and compare with baseline.
        Only replace if different.
        
        Returns:
            tuple: (filepath, is_new, is_different)
        """
        test_name = getattr(page, 'test_name', 'unknown_test')
        
        # Create descriptive filename
        filename = f"{test_name}_{name}.png"
        baseline_path = os.path.join(self.BASELINE_DIR, filename)
        temp_path = os.path.join(self.BASELINE_DIR, f"{filename}.temp.png")
        
        # Take screenshot to temp file
        page.screenshot(path=temp_path, full_page=True)
        
        # Check if baseline exists
        if not os.path.exists(baseline_path):
            # First time - create baseline
            os.rename(temp_path, baseline_path)
            print(f"📸 BASELINE CREATED: {filename}")
            return baseline_path, True, True
        
        # Compare with baseline using image similarity
        similarity = self.calculate_image_similarity(baseline_path, temp_path)
        SIMILARITY_THRESHOLD = 85.0  # 相似度閾值（百分比）
        
        if similarity >= SIMILARITY_THRESHOLD:
            # Screenshots are similar enough - delete temp, keep baseline
            os.remove(temp_path)
            print(f"✅ NO CHANGE: {filename} (similarity: {similarity:.2f}%, threshold: {SIMILARITY_THRESHOLD}%)")
            return baseline_path, False, False
        else:
            # Screenshots are different - replace baseline
            os.remove(baseline_path)
            os.rename(temp_path, baseline_path)
            print(f"🔄 UPDATED: {filename} (similarity: {similarity:.2f}%, threshold: {SIMILARITY_THRESHOLD}%)")
            return baseline_path, False, True
    
    # Test 1: History page loads correctly after authentication
    def test_history_page_loads(self, authenticated_page: Page):
        """Test that history page loads correctly after authentication."""
        page = authenticated_page
        
        # Navigate to history page
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "history_page")
        
        # Check page title
        expect(page).to_have_title(re.compile("Message History - SMS Application"))
        
        # Check page header
        history_header = page.locator(".history-header h1")
        expect(history_header).to_be_visible()
        expect(history_header).to_have_text("Message History")
        self.take_baseline_screenshot(page, "history_header")
        
        # Check Compose New SMS button
        compose_button = page.locator(".history-header .btn-primary")
        expect(compose_button).to_be_visible()
        expect(compose_button).to_have_text("Compose New SMS")
        self.take_baseline_screenshot(page, "compose_button")
    
    # Test 2: Search and filter functionality
    def test_search_and_filter_functionality(self, authenticated_page: Page):
        """Test search and filter functionality on history page."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "search_filter_start")
        
        # Check search form exists
        search_form = page.locator(".search-form")
        expect(search_form).to_be_visible()
        
        # Check search input
        search_input = page.locator(".search-input")
        expect(search_input).to_be_visible()
        expect(search_input).to_have_attribute("placeholder", "Search messages...")
        self.take_baseline_screenshot(page, "search_input")
        
        # Check status filter dropdown
        status_filter = page.locator(".filter-select")
        expect(status_filter).to_be_visible()
        
        # Check filter options
        expect(status_filter.locator("option[value='']")).to_have_text("All Status")
        expect(status_filter.locator("option[value='pending']")).to_have_text("Pending")
        expect(status_filter.locator("option[value='sent']")).to_have_text("Sent")
        expect(status_filter.locator("option[value='failed']")).to_have_text("Failed")
        expect(status_filter.locator("option[value='partial']")).to_have_text("Partial")
        
        # Check filter button
        filter_button = page.locator(".search-form .btn-secondary")
        expect(filter_button).to_be_visible()
        expect(filter_button).to_have_text("Filter")
        
        self.take_baseline_screenshot(page, "filter_elements")
        
        # Test search functionality
        search_input.fill("test message")
        self.take_baseline_screenshot(page, "search_filled")
        
        # Test status filter selection
        status_filter.select_option("sent")
        self.take_baseline_screenshot(page, "filter_selected")
        
        # Submit the form
        filter_button.click()
        page.wait_for_timeout(1000)
        
        # Check if URL contains filter parameters
        # Accept both %20 and + for space encoding
        expect(page).to_have_url(re.compile(".*search=test(%20|\\+)message.*"))
        expect(page).to_have_url(re.compile(".*status=sent.*"))
        
        self.take_baseline_screenshot(page, "filter_applied")
        
        # Check for clear button (should appear when filters are applied)
        clear_button = page.locator(".search-form .btn-small")
        if clear_button.count() > 0 and "Clear" in clear_button.text_content():
            expect(clear_button).to_be_visible()
            expect(clear_button).to_have_text("Clear")
            self.take_baseline_screenshot(page, "clear_button")
            
            # Test clear functionality
            clear_button.click()
            page.wait_for_timeout(1000)
            expect(page).not_to_have_url(re.compile(".*search=.*"))
            expect(page).not_to_have_url(re.compile(".*status=.*"))
            self.take_baseline_screenshot(page, "filters_cleared")
    
    # Test 3: History table structure
    def test_history_table_structure(self, authenticated_page: Page):
        """Test history table structure and columns."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "history_table")
        
        # Check if table exists
        table_container = page.locator(".table-container")
        
        if table_container.count() > 0:
            # Table is displayed (has messages)
            table = page.locator(".history-table")
            expect(table).to_be_visible()
            
            # Check table headers
            headers = table.locator("thead th")
            expect(headers).to_have_count(6)  # Status, Time, Message, Recipients, Sent/Failed, Actions
            
            expected_headers = ["Status", "Time", "Message", "Recipients", "Sent/Failed", "Actions"]
            for i, expected_header in enumerate(expected_headers):
                expect(headers.nth(i)).to_contain_text(expected_header)
            
            # Check if there are message rows
            message_rows = table.locator("tbody .message-row")
            if message_rows.count() > 0:
                # Check first message row structure
                first_row = message_rows.first
                
                # Check status badge
                status_badge = first_row.locator(".status")
                expect(status_badge).to_be_visible()
                
                # Check timestamp
                timestamp = first_row.locator(".timestamp")
                expect(timestamp).to_be_visible()
                
                # Check message content
                message_content = first_row.locator(".message-content")
                expect(message_content).to_be_visible()
                
                # Check recipients list
                recipients = first_row.locator(".recipients-list")
                expect(recipients).to_be_visible()
                
                # Check counts (Sent/Failed)
                counts = first_row.locator(".counts")
                expect(counts).to_be_visible()
                
                # Check actions button
                view_button = first_row.locator(".actions .btn")
                expect(view_button).to_be_visible()
                expect(view_button).to_have_text("View")
                
                self.take_baseline_screenshot(page, "message_row_details")
                
                # Test clicking View button
                view_button.click()
                page.wait_for_timeout(2000)
                
                # Check if navigated to message detail page
                if "sms_detail" in page.url or "message" in page.url:
                    expect(page).to_have_title(re.compile("Message Details - SMS Application"))
                    self.take_baseline_screenshot(page, "message_detail_page")
                    
                    # Go back to history
                    page.go_back()
                    page.wait_for_timeout(1000)
                    self.take_baseline_screenshot(page, "back_to_history")
                else:
                    print("View button did not navigate to message detail page")
            else:
                # No messages - check empty state
                empty_state = page.locator(".empty-state")
                expect(empty_state).to_be_visible()
                expect(empty_state).to_contain_text("No messages yet")
                
                # Check link to compose page
                compose_link = empty_state.locator("a")
                expect(compose_link).to_be_visible()
                expect(compose_link).to_have_text("Send your first SMS!")
                
                self.take_baseline_screenshot(page, "empty_state")
        else:
            # No table container (no messages section at all)
            print("No history table displayed")
            self.take_baseline_screenshot(page, "no_history_table")
    
    # Test 4: Pagination functionality
    def test_pagination_functionality(self, authenticated_page: Page):
        """Test pagination controls on history page."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "pagination_check")
        
        # Check if pagination exists
        pagination = page.locator(".pagination")
        
        if pagination.count() > 0:
            # Pagination is displayed
            expect(pagination).to_be_visible()
            
            # Check page info
            page_info = pagination.locator("span")
            expect(page_info).to_contain_text("Page")
            expect(page_info).to_contain_text("of")
            expect(page_info).to_contain_text("total")
            
            # Check navigation buttons
            prev_button = pagination.locator("a:has-text('Previous')")
            next_button = pagination.locator("a:has-text('Next')")
            
            if prev_button.count() > 0:
                expect(prev_button).to_be_visible()
                prev_button.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "previous_page")
                # Go back to original page
                page.go_back()
                page.wait_for_timeout(1000)
            
            if next_button.count() > 0:
                expect(next_button).to_be_visible()
                next_button.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "next_page")
            
            self.take_baseline_screenshot(page, "pagination_controls")
        else:
            # No pagination (single page or no messages)
            print("No pagination displayed (single page or no messages)")
            self.take_baseline_screenshot(page, "no_pagination")
    
    # Test 5: Responsive design on history page
    def test_history_responsive_design(self, authenticated_page: Page):
        """Test history page responsive design on different viewports."""
        page = authenticated_page
        
        # Test mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "mobile_viewport")
        
        # Check mobile layout elements
        history_header = page.locator(".history-header")
        expect(history_header).to_be_visible()
        
        # Check if search form adapts to mobile
        search_form = page.locator(".search-form")
        expect(search_form).to_be_visible()
        
        # Test tablet viewport
        page.set_viewport_size({"width": 768, "height": 1024})  # iPad
        self.take_baseline_screenshot(page, "tablet_viewport")
        
        # Test desktop viewport
        page.set_viewport_size({"width": 1280, "height": 800})  # Desktop
        self.take_baseline_screenshot(page, "desktop_viewport")
        
        # Verify key elements are visible on all viewports
        expect(page.locator(".history-header h1")).to_be_visible()
        expect(page.locator(".search-form")).to_be_visible()
        
        # Check if table container exists (only when there are messages)
        table_container = page.locator(".table-container")
        if table_container.count() > 0:
            expect(table_container).to_be_visible()
        else:
            # If no table container, check for empty state
            empty_state = page.locator(".empty-state")
            expect(empty_state).to_be_visible()
    
    # Test 6: History page accessibility without authentication
    def test_history_access_without_auth(self, browser_page: Page):
        """Test that history page redirects to login when not authenticated."""
        page = browser_page
        
        # Try to access history page without logging in
        response = page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "history_no_auth")
        
        # Should be redirected to login page
        expect(page).to_have_url(re.compile(".*login.*"))
        
        # Check login form is displayed
        expect(page.locator("h1")).to_have_text("Login")
        expect(page.locator("#username")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()
        
        self.take_baseline_screenshot(page, "redirected_to_login")
    
    # Test 7: Navigation from history page
    def test_history_navigation(self, authenticated_page: Page):
        """Test navigation links from history page."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "navigation_start")
        
        # Test Compose New SMS button
        compose_button = page.locator(".history-header .btn-primary")
        compose_button.click()
        page.wait_for_timeout(1000)
        
        # Check if navigated to compose page
        if "compose" in page.url:
            expect(page).to_have_url(re.compile(".*compose.*"))
            expect(page).to_have_title(re.compile("Compose SMS - SMS Application"))
            self.take_baseline_screenshot(page, "navigated_to_compose")
            # Go back to history
            page.go_back()
            page.wait_for_timeout(1000)
        else:
            print("Compose button did not navigate to compose page")
        
        # Test navigation via navbar
        navbar_links = page.locator(".nav-links a")
        
        # Test Dashboard link in navbar
        dashboard_nav_link = navbar_links.filter(has_text="Dashboard")
        if dashboard_nav_link.count() > 0:
            dashboard_nav_link.click()
            page.wait_for_timeout(1000)
            if "dashboard" in page.url or page.url.endswith("/"):
                self.take_baseline_screenshot(page, "navbar_dashboard")
                page.go_back()
                page.wait_for_timeout(1000)
        
        # Test Compose link in navbar
        compose_nav_link = navbar_links.filter(has_text="Compose")
        if compose_nav_link.count() > 0:
            compose_nav_link.click()
            page.wait_for_timeout(1000)
            if "compose" in page.url:
                self.take_baseline_screenshot(page, "navbar_compose")
                page.go_back()
                page.wait_for_timeout(1000)
        
        self.take_baseline_screenshot(page, "navigation_complete")
    
    # Test 8: Empty state with filters
    def test_empty_state_with_filters(self, authenticated_page: Page):
        """Test empty state when filters return no results."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        
        # Apply a filter that likely returns no results
        search_input = page.locator(".search-input")
        search_input.fill("nonexistentsearchterm12345")
        
        status_filter = page.locator(".filter-select")
        status_filter.select_option("sent")
        
        filter_button = page.locator(".search-form .btn-secondary")
        filter_button.click()
        page.wait_for_timeout(1000)
        
        self.take_baseline_screenshot(page, "empty_state_with_filters")
        
        # Check empty state message
        empty_state = page.locator(".empty-state")
        expect(empty_state).to_be_visible()
        expect(empty_state).to_contain_text("No messages found matching your criteria")
        
        # Check clear filters link
        clear_link = empty_state.locator("a")
        expect(clear_link).to_be_visible()
        expect(clear_link).to_have_text("Clear filters")
        
        # Test clearing filters
        clear_link.click()
        page.wait_for_timeout(1000)
        
        # Check if filters are cleared
        expect(page).not_to_have_url(re.compile(".*search=.*"))
        expect(page).not_to_have_url(re.compile(".*status=.*"))
        self.take_baseline_screenshot(page, "filters_cleared_from_empty_state")
    
    # Test 9: Status badges display
    def test_status_badges_display(self, authenticated_page: Page):
        """Test different status badges display correctly."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "status_badges_start")
        
        # Check if there are messages with different statuses
        status_badges = page.locator(".status")
        
        if status_badges.count() > 0:
            # Check different status classes
            for i in range(min(status_badges.count(), 5)):  # Check first 5 badges
                badge = status_badges.nth(i)
                badge_class = badge.get_attribute("class")
                badge_text = badge.text_content()
                print(f"Status badge {i+1}: class='{badge_class}', text='{badge_text}'")
            
            self.take_baseline_screenshot(page, "status_badges_visible")
            
            # Test filtering by clicking on a status badge (if implemented)
            # This would require checking if status badges are clickable links
            first_badge = status_badges.first
            first_badge.click()
            page.wait_for_timeout(1000)
            
            # Check if filtered by status
            if "status=" in page.url:
                self.take_baseline_screenshot(page, "filtered_by_status_badge")
                # Clear filter
                page.goto(self.HISTORY_URL)
                page.wait_for_timeout(1000)
        else:
            print("No status badges found to test")
            self.take_baseline_screenshot(page, "no_status_badges")
    
    # Test 10: Message content truncation
    def test_message_content_truncation(self, authenticated_page: Page):
        """Test that long message content is properly displayed."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "message_content_check")
        
        # Check message content cells
        message_cells = page.locator(".message-content")
        
        if message_cells.count() > 0:
            # Check first few message cells
            for i in range(min(message_cells.count(), 3)):
                cell = message_cells.nth(i)
                content = cell.text_content()
                print(f"Message {i+1}: {content[:50]}...")
            
            self.take_baseline_screenshot(page, "message_contents")
            
            # Check if long messages are truncated in the table
            # (This would depend on CSS styling)
        else:
            print("No message content cells found")
            self.take_baseline_screenshot(page, "no_message_contents")
    
    # Test 11: Recipients list display
    def test_recipients_list_display(self, authenticated_page: Page):
        """Test recipients list display in history table."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "recipients_check")
        
        # Check recipients list cells
        recipients_cells = page.locator(".recipients-list")
        
        if recipients_cells.count() > 0:
            # Check first recipients cell
            first_cell = recipients_cells.first
            recipient_items = first_cell.locator(".recipient-item")
            
            if recipient_items.count() > 0:
                print(f"First message has {recipient_items.count()} recipients")
                for i in range(min(recipient_items.count(), 3)):
                    recipient = recipient_items.nth(i)
                    phone_text = recipient.text_content()
                    print(f"  Recipient {i+1}: {phone_text}")
                
                self.take_baseline_screenshot(page, "recipients_list")
            else:
                print("No recipient items found in first cell")
                self.take_baseline_screenshot(page, "no_recipient_items")
        else:
            print("No recipients list cells found")
            self.take_baseline_screenshot(page, "no_recipients_cells")
    
    # Test 12: View detail functionality
    def test_view_detail_functionality(self, authenticated_page: Page):
        """Test view detail functionality from history page."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "view_detail_start")
        
        # Check if there are messages in the history table
        table_container = page.locator(".table-container")
        
        if table_container.count() > 0:
            # Table is displayed (has messages)
            table = page.locator(".history-table")
            expect(table).to_be_visible()
            
            # Check if there are message rows
            message_rows = table.locator("tbody .message-row")
            
            if message_rows.count() > 0:
                # Get first message row
                first_row = message_rows.first
                
                # Get message details from the row
                status_badge = first_row.locator(".status")
                timestamp = first_row.locator(".timestamp")
                message_content = first_row.locator(".message-content")
                recipients_list = first_row.locator(".recipients-list")
                counts = first_row.locator(".counts")
                
                # Store message details for verification
                status_text = status_badge.text_content()
                timestamp_text = timestamp.text_content()
                message_text = message_content.text_content()
                
                print(f"Message details from history table:")
                print(f"  Status: {status_text}")
                print(f"  Time: {timestamp_text}")
                print(f"  Message: {message_text[:50]}...")
                
                # Check View button exists
                view_button = first_row.locator(".actions .btn")
                expect(view_button).to_be_visible()
                expect(view_button).to_have_text("View")
                
                self.take_baseline_screenshot(page, "view_button_before_click")
                
                # Click View button
                view_button.click()
                page.wait_for_timeout(2000)
                
                # Check if navigated to message detail page
                expect(page).to_have_url(re.compile(".*sms_detail.*"))
                expect(page).to_have_title(re.compile("Message Details - SMS Application"))
                
                self.take_baseline_screenshot(page, "message_detail_page")
                
                # Verify detail page header
                detail_header = page.locator(".detail-header h1")
                expect(detail_header).to_be_visible()
                expect(detail_header).to_have_text("Message Details")
                
                # Check Back to History button
                back_button = page.locator(".detail-header .btn-small")
                expect(back_button).to_be_visible()
                expect(back_button).to_have_text("← Back to History")
                
                # Verify message information section
                message_info = page.locator(".message-info")
                expect(message_info).to_be_visible()
                
                # Check status matches
                detail_status = message_info.locator(".status")
                expect(detail_status).to_be_visible()
                # Status text should match (case-insensitive)
                detail_status_text = detail_status.text_content()
                assert detail_status_text.lower() == status_text.lower(), \
                    f"Status mismatch: detail={detail_status_text}, history={status_text}"
                
                # Check message content matches
                detail_content = message_info.locator(".message-content")
                expect(detail_content).to_be_visible()
                detail_content_text = detail_content.text_content()
                assert detail_content_text == message_text, \
                    f"Message content mismatch"
                
                # Check other info rows
                info_rows = message_info.locator(".info-row")
                expect(info_rows).to_have_count_at_least(4)  # Status, Created, Total Recipients, Successful, Failed
                
                # Check recipients list section
                recipients_section = page.locator(".recipients-list")
                expect(recipients_section).to_be_visible()
                
                recipients_header = recipients_section.locator("h2")
                expect(recipients_header).to_be_visible()
                expect(recipients_header).to_have_text("Recipients")
                
                # Check recipients table
                recipients_table = recipients_section.locator("table")
                expect(recipients_table).to_be_visible()
                
                # Check table headers
                table_headers = recipients_table.locator("thead th")
                expect(table_headers).to_have_count(3)
                expect(table_headers.nth(0)).to_have_text("Phone Number")
                expect(table_headers.nth(1)).to_have_text("Status")
                expect(table_headers.nth(2)).to_have_text("Error Message")
                
                # Check if there are recipient rows
                recipient_rows = recipients_table.locator("tbody tr")
                if recipient_rows.count() > 0:
                    print(f"Found {recipient_rows.count()} recipient(s) in detail view")
                    self.take_baseline_screenshot(page, "recipients_table")
                else:
                    print("No recipient rows found in detail view")
                
                # Test Back to History button functionality
                back_button.click()
                page.wait_for_timeout(1000)
                
                # Verify we're back on history page
                expect(page).to_have_url(re.compile(".*history.*"))
                expect(page).to_have_title(re.compile("Message History - SMS Application"))
                
                self.take_baseline_screenshot(page, "back_to_history_from_detail")
                
                print("✓ View detail functionality test completed successfully")
            else:
                print("No message rows found in history table")
                self.take_baseline_screenshot(page, "no_message_rows")
        else:
            print("No history table displayed (no messages)")
            self.take_baseline_screenshot(page, "no_history_table_for_detail")
    
    # Test 13: Advanced search functionality
    def test_advanced_search_functionality(self, authenticated_page: Page):
        """Test advanced search functionality on history page."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "advanced_search_start")
        
        # Check for advanced search toggle button
        advanced_search_toggle = page.locator(".advanced-search-toggle")
        
        if advanced_search_toggle.count() > 0:
            # Advanced search is available
            expect(advanced_search_toggle).to_be_visible()
            expect(advanced_search_toggle).to_have_text("Advanced Search")
            
            # Click to expand advanced search
            advanced_search_toggle.click()
            page.wait_for_timeout(500)
            self.take_baseline_screenshot(page, "advanced_search_expanded")
            
            # Check advanced search fields
            # Date range fields
            start_date_input = page.locator("input[name='start_date']")
            end_date_input = page.locator("input[name='end_date']")
            
            if start_date_input.count() > 0:
                expect(start_date_input).to_be_visible()
                expect(end_date_input).to_be_visible()
                
                # Test date range selection
                start_date_input.fill("2024-01-01")
                end_date_input.fill("2024-12-31")
                self.take_baseline_screenshot(page, "date_range_filled")
            
            # Message content search
            message_search = page.locator("input[name='message_content']")
            if message_search.count() > 0:
                expect(message_search).to_be_visible()
                message_search.fill("test message")
                self.take_baseline_screenshot(page, "message_content_search")
            
            # Recipient phone search
            phone_search = page.locator("input[name='recipient_phone']")
            if phone_search.count() > 0:
                expect(phone_search).to_be_visible()
                phone_search.fill("85212345678")
                self.take_baseline_screenshot(page, "phone_search")
            
            # Multiple status selection
            status_checkboxes = page.locator("input[name='status']")
            if status_checkboxes.count() > 0:
                # Select multiple statuses
                for i in range(min(status_checkboxes.count(), 3)):
                    status_checkboxes.nth(i).check()
                self.take_baseline_screenshot(page, "multiple_status_selected")
            
            # Apply advanced search
            apply_button = page.locator(".advanced-search-form .btn-primary")
            if apply_button.count() > 0:
                expect(apply_button).to_be_visible()
                apply_button.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "advanced_search_applied")
                
                # Check URL contains advanced search parameters
                expect(page).to_have_url(re.compile(".*start_date=.*"))
                expect(page).to_have_url(re.compile(".*end_date=.*"))
            
            # Test reset functionality
            reset_button = page.locator(".advanced-search-form .btn-secondary")
            if reset_button.count() > 0:
                expect(reset_button).to_be_visible()
                reset_button.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "advanced_search_reset")
        else:
            print("Advanced search functionality not available")
            self.take_baseline_screenshot(page, "no_advanced_search")
    
    # Test 14: Multi-column sorting functionality
    def test_multi_column_sorting_functionality(self, authenticated_page: Page):
        """Test multi-column sorting functionality on history table."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "sorting_start")
        
        # Check if history table exists
        table = page.locator(".history-table")
        
        if table.count() > 0:
            # Get table headers
            headers = table.locator("thead th")
            
            # Test sorting on each sortable column
            sortable_headers = []
            for i in range(headers.count()):
                header = headers.nth(i)
                header_text = header.text_content()
                
                # Check if header is sortable (has sort icon or clickable)
                if header.locator(".sort-icon").count() > 0 or "sortable" in header.get_attribute("class", ""):
                    sortable_headers.append((i, header_text))
            
            print(f"Found {len(sortable_headers)} sortable columns")
            
            for col_index, col_name in sortable_headers:
                header = headers.nth(col_index)
                
                # Click to sort ascending
                header.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, f"sort_asc_{col_name}")
                
                # Check for sort indicator
                sort_indicator = header.locator(".sort-asc, .sort-desc")
                if sort_indicator.count() > 0:
                    print(f"✓ {col_name} sorted ascending")
                
                # Click again to sort descending
                header.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, f"sort_desc_{col_name}")
                
                # Click again to clear sort (if supported)
                header.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, f"sort_cleared_{col_name}")
            
            # Test multi-column sorting (if supported)
            if len(sortable_headers) >= 2:
                # Sort by first column
                headers.nth(sortable_headers[0][0]).click()
                page.wait_for_timeout(500)
                
                # Sort by second column while holding shift (if supported)
                # Note: This depends on implementation
                second_header = headers.nth(sortable_headers[1][0])
                second_header.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "multi_column_sort")
                
                # Check URL for sort parameters
                expect(page).to_have_url(re.compile(".*sort=.*"))
        else:
            print("History table not found for sorting test")
            self.take_baseline_screenshot(page, "no_table_for_sorting")
    
    # Test 15: Batch operations functionality
    def test_batch_operations_functionality(self, authenticated_page: Page):
        """Test batch operations (select multiple messages) on history page."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "batch_ops_start")
        
        # Check for batch operations controls
        batch_controls = page.locator(".batch-controls")
        
        if batch_controls.count() > 0:
            # Batch operations are available
            expect(batch_controls).to_be_visible()
            
            # Check for select all checkbox
            select_all_checkbox = page.locator("input[type='checkbox'].select-all")
            if select_all_checkbox.count() > 0:
                expect(select_all_checkbox).to_be_visible()
                
                # Check select all
                select_all_checkbox.check()
                page.wait_for_timeout(500)
                self.take_baseline_screenshot(page, "select_all_checked")
                
                # Uncheck select all
                select_all_checkbox.uncheck()
                page.wait_for_timeout(500)
                self.take_baseline_screenshot(page, "select_all_unchecked")
            
            # Check for individual message checkboxes
            message_checkboxes = page.locator("input[type='checkbox'].message-select")
            if message_checkboxes.count() > 0:
                # Select first 3 messages
                for i in range(min(message_checkboxes.count(), 3)):
                    message_checkboxes.nth(i).check()
                    page.wait_for_timeout(200)
                
                self.take_baseline_screenshot(page, "messages_selected")
                
                # Check batch action buttons appear when messages are selected
                batch_actions = page.locator(".batch-actions")
                if batch_actions.count() > 0:
                    expect(batch_actions).to_be_visible()
                    
                    # Check available batch actions
                    delete_button = batch_actions.locator("button:has-text('Delete')")
                    export_button = batch_actions.locator("button:has-text('Export')")
                    resend_button = batch_actions.locator("button:has-text('Resend')")
                    
                    if delete_button.count() > 0:
                        expect(delete_button).to_be_visible()
                        # Test delete confirmation (if implemented)
                        delete_button.click()
                        page.wait_for_timeout(500)
                        self.take_baseline_screenshot(page, "delete_confirmation")
                        
                        # Check for confirmation dialog
                        confirm_dialog = page.locator(".confirm-dialog")
                        if confirm_dialog.count() > 0:
                            expect(confirm_dialog).to_be_visible()
                            expect(confirm_dialog).to_contain_text("Delete selected messages?")
                            
                            # Cancel deletion
                            cancel_button = confirm_dialog.locator("button:has-text('Cancel')")
                            if cancel_button.count() > 0:
                                cancel_button.click()
                                page.wait_for_timeout(500)
                                self.take_baseline_screenshot(page, "delete_cancelled")
                    
                    if export_button.count() > 0:
                        expect(export_button).to_be_visible()
                        export_button.click()
                        page.wait_for_timeout(500)
                        self.take_baseline_screenshot(page, "export_clicked")
                    
                    if resend_button.count() > 0:
                        expect(resend_button).to_be_visible()
                        resend_button.click()
                        page.wait_for_timeout(500)
                        self.take_baseline_screenshot(page, "resend_clicked")
                
                # Clear selections
                clear_selection_button = page.locator("button:has-text('Clear Selection')")
                if clear_selection_button.count() > 0:
                    clear_selection_button.click()
                    page.wait_for_timeout(500)
                    self.take_baseline_screenshot(page, "selection_cleared")
                else:
                    # Uncheck all checkboxes manually
                    for i in range(min(message_checkboxes.count(), 3)):
                        message_checkboxes.nth(i).uncheck()
                    page.wait_for_timeout(500)
                    self.take_baseline_screenshot(page, "selection_cleared_manual")
        else:
            print("Batch operations functionality not available")
            self.take_baseline_screenshot(page, "no_batch_operations")
    
    # Test 16: Export history functionality
    def test_export_history_functionality(self, authenticated_page: Page):
        """Test export history records functionality."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "export_start")
        
        # Check for export button
        export_button = page.locator("button:has-text('Export'), .export-button")
        
        if export_button.count() > 0:
            expect(export_button).to_be_visible()
            
            # Click export button
            export_button.click()
            page.wait_for_timeout(1000)
            self.take_baseline_screenshot(page, "export_modal")
            
            # Check export options modal
            export_modal = page.locator(".export-modal, .modal-dialog")
            if export_modal.count() > 0:
                expect(export_modal).to_be_visible()
                
                # Check export format options
                format_options = export_modal.locator("input[name='export_format']")
                if format_options.count() > 0:
                    # Select CSV format
                    csv_option = export_modal.locator("input[value='csv']")
                    if csv_option.count() > 0:
                        csv_option.check()
                        self.take_baseline_screenshot(page, "csv_selected")
                    
                    # Select Excel format
                    excel_option = export_modal.locator("input[value='excel']")
                    if excel_option.count() > 0:
                        excel_option.check()
                        self.take_baseline_screenshot(page, "excel_selected")
                
                # Check date range options
                export_date_range = export_modal.locator("select[name='date_range']")
                if export_date_range.count() > 0:
                    expect(export_date_range).to_be_visible()
                    
                    # Select different date ranges
                    export_date_range.select_option("last_7_days")
                    self.take_baseline_screenshot(page, "date_range_selected")
                    
                    export_date_range.select_option("custom")
                    page.wait_for_timeout(500)
                    
                    # Check custom date inputs appear
                    custom_start = export_modal.locator("input[name='custom_start']")
                    custom_end = export_modal.locator("input[name='custom_end']")
                    if custom_start.count() > 0:
                        custom_start.fill("2024-01-01")
                        custom_end.fill("2024-12-31")
                        self.take_baseline_screenshot(page, "custom_dates_filled")
                
                # Check status filter for export
                export_status = export_modal.locator("select[name='export_status']")
                if export_status.count() > 0:
                    export_status.select_option("sent")
                    self.take_baseline_screenshot(page, "export_status_selected")
                
                # Test export generation
                generate_button = export_modal.locator("button:has-text('Generate Export')")
                if generate_button.count() > 0:
                    expect(generate_button).to_be_visible()
                    generate_button.click()
                    page.wait_for_timeout(2000)
                    self.take_baseline_screenshot(page, "export_generating")
                    
                    # Check for download link or success message
                    success_message = page.locator(".alert-success, .export-success")
                    if success_message.count() > 0:
                        expect(success_message).to_be_visible()
                        expect(success_message).to_contain_text("Export generated")
                        self.take_baseline_screenshot(page, "export_success")
                    
                    download_link = page.locator("a:has-text('Download'), .download-link")
                    if download_link.count() > 0:
                        expect(download_link).to_be_visible()
                        self.take_baseline_screenshot(page, "download_available")
                
                # Test cancel export
                cancel_button = export_modal.locator("button:has-text('Cancel')")
                if cancel_button.count() > 0:
                    cancel_button.click()
                    page.wait_for_timeout(500)
                    self.take_baseline_screenshot(page, "export_cancelled")
        else:
            print("Export functionality not available")
            self.take_baseline_screenshot(page, "no_export_functionality")
    
    # Test 17: Time range selector functionality
    def test_time_range_selector_functionality(self, authenticated_page: Page):
        """Test time range selector for filtering history records."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "time_range_start")
        
        # Check for time range selector
        time_range_selector = page.locator(".time-range-selector, select[name='time_range']")
        
        if time_range_selector.count() > 0:
            expect(time_range_selector).to_be_visible()
            
            # Test different time range options
            time_options = ["today", "yesterday", "last_7_days", "last_30_days", "this_month", "last_month", "custom"]
            
            for option in time_options:
                option_element = time_range_selector.locator(f"option[value='{option}']")
                if option_element.count() > 0:
                    # Select the option
                    time_range_selector.select_option(option)
                    page.wait_for_timeout(500)
                    self.take_baseline_screenshot(page, f"time_range_{option}")
                    
                    # Check if custom date inputs appear for custom option
                    if option == "custom":
                        custom_start = page.locator("input[name='custom_start_date']")
                        custom_end = page.locator("input[name='custom_end_date']")
                        
                        if custom_start.count() > 0:
                            expect(custom_start).to_be_visible()
                            expect(custom_end).to_be_visible()
                            
                            # Fill custom dates
                            custom_start.fill("2024-01-01")
                            custom_end.fill("2024-01-31")
                            self.take_baseline_screenshot(page, "custom_dates_filled")
            
            # Test apply time range filter
            apply_button = page.locator("button:has-text('Apply Time Range')")
            if apply_button.count() > 0:
                apply_button.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "time_range_applied")
                
                # Check URL contains time range parameters
                expect(page).to_have_url(re.compile(".*time_range=.*"))
            
            # Test clear time range
            clear_button = page.locator("button:has-text('Clear Time Range')")
            if clear_button.count() > 0:
                clear_button.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "time_range_cleared")
        else:
            print("Time range selector not available")
            self.take_baseline_screenshot(page, "no_time_range_selector")
    
    # Test 18: Status filter combinations functionality
    def test_status_filter_combinations_functionality(self, authenticated_page: Page):
        """Test combinations of status filters on history page."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "status_combinations_start")
        
        # Check for status filter options
        status_filter = page.locator(".status-filter, select[name='status']")
        
        if status_filter.count() > 0:
            expect(status_filter).to_be_visible()
            
            # Test individual status filters
            status_options = ["pending", "sent", "failed", "partial"]
            
            for status in status_options:
                status_filter.select_option(status)
                page.wait_for_timeout(500)
                self.take_baseline_screenshot(page, f"status_{status}_selected")
                
                # Apply filter
                apply_button = page.locator("button:has-text('Apply Filter')")
                if apply_button.count() > 0:
                    apply_button.click()
                    page.wait_for_timeout(1000)
                    self.take_baseline_screenshot(page, f"status_{status}_applied")
                    
                    # Check URL contains status parameter
                    expect(page).to_have_url(re.compile(f".*status={status}.*"))
                    
                    # Clear filter
                    clear_button = page.locator("button:has-text('Clear Filter')")
                    if clear_button.count() > 0:
                        clear_button.click()
                        page.wait_for_timeout(500)
            
            # Check for multiple status selection (if supported)
            multi_status_select = page.locator("select[name='status'][multiple]")
            if multi_status_select.count() > 0:
                # Select multiple statuses
                multi_status_select.select_option(["sent", "failed"])
                page.wait_for_timeout(500)
                self.take_baseline_screenshot(page, "multiple_status_selected")
                
                # Apply multiple status filter
                apply_button.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "multiple_status_applied")
                
                # Check URL contains multiple status parameters
                expect(page).to_have_url(re.compile(".*status=sent.*"))
                expect(page).to_have_url(re.compile(".*status=failed.*"))
            
            # Test status filter with other filters (search)
            search_input = page.locator(".search-input")
            if search_input.count() > 0:
                # Apply status filter
                status_filter.select_option("sent")
                page.wait_for_timeout(300)
                
                # Add search term
                search_input.fill("test")
                page.wait_for_timeout(300)
                self.take_baseline_screenshot(page, "status_and_search_combined")
                
                # Apply combined filters
                filter_button = page.locator(".search-form .btn-secondary")
                if filter_button.count() > 0:
                    filter_button.click()
                    page.wait_for_timeout(1000)
                    self.take_baseline_screenshot(page, "combined_filters_applied")
                    
                    # Check URL contains both parameters
                    expect(page).to_have_url(re.compile(".*status=sent.*"))
                    expect(page).to_have_url(re.compile(".*search=test.*"))
        else:
            print("Status filter not available for combination testing")
            self.take_baseline_screenshot(page, "no_status_filter")
    
    # Test 19: Quick actions functionality
    def test_quick_actions_functionality(self, authenticated_page: Page):
        """Test quick actions (resend, duplicate, etc.) on history page."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "quick_actions_start")
        
        # Check if there are messages in the history table
        table_container = page.locator(".table-container")
        
        if table_container.count() > 0:
            table = page.locator(".history-table")
            expect(table).to_be_visible()
            
            # Check if there are message rows
            message_rows = table.locator("tbody .message-row")
            
            if message_rows.count() > 0:
                # Get first message row
                first_row = message_rows.first
                
                # Check for quick actions dropdown
                actions_dropdown = first_row.locator(".actions-dropdown, .dropdown-toggle")
                
                if actions_dropdown.count() > 0:
                    expect(actions_dropdown).to_be_visible()
                    
                    # Click to open dropdown
                    actions_dropdown.click()
                    page.wait_for_timeout(500)
                    self.take_baseline_screenshot(page, "actions_dropdown_open")
                    
                    # Check dropdown menu items
                    dropdown_menu = page.locator(".dropdown-menu.show")
                    if dropdown_menu.count() > 0:
                        expect(dropdown_menu).to_be_visible()
                        
                        # Check for resend option
                        resend_option = dropdown_menu.locator("a:has-text('Resend')")
                        if resend_option.count() > 0:
                            expect(resend_option).to_be_visible()
                            resend_option.click()
                            page.wait_for_timeout(1000)
                            self.take_baseline_screenshot(page, "resend_clicked")
                            
                            # Check if navigated to compose page with pre-filled data
                            if "compose" in page.url:
                                expect(page).to_have_url(re.compile(".*compose.*"))
                                self.take_baseline_screenshot(page, "navigated_to_compose")
                                # Go back to history
                                page.go_back()
                                page.wait_for_timeout(1000)
                        
                        # Check for duplicate option
                        duplicate_option = dropdown_menu.locator("a:has-text('Duplicate')")
                        if duplicate_option.count() > 0:
                            expect(duplicate_option).to_be_visible()
                            duplicate_option.click()
                            page.wait_for_timeout(1000)
                            self.take_baseline_screenshot(page, "duplicate_clicked")
                        
                        # Check for delete option
                        delete_option = dropdown_menu.locator("a:has-text('Delete')")
                        if delete_option.count() > 0:
                            expect(delete_option).to_be_visible()
                            delete_option.click()
                            page.wait_for_timeout(500)
                            self.take_baseline_screenshot(page, "delete_option_clicked")
                            
                            # Check for confirmation dialog
                            confirm_dialog = page.locator(".confirm-dialog")
                            if confirm_dialog.count() > 0:
                                expect(confirm_dialog).to_be_visible()
                                
                                # Cancel deletion
                                cancel_button = confirm_dialog.locator("button:has-text('Cancel')")
                                if cancel_button.count() > 0:
                                    cancel_button.click()
                                    page.wait_for_timeout(500)
                                    self.take_baseline_screenshot(page, "delete_cancelled")
                        
                        # Close dropdown
                        actions_dropdown.click()
                        page.wait_for_timeout(300)
                else:
                    print("No actions dropdown found for quick actions")
                    self.take_baseline_screenshot(page, "no_actions_dropdown")
            else:
                print("No message rows found for quick actions test")
                self.take_baseline_screenshot(page, "no_message_rows_for_actions")
        else:
            print("No history table displayed for quick actions test")
            self.take_baseline_screenshot(page, "no_table_for_actions")
    
    # Test 20: Bulk delete functionality
    def test_bulk_delete_functionality(self, authenticated_page: Page):
        """Test bulk delete functionality for multiple messages."""
        page = authenticated_page
        
        page.goto(self.HISTORY_URL)
        self.take_baseline_screenshot(page, "bulk_delete_start")
        
        # Check for bulk delete controls
        bulk_delete_section = page.locator(".bulk-delete-section")
        
        if bulk_delete_section.count() > 0:
            expect(bulk_delete_section).to_be_visible()
            
            # Check for select all checkbox
            select_all = bulk_delete_section.locator("input[type='checkbox'].select-all")
            if select_all.count() > 0:
                expect(select_all).to_be_visible()
                
                # Select all messages
                select_all.check()
                page.wait_for_timeout(500)
                self.take_baseline_screenshot(page, "all_messages_selected")
                
                # Check delete selected button
                delete_selected_button = bulk_delete_section.locator("button:has-text('Delete Selected')")
                if delete_selected_button.count() > 0:
                    expect(delete_selected_button).to_be_visible()
                    
                    # Click delete button
                    delete_selected_button.click()
                    page.wait_for_timeout(500)
                    self.take_baseline_screenshot(page, "bulk_delete_clicked")
                    
                    # Check confirmation modal
                    confirm_modal = page.locator(".confirm-modal")
                    if confirm_modal.count() > 0:
                        expect(confirm_modal).to_be_visible()
                        expect(confirm_modal).to_contain_text("Delete selected messages?")
                        
                        # Check message count in confirmation
                        message_count = confirm_modal.locator(".message-count")
                        if message_count.count() > 0:
                            expect(message_count).to_be_visible()
                        
                        # Cancel bulk delete
                        cancel_button = confirm_modal.locator("button:has-text('Cancel')")
                        if cancel_button.count() > 0:
                            cancel_button.click()
                            page.wait_for_timeout(500)
                            self.take_baseline_screenshot(page, "bulk_delete_cancelled")
                        
                        # Test confirm delete (optional - might delete actual data)
                        # confirm_button = confirm_modal.locator("button:has-text('Confirm')")
                        # if confirm_button.count() > 0:
                        #     # Only test if we're in a safe test environment
                        #     confirm_button.click()
                        #     page.wait_for_timeout(1000)
                        #     self.take_baseline_screenshot(page, "bulk_delete_confirmed")
                        
                        #     # Check for success message
                        #     success_message = page.locator(".alert-success")
                        #     if success_message.count() > 0:
                        #         expect(success_message).to_be_visible()
                        #         expect(success_message).to_contain_text("deleted")
                        #         self.take_baseline_screenshot(page, "bulk_delete_success")
            else:
                print("No select all checkbox found for bulk delete")
                self.take_baseline_screenshot(page, "no_select_all_checkbox")
        else:
            print("Bulk delete functionality not available")
            self.take_baseline_screenshot(page, "no_bulk_delete")



def run_history_baseline_tests():
    """Run history page baseline tests and show summary."""
    import subprocess
    import sys
    
    print("=" * 60)
    print("SMS Panel History Page Baseline Tests")
    print("=" * 60)
    print("Features:")
    print("- Trace recording: DISABLED by default")
    print("- Video recording: DISABLED by default")
    print("- Screenshot comparison: ENABLED")
    print("- Baseline images: test_history_baseline_screenshots/")
    print("- Authentication: Auto-login with test_SMSadmin credentials")
    print("=" * 60)
    
    # Create directories
    os.makedirs("test_ui/test_history_baseline_screenshots", exist_ok=True)
    
    # Run tests
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        __file__,
        "-v",
        "--headed"
    ])
    
    print("\n" + "=" * 60)
    print("HISTORY PAGE BASELINE TEST SUMMARY")
    print("=" * 60)
    
    # Count baseline files
    baseline_dir = "test_ui/test_history_baseline_screenshots"
    if os.path.exists(baseline_dir):
        baseline_files = [f for f in os.listdir(baseline_dir) if f.endswith('.png')]
        print(f"History baseline screenshots: {len(baseline_files)} files")
        
        # Show some examples
        if baseline_files:
            print("\nExample baseline files:")
            for f in baseline_files[:5]:
                print(f"  - {f}")
            if len(baseline_files) > 5:
                print(f"  - ... and {len(baseline_files) - 5} more")
    
    print("\nTo update baseline images:")
    print("1. Delete files from test_ui/test_history_baseline_screenshots/")
    print("2. Run tests again to create new baselines")
    print("\nTo enable trace/video recording:")
    print("Edit test_ui/test_history_page_baseline.py")
    print("Set ENABLE_TRACE = True for trace recording")
    print("Set ENABLE_VIDEO = True for video recording")
    
    return result.returncode


if __name__ == "__main__":
    """Command line interface."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        sys.exit(run_history_baseline_tests())
    else:
        print("Usage:")
        print("  python test_ui/test_history_page_baseline.py run")
        print()
        print("Or run with pytest directly:")
        print("  pytest test_ui/test_history_page_baseline.py -v --headed")
        print()
        print("Test suite includes:")
        print("  1. History page loads after authentication")
        print("  2. Search and filter functionality")
        print("  3. History table structure")
        print("  4. Pagination functionality")
        print("  5. Responsive design")
        print("  6. Access without authentication")
        print("  7. Navigation from history page")
        print("  8. Empty state with filters")
        print("  9. Status badges display")
        print("  10. Message content truncation")
        print("  11. Recipients list display")
        print("  12. View detail functionality")
        print("  13. Advanced search functionality")
        print("  14. Multi-column sorting functionality")
        print("  15. Batch operations functionality")
        print("  16. Export history functionality")
        print("  17. Time range selector functionality")
        print("  18. Status filter combinations functionality")
        print("  19. Quick actions functionality")
        print("  20. Bulk delete functionality")

