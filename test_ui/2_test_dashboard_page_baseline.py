"""
Playwright UI tests for SMS Panel Dashboard page with baseline screenshot comparison.
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


class TestDashboardPageBaseline:
    """Test suite for SMS Panel Dashboard page with baseline screenshot comparison."""
    
    # Configuration - CHANGE THESE SETTINGS AS NEEDED
    BASELINE_DIR = "test_ui/test_dashboard_baseline_screenshots"  # Store baseline images here
    ENABLE_VIDEO = False  # Set to True to enable video recording
    ENABLE_TRACE = False  # Set to True to enable trace recording
    
    # Login credentials
    LOGIN_URL = "http://127.0.0.1:3570/login?next=%2F"
    DASHBOARD_URL = "http://127.0.0.1:3570/"  # Dashboard is at root path
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
            context_args["record_video_dir"] = "test_videos_dashboard"
            context_args["record_video_size"] = {"width": 1280, "height": 800}
            os.makedirs("test_videos_dashboard", exist_ok=True)
        
        context = browser.new_context(**context_args)
        
        # Start optional tracing
        if self.ENABLE_TRACE:
            os.makedirs("test_traces_dashboard", exist_ok=True)
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
            trace_path = os.path.join("test_traces_dashboard", f"{test_name}.zip")
            context.tracing.stop(path=trace_path)
        
        # Close context (saves video if enabled)
        context.close()
        browser.close()
    
    @pytest.fixture(scope="function")
    def authenticated_page(self, browser_page: Page):
        """Create an authenticated page for dashboard tests."""
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
        SIMILARITY_THRESHOLD = 99.0  # 相似度閾值（百分比）
        
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

    # Test 1: Dashboard page loads correctly after authentication
    def test_dashboard_page_loads(self, authenticated_page: Page):
        """Test that dashboard page loads correctly after authentication."""
        page = authenticated_page
        
        # Navigate to dashboard
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "dashboard_page")
        
        # Check page title
        expect(page).to_have_title(re.compile("Dashboard - SMS Application"))
        
        # Check welcome message with username
        welcome_header = page.locator(".dashboard-header h1")
        expect(welcome_header).to_be_visible()
        expect(welcome_header).to_contain_text("Welcome")
        expect(welcome_header).to_contain_text(self.USERNAME)
        self.take_baseline_screenshot(page, "welcome_header")
        
        # Check Compose New SMS button
        compose_button = page.locator(".dashboard-header .btn-primary")
        expect(compose_button).to_be_visible()
        expect(compose_button).to_have_text("Compose New SMS")
        self.take_baseline_screenshot(page, "compose_button")
    
    # Test 2: Dashboard statistics cards
    def test_dashboard_statistics(self, authenticated_page: Page):
        """Test that dashboard statistics cards are displayed correctly."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "dashboard_stats")
        
        # Check stats section exists
        stats_section = page.locator(".stats")
        expect(stats_section).to_be_visible()
        
        # Check stat cards
        stat_cards = page.locator(".stat-card")
        expect(stat_cards).to_have_count(2)  # Total Messages and Sent Successfully
        
        # Check first stat card (Total Messages)
        total_messages_card = stat_cards.nth(0)
        expect(total_messages_card.locator("h2")).to_be_visible()
        expect(total_messages_card.locator("p")).to_have_text("Total Messages")
        
        # Check second stat card (Sent Successfully)
        sent_card = stat_cards.nth(1)
        expect(sent_card.locator("h2")).to_be_visible()
        expect(sent_card.locator("p")).to_have_text("Sent Successfully")
        
        self.take_baseline_screenshot(page, "stat_cards")
    
    # Test 3: Queue status display (if applicable)
    def test_queue_status_display(self, authenticated_page: Page):
        """Test queue status display on dashboard."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "queue_status_check")
        
        # Check if queue status section exists
        queue_status_section = page.locator(".queue-status")
        
        if queue_status_section.count() > 0:
            # Queue status is displayed
            expect(queue_status_section.locator(".card-header h5")).to_have_text("Queue Status")
            
            # Check queue metrics
            queue_metrics = queue_status_section.locator(".stat")
            expect(queue_metrics).to_have_count_at_least(1)  # Messages in Queue and msgs/sec
            
            self.take_baseline_screenshot(page, "queue_status_visible")
        else:
            # Queue status not displayed (no queue data)
            print("Queue status section not displayed (no queue data)")
            self.take_baseline_screenshot(page, "queue_status_hidden")
    
    # Test 4: Messages section with time filters
    def test_messages_section_and_filters(self, authenticated_page: Page):
        """Test messages section and time filter buttons."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "messages_section")
        
        # Check messages section header
        messages_header = page.locator(".messages-header")
        expect(messages_header).to_be_visible()
        
        # Check "Messages" title
        messages_title = messages_header.locator("h2")
        expect(messages_title).to_have_text("Messages")
        
        # Check time filter buttons
        time_filters = page.locator(".time-filter-buttons .btn")
        expect(time_filters).to_have_count(3)  # Last 3 hours, Today, Last 7 days
        
        # Verify filter button texts
        filter_texts = ["Last 3 hours", "Today", "Last 7 days"]
        for i, expected_text in enumerate(filter_texts):
            expect(time_filters.nth(i)).to_contain_text(expected_text)
        
        self.take_baseline_screenshot(page, "time_filters")
        
        # Test clicking on a filter (Today)
        today_filter = page.locator(".time-filter-buttons .btn:has-text('Today')")
        today_filter.click()
        
        # Wait for page to update
        page.wait_for_timeout(1000)
        self.take_baseline_screenshot(page, "today_filter_applied")
        
        # Check if URL contains filter parameter
        expect(page).to_have_url(re.compile(".*time_filter=today.*"))
    
    # Test 5: Messages table structure
    def test_messages_table_structure(self, authenticated_page: Page):
        """Test messages table structure and columns."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "messages_table")
        
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
            else:
                # No messages - check empty state
                empty_state = page.locator(".empty-state")
                expect(empty_state).to_be_visible()
                expect(empty_state).to_contain_text("No messages for the selected time period")
                
                # Check link to compose page
                compose_link = empty_state.locator("a")
                expect(compose_link).to_be_visible()
                expect(compose_link).to_have_text("Send your first SMS!")
                
                self.take_baseline_screenshot(page, "empty_state")
        else:
            # No table container (no messages section at all)
            print("No messages table displayed")
            self.take_baseline_screenshot(page, "no_messages_section")
    
    # Test 6: Pagination functionality
    def test_pagination_functionality(self, authenticated_page: Page):
        """Test pagination controls on dashboard."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
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
    
    # Test 7: Navigation from dashboard
    def test_dashboard_navigation(self, authenticated_page: Page):
        """Test navigation links from dashboard page."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "navigation_start")
        
        # Test Compose New SMS button
        compose_button = page.locator(".dashboard-header .btn-primary")
        compose_button.click()
        page.wait_for_timeout(1000)
        
        # Check if navigated to compose page
        if "compose" in page.url:
            expect(page).to_have_url(re.compile(".*compose.*"))
            expect(page).to_have_title(re.compile("Compose SMS - SMS Application"))
            self.take_baseline_screenshot(page, "navigated_to_compose")
            # Go back to dashboard
            page.go_back()
            page.wait_for_timeout(1000)
        else:
            print("Compose button did not navigate to compose page")
        
        # Test View All History button
        view_history_button = page.locator(".dashboard-footer .btn-secondary")
        view_history_button.click()
        page.wait_for_timeout(1000)
        
        # Check if navigated to history page
        if "history" in page.url:
            expect(page).to_have_url(re.compile(".*history.*"))
            expect(page).to_have_title(re.compile("History - SMS Application"))
            self.take_baseline_screenshot(page, "navigated_to_history")
            # Go back to dashboard
            page.go_back()
            page.wait_for_timeout(1000)
        else:
            print("View All History button did not navigate to history page")
        
        # Test navigation via navbar
        navbar_links = page.locator(".nav-links a")
        
        # Test Compose link in navbar
        compose_nav_link = navbar_links.filter(has_text="Compose")
        if compose_nav_link.count() > 0:
            compose_nav_link.click()
            page.wait_for_timeout(1000)
            if "compose" in page.url:
                self.take_baseline_screenshot(page, "navbar_compose")
                page.go_back()
                page.wait_for_timeout(1000)
        
        # Test History link in navbar
        history_nav_link = navbar_links.filter(has_text="History")
        if history_nav_link.count() > 0:
            history_nav_link.click()
            page.wait_for_timeout(1000)
            if "history" in page.url:
                self.take_baseline_screenshot(page, "navbar_history")
                page.go_back()
                page.wait_for_timeout(1000)
        
        self.take_baseline_screenshot(page, "navigation_complete")
    
    # Test 8: Responsive design on dashboard
    def test_dashboard_responsive_design(self, authenticated_page: Page):
        """Test dashboard responsive design on different viewports."""
        page = authenticated_page
        
        # Test mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "mobile_viewport")
        
        # Check mobile layout elements
        dashboard_header = page.locator(".dashboard-header")
        expect(dashboard_header).to_be_visible()
        
        # Check if stats stack vertically on mobile
        stats = page.locator(".stats")
        expect(stats).to_be_visible()
        
        # Test tablet viewport
        page.set_viewport_size({"width": 768, "height": 1024})  # iPad
        self.take_baseline_screenshot(page, "tablet_viewport")
        
        # Test desktop viewport
        page.set_viewport_size({"width": 1280, "height": 800})  # Desktop
        self.take_baseline_screenshot(page, "desktop_viewport")
        
        # Verify key elements are visible on all viewports
        expect(page.locator(".dashboard-header h1")).to_be_visible()
        expect(page.locator(".stats")).to_be_visible()
        expect(page.locator(".messages-section")).to_be_visible()
    
    # Test 9: Dashboard accessibility without authentication
    def test_dashboard_access_without_auth(self, browser_page: Page):
        """Test that dashboard redirects to login when not authenticated."""
        page = browser_page
        
        # Try to access dashboard without logging in
        response = page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "dashboard_no_auth")
        
        # Should be redirected to login page
        expect(page).to_have_url(re.compile(".*login.*"))
        
        # Check login form is displayed
        expect(page.locator("h1")).to_have_text("Login")
        expect(page.locator("#username")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()
        
        self.take_baseline_screenshot(page, "redirected_to_login")
    
    # Test 10: Dashboard footer and navigation
    def test_dashboard_footer_and_complete_navigation(self, authenticated_page: Page):
        """Test complete dashboard navigation including footer links."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "dashboard_complete")
        
        # Check current user display in navbar
        current_user = page.locator(".current-user")
        if current_user.count() > 0:
            expect(current_user).to_be_visible()
            expect(current_user).to_contain_text(self.USERNAME)
            self.take_baseline_screenshot(page, "current_user_display")
        
        # Check all navbar links
        nav_links = page.locator(".nav-links a")
        link_count = nav_links.count()
        
        print(f"Found {link_count} navbar links")
        for i in range(link_count):
            link = nav_links.nth(i)
            link_text = link.text_content()
            print(f"  - Link {i+1}: {link_text}")
        
        # Check footer
        footer = page.locator("footer")
        expect(footer).to_be_visible()
        expect(footer).to_contain_text("SMS Application")
        
        self.take_baseline_screenshot(page, "dashboard_footer")
    
    # Test 11: Message detail view from dashboard
    def test_message_detail_view(self, authenticated_page: Page):
        """Test viewing message details from dashboard."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "detail_view_start")
        
        # Check if there are messages to view
        view_buttons = page.locator(".actions .btn")
        
        if view_buttons.count() > 0:
            # Click first View button
            first_view_button = view_buttons.first
            expect(first_view_button).to_have_text("View")
            first_view_button.click()
            
            # Wait for detail page to load
            page.wait_for_timeout(2000)
            
            # Check if on message detail page
            if "sms_detail" in page.url or "message" in page.url:
                expect(page).to_have_title(re.compile("Message Details - SMS Application"))
                expect(page.locator("h1")).to_contain_text("Message Details")
                
                # Check message details sections
                message_info = page.locator(".message-info")
                expect(message_info).to_be_visible()
                
                recipients_list = page.locator(".recipients-list")
                expect(recipients_list).to_be_visible()
                
                self.take_baseline_screenshot(page, "message_detail_page")
                
                # Go back to dashboard
                page.go_back()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "back_to_dashboard")
            else:
                print("View button did not navigate to message detail page")
                self.take_baseline_screenshot(page, "view_button_no_detail")
        else:
            print("No View buttons available (no messages or empty state)")
            self.take_baseline_screenshot(page, "no_view_buttons")
    
    # Test 12: Statistics cards refresh functionality
    def test_statistics_cards_refresh(self, authenticated_page: Page):
        """Test statistics cards refresh functionality."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "stats_refresh_start")
        
        # Check if refresh button exists
        refresh_button = page.locator("#refresh-stats, .refresh-button, button:has-text('Refresh')")
        
        if refresh_button.count() > 0:
            # Refresh functionality is implemented
            expect(refresh_button).to_be_visible()
            
            # Get initial stat values
            stat_cards = page.locator(".stat-card")
            initial_values = []
            
            for i in range(stat_cards.count()):
                card = stat_cards.nth(i)
                value = card.locator("h2").text_content()
                initial_values.append(value)
                print(f"Initial stat {i+1}: {value}")
            
            self.take_baseline_screenshot(page, "initial_stats")
            
            # Click refresh button
            refresh_button.click()
            page.wait_for_timeout(2000)
            self.take_baseline_screenshot(page, "refresh_clicked")
            
            # Check if stats were refreshed
            refreshed_values = []
            for i in range(stat_cards.count()):
                card = stat_cards.nth(i)
                value = card.locator("h2").text_content()
                refreshed_values.append(value)
                print(f"Refreshed stat {i+1}: {value}")
            
            # Compare values (they might be the same or different)
            if initial_values != refreshed_values:
                print("Statistics were refreshed (values changed)")
                self.take_baseline_screenshot(page, "stats_refreshed")
            else:
                print("Statistics refresh clicked but values remained the same")
                self.take_baseline_screenshot(page, "stats_unchanged")
            
            # Check for loading indicator during refresh
            loading_indicator = page.locator(".loading, .spinner, [aria-busy='true']")
            if loading_indicator.count() > 0:
                print("Loading indicator shown during refresh")
                self.take_baseline_screenshot(page, "loading_indicator")
        else:
            # Refresh functionality not implemented
            print("Statistics refresh functionality not implemented")
            self.take_baseline_screenshot(page, "no_refresh_button")
    
    # Test 13: Messages table sorting functionality
    def test_messages_table_sorting(self, authenticated_page: Page):
        """Test messages table sorting functionality."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "table_sorting_start")
        
        # Check if table exists
        table_container = page.locator(".table-container")
        
        if table_container.count() > 0:
            # Table is displayed
            table = page.locator(".history-table")
            expect(table).to_be_visible()
            
            # Check table headers for sortable indicators
            headers = table.locator("thead th")
            
            # Check which columns are sortable
            sortable_headers = []
            for i in range(headers.count()):
                header = headers.nth(i)
                header_text = header.text_content()
                
                # Check for sort indicators
                sort_indicator = header.locator(".sort-indicator, [data-sort], .sortable")
                if sort_indicator.count() > 0:
                    sortable_headers.append((i, header_text))
                    print(f"Sortable column: {header_text}")
            
            if sortable_headers:
                # Test sorting on first sortable column
                first_sortable = sortable_headers[0]
                column_index, column_name = first_sortable
                
                print(f"Testing sort on column: {column_name}")
                
                # Click column header to sort
                sort_header = headers.nth(column_index)
                sort_header.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "first_sort_clicked")
                
                # Check if sort indicator changed
                sort_indicator = sort_header.locator(".sort-indicator")
                if sort_indicator.count() > 0:
                    indicator_class = sort_indicator.get_attribute("class")
                    print(f"Sort indicator class after click: {indicator_class}")
                
                # Click again to reverse sort
                sort_header.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "second_sort_clicked")
                
                # Check URL for sort parameters
                if "sort=" in page.url:
                    print(f"Sort parameter in URL: {page.url}")
                    self.take_baseline_screenshot(page, "sort_url_parameter")
                
                # Test sorting on another column if available
                if len(sortable_headers) > 1:
                    second_sortable = sortable_headers[1]
                    column_index2, column_name2 = second_sortable
                    
                    print(f"Testing sort on second column: {column_name2}")
                    
                    sort_header2 = headers.nth(column_index2)
                    sort_header2.click()
                    page.wait_for_timeout(1000)
                    self.take_baseline_screenshot(page, "second_column_sort")
            else:
                print("No sortable columns found in messages table")
                self.take_baseline_screenshot(page, "no_sortable_columns")
        else:
            print("No messages table displayed")
            self.take_baseline_screenshot(page, "no_table_for_sorting")
    
    # Test 14: Additional message filter options
    def test_additional_message_filter_options(self, authenticated_page: Page):
        """Test additional message filter options beyond time filters."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "additional_filters_start")
        
        # Check for additional filter controls
        additional_filters = page.locator(".additional-filters, .filter-options, .advanced-filters")
        
        if additional_filters.count() > 0:
            # Additional filters are implemented
            expect(additional_filters).to_be_visible()
            
            # Check filter types
            filter_types = additional_filters.locator(".filter-type, select, input[type='checkbox']")
            
            if filter_types.count() > 0:
                print(f"Found {filter_types.count()} additional filter options")
                
                # Test status filter if available
                status_filter = page.locator("select[name='status'], #status-filter, .status-select")
                if status_filter.count() > 0:
                    expect(status_filter).to_be_visible()
                    
                    # Select a status option
                    status_options = status_filter.locator("option")
                    if status_options.count() > 1:
                        # Select first non-empty option
                        for i in range(status_options.count()):
                            option = status_options.nth(i)
                            option_value = option.get_attribute("value")
                            if option_value and option_value != "":
                                status_filter.select_option(option_value)
                                break
                        
                        page.wait_for_timeout(500)
                        self.take_baseline_screenshot(page, "status_filter_selected")
                        
                        selected_status = status_filter.input_value()
                        print(f"Selected status filter: {selected_status}")
                
                # Test search filter if available
                search_filter = page.locator("input[type='search'], #search-filter, .search-input")
                if search_filter.count() > 0:
                    expect(search_filter).to_be_visible()
                    
                    # Enter search term
                    search_filter.fill("test")
                    page.wait_for_timeout(500)
                    self.take_baseline_screenshot(page, "search_filter_filled")
                    
                    # Check if there's a search button
                    search_button = page.locator("button:has-text('Search'), .search-button")
                    if search_button.count() > 0:
                        search_button.click()
                        page.wait_for_timeout(1000)
                        self.take_baseline_screenshot(page, "search_applied")
                
                # Test apply filters button
                apply_button = page.locator("button:has-text('Apply Filters'), .apply-filters")
                if apply_button.count() > 0:
                    expect(apply_button).to_be_visible()
                    apply_button.click()
                    page.wait_for_timeout(1000)
                    self.take_baseline_screenshot(page, "filters_applied")
                    
                    # Check if URL contains filter parameters
                    if "filter" in page.url or "status" in page.url or "search" in page.url:
                        print(f"Filter parameters in URL: {page.url}")
                
                # Test clear filters button
                clear_button = page.locator("button:has-text('Clear'), .clear-filters")
                if clear_button.count() > 0:
                    expect(clear_button).to_be_visible()
                    clear_button.click()
                    page.wait_for_timeout(1000)
                    self.take_baseline_screenshot(page, "filters_cleared")
            else:
                print("No additional filter types found")
                self.take_baseline_screenshot(page, "no_filter_types")
        else:
            # Additional filters not implemented
            print("Additional filter options not implemented")
            self.take_baseline_screenshot(page, "no_additional_filters")
    
    # Test 15: Chart interaction functionality
    def test_chart_interaction_functionality(self, authenticated_page: Page):
        """Test chart interaction functionality on dashboard."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "chart_interaction_start")
        
        # Check if charts exist
        charts = page.locator(".chart-container, canvas, [data-chart], .chart")
        
        if charts.count() > 0:
            # Charts are implemented
            expect(charts).to_be_visible()
            
            print(f"Found {charts.count()} chart(s) on dashboard")
            
            # Check chart types
            for i in range(min(charts.count(), 3)):  # Check first 3 charts
                chart = charts.nth(i)
                chart_class = chart.get_attribute("class")
                chart_id = chart.get_attribute("id")
                print(f"Chart {i+1}: class='{chart_class}', id='{chart_id}'")
            
            self.take_baseline_screenshot(page, "charts_visible")
            
            # Check for chart controls
            chart_controls = page.locator(".chart-controls, .chart-options, .chart-buttons")
            if chart_controls.count() > 0:
                expect(chart_controls).to_be_visible()
                
                # Test time range buttons
                time_buttons = chart_controls.locator("button:has-text('Day'), button:has-text('Week'), button:has-text('Month')")
                if time_buttons.count() > 0:
                    # Click first time button
                    if time_buttons.count() > 0:
                        first_button = time_buttons.first
                        first_button.click()
                        page.wait_for_timeout(1000)
                        self.take_baseline_screenshot(page, "chart_time_range_selected")
                
                # Test chart type toggle
                chart_type_toggle = chart_controls.locator("button:has-text('Bar'), button:has-text('Line'), button:has-text('Pie')")
                if chart_type_toggle.count() > 0:
                    # Click first chart type button
                    if chart_type_toggle.count() > 0:
                        first_type = chart_type_toggle.first
                        first_type.click()
                        page.wait_for_timeout(1000)
                        self.take_baseline_screenshot(page, "chart_type_changed")
            
            # Check for chart tooltips (hover interaction)
            # Note: This would require mouse hover simulation
            print("Chart interaction testing would require mouse hover simulation")
            
            # Check for chart data export
            export_button = page.locator("button:has-text('Export'), .export-chart, .download-chart")
            if export_button.count() > 0:
                expect(export_button).to_be_visible()
                print("Chart export button found")
                self.take_baseline_screenshot(page, "chart_export_button")
        else:
            # Charts not implemented
            print("Chart functionality not implemented")
            self.take_baseline_screenshot(page, "no_charts")
    
    # Test 16: Real-time updates functionality
    def test_real_time_updates_functionality(self, authenticated_page: Page):
        """Test real-time updates functionality on dashboard."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "real_time_start")
        
        # Check for real-time update indicators
        real_time_indicator = page.locator(".real-time-indicator, [data-real-time], .live-updates")
        
        if real_time_indicator.count() > 0:
            # Real-time updates are implemented
            expect(real_time_indicator).to_be_visible()
            
            indicator_text = real_time_indicator.text_content()
            print(f"Real-time indicator: {indicator_text}")
            
            self.take_baseline_screenshot(page, "real_time_indicator")
            
            # Check for auto-refresh toggle
            auto_refresh_toggle = page.locator("#auto-refresh, input[type='checkbox'][name*='refresh'], .auto-refresh-toggle")
            if auto_refresh_toggle.count() > 0:
                expect(auto_refresh_toggle).to_be_visible()
                
                # Check the toggle
                auto_refresh_toggle.check()
                page.wait_for_timeout(500)
                self.take_baseline_screenshot(page, "auto_refresh_enabled")
                
                # Wait to see if updates occur
                page.wait_for_timeout(3000)
                self.take_baseline_screenshot(page, "after_auto_refresh_wait")
                
                # Uncheck the toggle
                auto_refresh_toggle.uncheck()
                page.wait_for_timeout(500)
                self.take_baseline_screenshot(page, "auto_refresh_disabled")
            
            # Check for manual refresh button
            manual_refresh = page.locator("button:has-text('Refresh Now'), .manual-refresh")
            if manual_refresh.count() > 0:
                expect(manual_refresh).to_be_visible()
                
                # Click manual refresh
                manual_refresh.click()
                page.wait_for_timeout(2000)
                self.take_baseline_screenshot(page, "manual_refresh_clicked")
                
                # Check for loading indicator
                loading_indicator = page.locator(".loading, .spinner, [aria-busy='true']")
                if loading_indicator.count() > 0:
                    print("Loading indicator shown during manual refresh")
                    self.take_baseline_screenshot(page, "manual_refresh_loading")
        else:
            # Real-time updates not implemented
            print("Real-time updates functionality not implemented")
            self.take_baseline_screenshot(page, "no_real_time_updates")
    
    # Test 17: Export report functionality
    def test_export_report_functionality(self, authenticated_page: Page):
        """Test export report functionality on dashboard."""
        page = authenticated_page
        
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "export_report_start")
        
        # Check for export button
        export_button = page.locator("#export-report, button:has-text('Export'), .export-button")
        
        if export_button.count() > 0:
            # Export functionality is implemented
            expect(export_button).to_be_visible()
            
            self.take_baseline_screenshot(page, "export_button_visible")
            
            # Check for export options dropdown
            export_dropdown = page.locator(".export-dropdown, .dropdown-menu:has-text('Export')")
            if export_dropdown.count() > 0:
                # It's a dropdown with options
                export_button.click()
                page.wait_for_timeout(500)
                expect(export_dropdown).to_be_visible()
                
                self.take_baseline_screenshot(page, "export_dropdown_open")
                
                # Check export format options
                export_options = export_dropdown.locator("a, button")
                print(f"Found {export_options.count()} export options")
                
                for i in range(min(export_options.count(), 3)):
                    option = export_options.nth(i)
                    option_text = option.text_content()
                    print(f"  Export option {i+1}: {option_text}")
                
                # Test clicking on an export option (e.g., CSV)
                csv_option = export_dropdown.locator("a:has-text('CSV'), button:has-text('CSV')")
                if csv_option.count() > 0:
                    # Note: This would trigger a file download
                    print("CSV export option found - would trigger file download")
                    self.take_baseline_screenshot(page, "csv_export_option")
                    
                    # We can't test actual download in this test, but we can verify the option exists
                else:
                    print("No CSV export option found")
                
                # Close dropdown
                export_button.click()
                page.wait_for_timeout(500)
                expect(export_dropdown).not_to_be_visible()
                self.take_baseline_screenshot(page, "export_dropdown_closed")
            else:
                # It's a direct export button
                print("Direct export button (no dropdown options)")
                
                # Click export button (would trigger download)
                # Note: We can't test actual file download
                export_button.click()
                page.wait_for_timeout(2000)
                self.take_baseline_screenshot(page, "export_clicked")
                
                # Check for success message
                success_message = page.locator(".flash-success, .alert-success, .success-message")
                if success_message.count() > 0:
                    message_text = success_message.text_content()
                    print(f"Export success message: {message_text}")
                    self.take_baseline_screenshot(page, "export_success_message")
                else:
                    print("No success message shown after export")
        else:
            # Export functionality not implemented
            print("Export report functionality not implemented")
            self.take_baseline_screenshot(page, "no_export_button")
        
        # Check for export settings/options
        export_settings = page.locator(".export-settings, #export-options, .export-config")
        if export_settings.count() > 0:
            expect(export_settings).to_be_visible()
            
            # Test date range selection for export
            date_from = page.locator("#export-date-from, input[name='date_from']")
            date_to = page.locator("#export-date-to, input[name='date_to']")
            
            if date_from.count() > 0 and date_to.count() > 0:
                expect(date_from).to_be_visible()
                expect(date_to).to_be_visible()
                
                # Set date range
                date_from.fill("2024-01-01")
                date_to.fill("2024-12-31")
                page.wait_for_timeout(500)
                self.take_baseline_screenshot(page, "export_date_range_set")
                
                print("Export date range selectors found and configured")
            
            # Test export format selection
            format_select = page.locator("select[name='format'], #export-format")
            if format_select.count() > 0:
                expect(format_select).to_be_visible()
                
                # Select CSV format
                format_options = format_select.locator("option")
                for i in range(format_options.count()):
                    option = format_options.nth(i)
                    option_value = option.get_attribute("value")
                    if option_value and "csv" in option_value.lower():
                        format_select.select_option(option_value)
                        break
                
                page.wait_for_timeout(500)
                self.take_baseline_screenshot(page, "export_format_selected")
                
                selected_format = format_select.input_value()
                print(f"Selected export format: {selected_format}")




def run_dashboard_baseline_tests():
    """Run dashboard page baseline tests and show summary."""
    import subprocess
    import sys
    
    print("=" * 60)
    print("SMS Panel Dashboard Page Baseline Tests")
    print("=" * 60)
    print("Features:")
    print("- Trace recording: DISABLED by default")
    print("- Video recording: DISABLED by default")
    print("- Screenshot comparison: ENABLED")
    print("- Baseline images: test_ui/test_dashboard_baseline_screenshots/")
    print("- Authentication: Auto-login with test_SMSadmin credentials")
    print("=" * 60)
    
    # Create directories
    os.makedirs("test_ui/test_dashboard_baseline_screenshots", exist_ok=True)
    
    # Run tests
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        __file__,
        "-v",
        "--headed"
    ])
    
    print("\n" + "=" * 60)
    print("DASHBOARD PAGE BASELINE TEST SUMMARY")
    print("=" * 60)
    
    # Count baseline files
    baseline_dir = "test_ui/test_dashboard_baseline_screenshots"
    if os.path.exists(baseline_dir):
        baseline_files = [f for f in os.listdir(baseline_dir) if f.endswith('.png')]
        print(f"Dashboard baseline screenshots: {len(baseline_files)} files")
        
        # Show some examples
        if baseline_files:
            print("\nExample baseline files:")
            for f in baseline_files[:5]:
                print(f"  - {f}")
            if len(baseline_files) > 5:
                print(f"  - ... and {len(baseline_files) - 5} more")
    
    print("\nTo update baseline images:")
    print("1. Delete files from test_dashboard_baseline_screenshots/")
    print("2. Run tests again to create new baselines")
    print("\nTo enable trace/video recording:")
    print("Edit test_ui/test_dashboard_page_baseline.py")
    print("Set ENABLE_TRACE = True for trace recording")
    print("Set ENABLE_VIDEO = True for video recording")
    
    return result.returncode


if __name__ == "__main__":
    """Command line interface."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        sys.exit(run_dashboard_baseline_tests())
    else:
        print("Usage:")
        print("  python test_ui/test_dashboard_page_baseline.py run")
        print()
        print("Or run with pytest directly:")
        print("  pytest test_ui/test_dashboard_page_baseline.py -v --headed")
        print()
        print("Test suite includes:")
        print("  1. Dashboard page loads after authentication")
        print("  2. Dashboard statistics cards")
        print("  3. Queue status display")
        print("  4. Messages section with time filters")
        print("  5. Messages table structure")
        print("  6. Pagination functionality")
        print("  7. Navigation from dashboard")
        print("  8. Responsive design")
        print("  9. Access without authentication")
        print("  10. Footer and complete navigation")
        print("  11. Message detail view")
        print("  12. Statistics cards refresh functionality")
        print("  13. Messages table sorting functionality")
        print("  14. Additional message filter options")
        print("  15. Chart interaction functionality")
        print("  16. Real-time updates functionality")
        print("  17. Export report functionality")

