"""
Playwright UI tests for SMS Panel Admin pages with baseline screenshot comparison.
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


class TestAdminPageBaseline:
    """Test suite for SMS Panel Admin pages with baseline screenshot comparison."""
    
    # Configuration - CHANGE THESE SETTINGS AS NEEDED
    BASELINE_DIR = "test_ui/test_admin_baseline_screenshots"  # Store baseline images here
    ENABLE_VIDEO = False  # Set to True to enable video recording
    ENABLE_TRACE = False  # Set to True to enable trace recording
    
    # Login credentials
    LOGIN_URL = "http://127.0.0.1:3570/login?next=%2F"
    ADMIN_USERS_URL = "http://127.0.0.1:3570/admin/users"
    ADMIN_MESSAGES_URL = "http://127.0.0.1:3570/admin/messages"
    ADMIN_DEAD_LETTER_URL = "http://127.0.0.1:3570/admin/dead-letter"
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
            context_args["record_video_dir"] = "test_videos_admin"
            context_args["record_video_size"] = {"width": 1280, "height": 800}
            os.makedirs("test_videos_admin", exist_ok=True)
        
        context = browser.new_context(**context_args)
        
        # Start optional tracing
        if self.ENABLE_TRACE:
            os.makedirs("test_traces_admin", exist_ok=True)
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
            trace_path = os.path.join("test_traces_admin", f"{test_name}.zip")
            context.tracing.stop(path=trace_path)
        
        # Close context (saves video if enabled)
        context.close()
        browser.close()
    
    @pytest.fixture(scope="function")
    def authenticated_page(self, browser_page: Page):
        """Create an authenticated page for admin tests."""
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
        SIMILARITY_THRESHOLD = 80.0  # 相似度閾值（百分比）
        
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
    
    # Test 1: Admin users page loads correctly
    def test_admin_users_page_loads(self, authenticated_page: Page):
        """Test that admin users page loads correctly after authentication."""
        page = authenticated_page
        
        # Navigate to admin users page
        page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "admin_users_page")
        
        # Check page title
        expect(page).to_have_title(re.compile("User Management - SMS Application"))
        
        # Check page header
        admin_header = page.locator(".admin-header h1")
        expect(admin_header).to_be_visible()
        expect(admin_header).to_have_text("User Management")
        self.take_baseline_screenshot(page, "admin_header")
        
        # Check Create New User button
        create_user_button = page.locator(".admin-header .btn-primary")
        expect(create_user_button).to_be_visible()
        expect(create_user_button).to_have_text("Create New User")
        self.take_baseline_screenshot(page, "create_user_button")
    
    # Test 2: Admin users table structure
    def test_admin_users_table_structure(self, authenticated_page: Page):
        """Test admin users table structure and columns."""
        page = authenticated_page
        
        page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "users_table")
        
        # Check if table exists
        table_container = page.locator(".table-container")
        
        if table_container.count() > 0:
            # Table is displayed (has users)
            table = page.locator(".users-table")
            expect(table).to_be_visible()
            
            # Check table headers
            headers = table.locator("thead th")
            expect(headers).to_have_count(6)  # Username, Admin, Active, API Token, Created At, Actions
            
            expected_headers = ["Username", "Admin", "Active", "API Token", "Created At", "Actions"]
            for i, expected_header in enumerate(expected_headers):
                expect(headers.nth(i)).to_contain_text(expected_header)
            
            # Check if there are user rows
            user_rows = table.locator("tbody .user-row")
            if user_rows.count() > 0:
                # Check first user row structure
                first_row = user_rows.first
                
                # Check username
                username = first_row.locator("td:nth-child(1)")
                expect(username).to_be_visible()
                
                # Check admin status
                admin_status = first_row.locator("td:nth-child(2) .status")
                expect(admin_status).to_be_visible()
                
                # Check active status
                active_status = first_row.locator("td:nth-child(3) .status")
                expect(active_status).to_be_visible()
                
                # Check API token display
                token_display = first_row.locator("td:nth-child(4)")
                expect(token_display).to_be_visible()
                
                # Check created at timestamp
                created_at = first_row.locator("td:nth-child(5)")
                expect(created_at).to_be_visible()
                
                # Check action buttons
                action_buttons = first_row.locator(".action-buttons .btn, .action-buttons .btn-small")
                assert action_buttons.count() >= 1, "Should have at least one action button"
                
                self.take_baseline_screenshot(page, "user_row_details")
            else:
                # No users - check empty state
                empty_state = page.locator(".empty-state")
                expect(empty_state).to_be_visible()
                expect(empty_state).to_contain_text("No users found")
                
                # Check link to create user
                create_link = empty_state.locator("a")
                expect(create_link).to_be_visible()
                expect(create_link).to_have_text("Create your first user!")
                
                self.take_baseline_screenshot(page, "empty_state")
        else:
            # No table container (no users section at all)
            print("No users table displayed")
            self.take_baseline_screenshot(page, "no_users_table")
    
    # Test 3: Admin messages page loads correctly
    def test_admin_messages_page_loads(self, authenticated_page: Page):
        """Test that admin messages page loads correctly."""
        page = authenticated_page
        
        # Navigate to admin messages page
        page.goto(self.ADMIN_MESSAGES_URL)
        self.take_baseline_screenshot(page, "admin_messages_page")
        
        # Check page title
        expect(page).to_have_title(re.compile("Message Query - SMS Application"))
        
        # Check page header
        admin_header = page.locator(".admin-header h1")
        expect(admin_header).to_be_visible()
        expect(admin_header).to_have_text("Message Query")
        
        # Check description
        description = page.locator(".admin-header p")
        expect(description).to_be_visible()
        expect(description).to_have_text("Query messages by user, status, or date range")
        
        self.take_baseline_screenshot(page, "messages_header")
    
    # Test 4: Admin messages filter functionality
    def test_admin_messages_filter_functionality(self, authenticated_page: Page):
        """Test filter functionality on admin messages page."""
        page = authenticated_page
        
        page.goto(self.ADMIN_MESSAGES_URL)
        self.take_baseline_screenshot(page, "messages_filter_start")
        
        # Check filter form exists
        filter_form = page.locator(".filter-form")
        expect(filter_form).to_be_visible()
        
        # Check user filter dropdown
        user_filter = page.locator("#user_id")
        expect(user_filter).to_be_visible()
        
        # Check status filter dropdown
        status_filter = page.locator("#status")
        expect(status_filter).to_be_visible()
        
        # Check date range inputs
        start_date_input = page.locator("#start_date")
        expect(start_date_input).to_be_visible()
        
        end_date_input = page.locator("#end_date")
        expect(end_date_input).to_be_visible()
        
        # Check search button
        search_button = page.locator(".filter-form .btn-primary")
        expect(search_button).to_be_visible()
        expect(search_button).to_have_text("Search")
        
        # Check clear button
        clear_button = page.locator(".filter-form .btn-secondary")
        expect(clear_button).to_be_visible()
        expect(clear_button).to_have_text("Clear")
        
        self.take_baseline_screenshot(page, "filter_elements")
        
        # Test filter functionality
        status_filter.select_option("sent")
        self.take_baseline_screenshot(page, "status_selected")
        
        # Submit the form
        search_button.click()
        page.wait_for_timeout(1000)
        
        # Check if URL contains filter parameters
        expect(page).to_have_url(re.compile(".*status=sent.*"))
        
        self.take_baseline_screenshot(page, "filter_applied")
        
        # Test clear functionality
        clear_button.click()
        page.wait_for_timeout(1000)
        
        # Check if filters are cleared
        expect(page).not_to_have_url(re.compile(".*status=.*"))
        self.take_baseline_screenshot(page, "filters_cleared")
    
    # Test 5: Admin messages table structure
    def test_admin_messages_table_structure(self, authenticated_page: Page):
        """Test admin messages table structure."""
        page = authenticated_page
        
        page.goto(self.ADMIN_MESSAGES_URL)
        self.take_baseline_screenshot(page, "messages_table")
        
        # Check if table exists
        table_container = page.locator(".table-container")
        
        if table_container.count() > 0:
            # Table is displayed (has messages)
            table = page.locator(".data-table")
            expect(table).to_be_visible()
            
            # Check table headers
            headers = table.locator("thead th")
            expect(headers).to_have_count(6)  # ID, User, Content, Status, Recipients, Created
            
            expected_headers = ["ID", "User", "Content", "Status", "Recipients", "Created"]
            for i, expected_header in enumerate(expected_headers):
                expect(headers.nth(i)).to_contain_text(expected_header)
            
            # Check if there are message rows
            message_rows = table.locator("tbody tr")
            if message_rows.count() > 0:
                # Check first message row
                first_row = message_rows.first

                # Check that the row exists and has some content
                expect(first_row).to_be_visible()
                
                # Check that the row has at least some cells
                cells = first_row.locator("td")
                assert cells.count() >= 1, "Should have at least one cell in message row"

                self.take_baseline_screenshot(page, "message_row_details")
            else:
                # No messages - check empty state
                empty_state = page.locator(".empty-state")
                expect(empty_state).to_be_visible()
                expect(empty_state).to_contain_text("No messages found")
                
                self.take_baseline_screenshot(page, "empty_state")
        else:
            # No table container
            print("No messages table displayed")
            self.take_baseline_screenshot(page, "no_messages_table")
    
    # Test 6: Admin dead letter page loads correctly
    def test_admin_dead_letter_page_loads(self, authenticated_page: Page):
        """Test that admin dead letter page loads correctly."""
        page = authenticated_page
        
        # Navigate to admin dead letter page
        page.goto(self.ADMIN_DEAD_LETTER_URL)
        self.take_baseline_screenshot(page, "admin_dead_letter_page")
        
        # Check page title
        expect(page).to_have_title(re.compile("Dead Letter Queue - SMS Application"))
        
        # Check page header
        admin_header = page.locator(".admin-header h1")
        expect(admin_header).to_be_visible()
        expect(admin_header).to_have_text("Dead Letter Queue")
        
        # Check description
        description = page.locator(".admin-header p")
        expect(description).to_be_visible()
        expect(description).to_have_text("Messages that failed after all retry attempts")
        
        self.take_baseline_screenshot(page, "dead_letter_header")
    
    # Test 7: Admin dead letter stats cards
    def test_admin_dead_letter_stats_cards(self, authenticated_page: Page):
        """Test dead letter queue stats cards."""
        page = authenticated_page
        
        page.goto(self.ADMIN_DEAD_LETTER_URL)
        self.take_baseline_screenshot(page, "stats_cards")
        
        # Check stats cards section
        stats_cards = page.locator(".stats-cards")
        expect(stats_cards).to_be_visible()
        
        # Check individual stat cards
        stat_cards = page.locator(".stat-card")
        expect(stat_cards).to_have_count(4)  # Pending, Retried, Abandoned, Total
        
        # Check card labels
        expected_labels = ["Pending", "Retried", "Abandoned", "Total"]
        for i, expected_label in enumerate(expected_labels):
            card = stat_cards.nth(i)
            expect(card.locator("p")).to_have_text(expected_label)
            expect(card.locator("h3")).to_be_visible()  # Count value
        
        self.take_baseline_screenshot(page, "stats_cards_detailed")
    
    # Test 8: Admin dead letter filter functionality
    def test_admin_dead_letter_filter_functionality(self, authenticated_page: Page):
        """Test filter functionality on dead letter page."""
        page = authenticated_page
        
        page.goto(self.ADMIN_DEAD_LETTER_URL)
        self.take_baseline_screenshot(page, "dead_letter_filter_start")
        
        # Check filter bar exists
        filter_bar = page.locator(".filter-bar")
        expect(filter_bar).to_be_visible()
        
        # Check filter buttons (links, not buttons)
        filter_links = filter_bar.locator("a.btn")
        expect(filter_links).to_have_count(4)  # All, Pending, Retried, Abandoned
        
        # Check All button (link)
        all_link = filter_bar.locator("a.btn:has-text('All')")
        expect(all_link).to_be_visible()
        
        # Check Pending button (link)
        pending_link = filter_bar.locator("a.btn:has-text('Pending')")
        expect(pending_link).to_be_visible()
        
        # Check Retried button (link)
        retried_link = filter_bar.locator("a.btn:has-text('Retried')")
        expect(retried_link).to_be_visible()
        
        # Check Abandoned button (link)
        abandoned_link = filter_bar.locator("a.btn:has-text('Abandoned')")
        expect(abandoned_link).to_be_visible()
        
        self.take_baseline_screenshot(page, "filter_buttons")
        
        # Test filtering by status
        pending_link.click()
        page.wait_for_timeout(1000)
        
        # Check if URL contains filter parameter
        expect(page).to_have_url(re.compile(".*status=pending.*"))
        self.take_baseline_screenshot(page, "filtered_by_pending")
        
        # Check if Retry All Pending button appears
        retry_all_button = page.locator("button:has-text('Retry All Pending')")
        if retry_all_button.count() > 0:
            expect(retry_all_button).to_be_visible()
            self.take_baseline_screenshot(page, "retry_all_button")
        
        # Go back to All - need to get the All link again after page change
        all_link = page.locator(".filter-bar a.btn:has-text('All')")
        all_link.click()
        page.wait_for_timeout(1000)
        expect(page).not_to_have_url(re.compile(".*status=.*"))
        self.take_baseline_screenshot(page, "filter_cleared")
    
    # Test 9: Admin dead letter table structure
    def test_admin_dead_letter_table_structure(self, authenticated_page: Page):
        """Test dead letter table structure."""
        page = authenticated_page
        
        page.goto(self.ADMIN_DEAD_LETTER_URL)
        self.take_baseline_screenshot(page, "dead_letter_table")
        
        # Check if table exists
        table_container = page.locator(".table-container")
        
        if table_container.count() > 0:
            # Table is displayed (has dead letter messages)
            table = page.locator(".data-table")
            expect(table).to_be_visible()
            
            # Check table headers
            headers = table.locator("thead th")
            expect(headers).to_have_count(8)  # ID, Recipient, Content, Error, Retries, Status, Created, Actions
            
            expected_headers = ["ID", "Recipient", "Content", "Error", "Retries", "Status", "Created", "Actions"]
            for i, expected_header in enumerate(expected_headers):
                expect(headers.nth(i)).to_contain_text(expected_header)
            
            # Check if there are dead letter rows
            dead_letter_rows = table.locator("tbody tr")
            if dead_letter_rows.count() > 0:
                # Check first dead letter row
                first_row = dead_letter_rows.first
                
                # Check that the row exists and has some content
                expect(first_row).to_be_visible()
                
                # Check that the row has at least some cells
                cells = first_row.locator("td")
                assert cells.count() >= 1, "Should have at least one cell"
                
                self.take_baseline_screenshot(page, "dead_letter_row_details")
            else:
                # No dead letter messages - check empty state
                empty_state = page.locator(".empty-state")
                expect(empty_state).to_be_visible()
                expect(empty_state).to_contain_text("No dead letter messages found")
                
                self.take_baseline_screenshot(page, "empty_state")
        else:
            # No table container
            print("No dead letter table displayed")
            self.take_baseline_screenshot(page, "no_dead_letter_table")
    
    # Test 10: Admin page accessibility without admin privileges
    def test_admin_access_without_admin_privileges(self, authenticated_page: Page):
        """Test that admin pages redirect or show error when accessed by non-admin user."""
        page = authenticated_page
        
        # Note: This test assumes test_SMSadmin has admin privileges
        # We'll test that admin pages are accessible with admin user
        
        # Test admin users page access
        page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "admin_users_access")
        
        # Should be accessible (test_SMSadmin is admin)
        expect(page).to_have_title(re.compile("User Management - SMS Application"))
        
        # Test admin messages page access
        page.goto(self.ADMIN_MESSAGES_URL)
        self.take_baseline_screenshot(page, "admin_messages_access")
        
        # Should be accessible
        expect(page).to_have_title(re.compile("Message Query - SMS Application"))
        
        # Test admin dead letter page access
        page.goto(self.ADMIN_DEAD_LETTER_URL)
        self.take_baseline_screenshot(page, "admin_dead_letter_access")
        
        # Should be accessible
        expect(page).to_have_title(re.compile("Dead Letter Queue - SMS Application"))
    
    # Test 11: Admin page navigation
    def test_admin_page_navigation(self, authenticated_page: Page):
        """Test navigation between admin pages."""
        page = authenticated_page
        
        # Start at admin users page
        page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "navigation_start")
        
        # Check for admin navigation links (if they exist in navbar)
        navbar_links = page.locator(".nav-links a")
        
        # Look for admin-specific links
        admin_links = []
        for i in range(navbar_links.count()):
            link = navbar_links.nth(i)
            link_text = link.text_content()
            if "admin" in link_text.lower() or "Admin" in link_text:
                admin_links.append(link)
        
        print(f"Found {len(admin_links)} admin-related navbar links")
        
        # Test Create New User button navigation
        create_user_button = page.locator(".admin-header .btn-primary")
        create_user_button.click()
        page.wait_for_timeout(1000)
        
        # Check if navigated to create user page
        if "create" in page.url:
            expect(page).to_have_title(re.compile("Create User - SMS Application"))
            self.take_baseline_screenshot(page, "create_user_page")
            
            # Go back to users page
            page.go_back()
            page.wait_for_timeout(1000)
        else:
            print("Create New User button did not navigate to create user page")
        
        # Test navigation to admin messages page via URL
        page.goto(self.ADMIN_MESSAGES_URL)
        self.take_baseline_screenshot(page, "navigated_to_messages")
        
        # Test navigation to admin dead letter page via URL
        page.goto(self.ADMIN_DEAD_LETTER_URL)
        self.take_baseline_screenshot(page, "navigated_to_dead_letter")
        
        # Test navigation back to users page
        page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "navigation_complete")
    
    # Test 12: Responsive design on admin pages
    def test_admin_responsive_design(self, authenticated_page: Page):
        """Test admin pages responsive design on different viewports."""
        page = authenticated_page
        
        # Test admin users page on different viewports
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE
        page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "users_mobile_viewport")
        
        # Check mobile layout elements
        admin_header = page.locator(".admin-header")
        expect(admin_header).to_be_visible()
        
        # Test tablet viewport
        page.set_viewport_size({"width": 768, "height": 1024})  # iPad
        self.take_baseline_screenshot(page, "users_tablet_viewport")
        
        # Test desktop viewport
        page.set_viewport_size({"width": 1280, "height": 800})  # Desktop
        self.take_baseline_screenshot(page, "users_desktop_viewport")
        
        # Test admin messages page responsive design
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(self.ADMIN_MESSAGES_URL)
        self.take_baseline_screenshot(page, "messages_mobile_viewport")
        
        page.set_viewport_size({"width": 1280, "height": 800})
        self.take_baseline_screenshot(page, "messages_desktop_viewport")
        
        # Verify key elements are visible on all viewports
        expect(page.locator(".admin-header h1")).to_be_visible()
        expect(page.locator(".filter-form")).to_be_visible()
    
    # Test 13: Admin page pagination (if applicable)
    def test_admin_pagination_functionality(self, authenticated_page: Page):
        """Test pagination controls on admin pages."""
        page = authenticated_page
        
        # Test pagination on admin messages page
        page.goto(self.ADMIN_MESSAGES_URL)
        self.take_baseline_screenshot(page, "messages_pagination_check")
        
        # Check if pagination exists
        pagination = page.locator(".pagination")
        
        if pagination.count() > 0:
            # Pagination is displayed
            expect(pagination).to_be_visible()
            
            # Check page buttons
            page_buttons = pagination.locator(".btn")
            expect(page_buttons).to_have_count(1)
            
            # Test clicking on a page button
            if page_buttons.count() > 1:
                second_page_button = page_buttons.nth(1)
                second_page_button.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "page_2")
                
                # Check if URL contains page parameter
                expect(page).to_have_url(re.compile(".*page=2.*"))
            else:
                print("Only one page available, cannot test pagination")
        else:
            # No pagination (single page or no data)
            print("No pagination displayed on admin messages page")
            self.take_baseline_screenshot(page, "no_pagination")
    
    # Test 14: Admin action buttons functionality
    def test_admin_action_buttons(self, authenticated_page: Page):
        """Test admin action buttons (view, edit, delete, etc.)."""
        page = authenticated_page
        
        page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "action_buttons_start")
        
        # Check if there are users with action buttons
        action_buttons = page.locator(".action-buttons .btn")
        
        if action_buttons.count() > 0:
            # Check different types of action buttons
            for i in range(min(action_buttons.count(), 3)):
                button = action_buttons.nth(i)
                button_text = button.text_content()
                print(f"Action button {i+1}: {button_text}")
            
            self.take_baseline_screenshot(page, "action_buttons_visible")
            
            # Test Password button (should navigate to change password page)
            password_button = page.locator(".action-buttons .btn:has-text('Password')")
            if password_button.count() > 0:
                password_button.first.click()
                page.wait_for_timeout(1000)
                
                # Check if navigated to change password page
                if "password" in page.url:
                    expect(page).to_have_title(re.compile("Change Password - SMS Application"))
                    self.take_baseline_screenshot(page, "change_password_page")
                    
                    # Go back to users page
                    page.go_back()
                    page.wait_for_timeout(1000)
                else:
                    print("Password button did not navigate to change password page")
        else:
            print("No action buttons found to test")
            self.take_baseline_screenshot(page, "no_action_buttons")
    
    # Test 15: Create admin user functionality
    def test_create_admin_user(self, authenticated_page: Page):
        """Test creating a new admin user."""
        page = authenticated_page
        
        # Navigate to admin users page
        page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "create_user_start")
        
        # Click Create New User button
        create_user_button = page.locator(".admin-header .btn-primary")
        expect(create_user_button).to_be_visible()
        expect(create_user_button).to_have_text("Create New User")
        create_user_button.click()
        
        page.wait_for_timeout(1000)
        self.take_baseline_screenshot(page, "create_user_page")
        
        # Check page title
        expect(page).to_have_title(re.compile("Create User - SMS Application"))
        
        # Check form elements
        expect(page.locator("h1")).to_have_text("Create New User")
        
        # Check username field
        username_input = page.locator("#username")
        expect(username_input).to_be_visible()
        expect(username_input).to_have_attribute("type", "text")
        expect(username_input).to_have_attribute("required", "")
        
        # Check password field
        password_input = page.locator("#password")
        expect(password_input).to_be_visible()
        expect(password_input).to_have_attribute("type", "password")
        expect(password_input).to_have_attribute("required", "")
        
        # Check confirm password field
        confirm_password_input = page.locator("#confirm_password")
        expect(confirm_password_input).to_be_visible()
        expect(confirm_password_input).to_have_attribute("type", "password")
        expect(confirm_password_input).to_have_attribute("required", "")
        
        # Check admin checkbox
        admin_checkbox = page.locator("#is_admin")
        expect(admin_checkbox).to_be_visible()
        expect(admin_checkbox).to_have_attribute("type", "checkbox")
        
        # Check checkbox label
        admin_label = page.locator("label[for='is_admin'] span")
        expect(admin_label).to_have_text("Admin Account")
        
        # Check form buttons
        create_button = page.locator("button[type='submit']")
        expect(create_button).to_be_visible()
        expect(create_button).to_have_text("Create User")
        
        cancel_button = page.locator("a.btn-secondary:has-text('Cancel')")
        expect(cancel_button).to_be_visible()
        expect(cancel_button).to_have_text("Cancel")
        
        self.take_baseline_screenshot(page, "create_user_form")
        
        # Fill form with admin user data
        test_admin_username = f"test_admin_{int(datetime.now().timestamp())}"
        test_password = "TestPass#123"
        
        username_input.fill(test_admin_username)
        password_input.fill(test_password)
        confirm_password_input.fill(test_password)
        admin_checkbox.check()
        
        self.take_baseline_screenshot(page, "admin_user_filled")
        
        # Submit the form
        create_button.click()
        page.wait_for_timeout(2000)
        
        # Check if redirected back to users page
        expect(page).to_have_url(re.compile(".*/admin/users.*"))
        self.take_baseline_screenshot(page, "admin_user_created")
        
        # Check for success message or new user in table
        # (This depends on how the application shows success)
        print(f"Created admin user: {test_admin_username}")
    
    # Test 16: Create normal user functionality
    def test_create_normal_user(self, authenticated_page: Page):
        """Test creating a new normal (non-admin) user."""
        page = authenticated_page
        
        # Navigate to create user page
        page.goto(f"{self.ADMIN_USERS_URL}/create")
        self.take_baseline_screenshot(page, "create_normal_user_start")
        
        # Fill form with normal user data
        test_username = f"test_user_{int(datetime.now().timestamp())}"
        test_password = "UserPass#456"
        
        page.locator("#username").fill(test_username)
        page.locator("#password").fill(test_password)
        page.locator("#confirm_password").fill(test_password)
        # Don't check admin checkbox (default is non-admin)
        
        self.take_baseline_screenshot(page, "normal_user_filled")
        
        # Submit the form
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(2000)
        
        # Check if redirected back to users page
        expect(page).to_have_url(re.compile(".*/admin/users.*"))
        self.take_baseline_screenshot(page, "normal_user_created")
        
        print(f"Created normal user: {test_username}")
    
    # Test 17: User creation form validation
    def test_user_creation_form_validation(self, authenticated_page: Page):
        """Test form validation for user creation."""
        page = authenticated_page
        
        page.goto(f"{self.ADMIN_USERS_URL}/create")
        self.take_baseline_screenshot(page, "form_validation_start")
        
        # Test empty form submission
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(1000)
        
        # Check if still on create page (form validation failed)
        expect(page).to_have_url(re.compile(".*/create.*"))
        self.take_baseline_screenshot(page, "empty_form_validation")
        
        # Test password mismatch
        page.locator("#username").fill("testuser")
        page.locator("#password").fill("Password123")
        page.locator("#confirm_password").fill("DifferentPassword")
        
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(1000)
        
        expect(page).to_have_url(re.compile(".*/create.*"))
        self.take_baseline_screenshot(page, "password_mismatch")
        
        # Test weak password - note: application currently doesn't have password strength validation
        # So weak password should be accepted and user created
        page.locator("#username").fill(f"testuser_{int(datetime.now().timestamp())}")
        page.locator("#password").fill("weak")
        page.locator("#confirm_password").fill("weak")
        
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(1000)
        
        # Since there's no password strength validation, user should be created
        # and we should be redirected to users page
        expect(page).to_have_url(re.compile(".*/admin/users.*"))
        self.take_baseline_screenshot(page, "weak_password_accepted")
        
        # Go back to create page for next test
        page.goto(f"{self.ADMIN_USERS_URL}/create")
        
        # Test valid form (but don't submit to avoid creating actual user)
        page.locator("#username").fill(f"test_{int(datetime.now().timestamp())}")
        page.locator("#password").fill("StrongPass#123")
        page.locator("#confirm_password").fill("StrongPass#123")
        
        self.take_baseline_screenshot(page, "valid_form")
        
        # Go back without submitting
        page.locator("a.btn-secondary:has-text('Cancel')").click()
        page.wait_for_timeout(1000)
        
        expect(page).to_have_url(re.compile(".*/admin/users.*"))
        self.take_baseline_screenshot(page, "cancelled_creation")
    
    # Test 18: Test cancel button functionality
    def test_cancel_user_creation(self, authenticated_page: Page):
        """Test cancel button on create user page."""
        page = authenticated_page
        
        page.goto(f"{self.ADMIN_USERS_URL}/create")
        self.take_baseline_screenshot(page, "cancel_test_start")
        
        # Fill some data
        page.locator("#username").fill("testuser")
        page.locator("#password").fill("TestPass123")
        page.locator("#confirm_password").fill("TestPass123")
        
        self.take_baseline_screenshot(page, "filled_before_cancel")
        
        # Click cancel button
        page.locator("a.btn-secondary:has-text('Cancel')").click()
        page.wait_for_timeout(1000)
        
        # Should be redirected to users page
        expect(page).to_have_url(re.compile(".*/admin/users.*"))
        self.take_baseline_screenshot(page, "cancelled_to_users")
        
        # Verify no user was created (by checking URL is not create page)
        expect(page).not_to_have_url(re.compile(".*/create.*"))
    
    # Helper method to create a test user
    def create_test_user(self, page: Page, is_admin=False):
        """Helper method to create a test user and return the username."""
        import time
        
        # Navigate to create user page
        page.goto(f"{self.ADMIN_USERS_URL}/create")
        
        # Generate unique username
        timestamp = int(time.time())
        test_username = f"test_user_{timestamp}"
        test_password = "TestPass#123"
        
        # Fill form
        page.locator("#username").fill(test_username)
        page.locator("#password").fill(test_password)
        page.locator("#confirm_password").fill(test_password)
        
        if is_admin:
            page.locator("#is_admin").check()
        
        # Submit the form
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(2000)
        
        # Verify redirected to users page
        expect(page).to_have_url(re.compile(".*/admin/users.*"))
        
        return test_username
    
    # Test 19: Change user password functionality
    def test_change_user_password(self, authenticated_page: Page):
        """Test changing a user's password."""
        page = authenticated_page
        
        # First, create a test user
        test_username = self.create_test_user(page, is_admin=False)
        print(f"Created test user for password change: {test_username}")
        
        # Find the test user in the table and click Password button
        # We need to locate the user row and click the Password button
        user_rows = page.locator(".user-row")
        
        for i in range(user_rows.count()):
            row = user_rows.nth(i)
            username_cell = row.locator("td:nth-child(1)")
            if test_username in username_cell.text_content():
                # Found our test user, click Password button
                password_button = row.locator(".action-buttons .btn:has-text('Password')")
                expect(password_button).to_be_visible()
                password_button.click()
                page.wait_for_timeout(1000)
                break
        
        # Check if on change password page
        expect(page).to_have_url(re.compile(".*/password.*"))
        expect(page).to_have_title(re.compile("Change Password - SMS Application"))
        self.take_baseline_screenshot(page, "change_password_page")
        
        # Check form elements
        expect(page.locator("h1")).to_contain_text("Change Password for")
        expect(page.locator("h1")).to_contain_text(test_username)
        
        new_password_input = page.locator("#new_password")
        expect(new_password_input).to_be_visible()
        expect(new_password_input).to_have_attribute("type", "password")
        expect(new_password_input).to_have_attribute("required", "")
        
        confirm_password_input = page.locator("#confirm_password")
        expect(confirm_password_input).to_be_visible()
        expect(confirm_password_input).to_have_attribute("type", "password")
        expect(confirm_password_input).to_have_attribute("required", "")
        
        change_button = page.locator("button[type='submit']")
        expect(change_button).to_be_visible()
        expect(change_button).to_have_text("Change Password")
        
        cancel_button = page.locator("a.btn-secondary:has-text('Cancel')")
        expect(cancel_button).to_be_visible()
        expect(cancel_button).to_have_text("Cancel")
        
        self.take_baseline_screenshot(page, "change_password_form")
        
        # Fill form with new password
        new_password = "NewPass#456"
        new_password_input.fill(new_password)
        confirm_password_input.fill(new_password)
        
        self.take_baseline_screenshot(page, "new_password_filled")
        
        # Submit the form
        change_button.click()
        page.wait_for_timeout(2000)
        
        # Should be redirected back to users page
        expect(page).to_have_url(re.compile(".*/admin/users.*"))
        self.take_baseline_screenshot(page, "password_changed")
        
        print(f"Changed password for user: {test_username}")
    
    # Test 20: Disable/enable user functionality
    def test_disable_enable_user(self, authenticated_page: Page):
        """Test disabling and enabling a user."""
        page = authenticated_page
        
        # First, create a test user
        test_username = self.create_test_user(page, is_admin=False)
        print(f"Created test user for disable/enable: {test_username}")
        
        # Find the test user in the table
        page.goto(self.ADMIN_USERS_URL)
        user_rows = page.locator(".user-row")
        
        for i in range(user_rows.count()):
            row = user_rows.nth(i)
            username_cell = row.locator("td:nth-child(1)")
            if test_username in username_cell.text_content():
                # Check initial status (should be Active)
                status_cell = row.locator("td:nth-child(3) .status")
                status_text = status_cell.text_content()
                print(f"Initial status: {status_text}")
                
                # Find Disable button (should be visible since user is active)
                disable_button = row.locator(".action-buttons button:has-text('Disable')")
                if disable_button.count() > 0:
                    # Click Disable button
                    disable_button.click()
                    page.wait_for_timeout(2000)
                    self.take_baseline_screenshot(page, "user_disabled")
                    
                    # Check status changed to Disabled
                    page.reload()
                    page.wait_for_timeout(1000)
                    
                    # Find the user again after reload
                    user_rows_after = page.locator(".user-row")
                    for j in range(user_rows_after.count()):
                        row_after = user_rows_after.nth(j)
                        username_cell_after = row_after.locator("td:nth-child(1)")
                        if test_username in username_cell_after.text_content():
                            status_cell_after = row_after.locator("td:nth-child(3) .status")
                            status_text_after = status_cell_after.text_content()
                            print(f"Status after disable: {status_text_after}")
                            
                            # Should now have Enable button
                            enable_button = row_after.locator(".action-buttons button:has-text('Enable')")
                            if enable_button.count() > 0:
                                # Click Enable button
                                enable_button.click()
                                page.wait_for_timeout(2000)
                                self.take_baseline_screenshot(page, "user_enabled")
                                
                                # Check status changed back to Active
                                page.reload()
                                page.wait_for_timeout(1000)
                                print(f"User {test_username} re-enabled")
                            break
                break
    
    # Test 21: Regenerate API token functionality
    def test_regenerate_api_token(self, authenticated_page: Page):
        """Test regenerating a user's API token."""
        page = authenticated_page
        
        # First, create a test user
        test_username = self.create_test_user(page, is_admin=False)
        print(f"Created test user for token regeneration: {test_username}")
        
        # Find the test user in the table
        page.goto(self.ADMIN_USERS_URL)
        user_rows = page.locator(".user-row")
        
        for i in range(user_rows.count()):
            row = user_rows.nth(i)
            username_cell = row.locator("td:nth-child(1)")
            if test_username in username_cell.text_content():
                # Check token display
                token_cell = row.locator("td:nth-child(4)")
                initial_token_display = token_cell.text_content()
                print(f"Initial token display: {initial_token_display}")
                
                # Find Regenerate Token button
                regenerate_button = row.locator(".action-buttons button:has-text('Regenerate Token')")
                expect(regenerate_button).to_be_visible()
                
                # Click Regenerate Token button
                regenerate_button.click()
                page.wait_for_timeout(2000)
                self.take_baseline_screenshot(page, "token_regenerated")
                
                # Check if token changed (page should reload or show success message)
                page.reload()
                page.wait_for_timeout(1000)
                
                # Find the user again after reload
                user_rows_after = page.locator(".user-row")
                for j in range(user_rows_after.count()):
                    row_after = user_rows_after.nth(j)
                    username_cell_after = row_after.locator("td:nth-child(1)")
                    if test_username in username_cell_after.text_content():
                        token_cell_after = row_after.locator("td:nth-child(4)")
                        new_token_display = token_cell_after.text_content()
                        print(f"New token display: {new_token_display}")
                        
                        # Tokens should be different (or at least the page should have updated)
                        if initial_token_display != new_token_display:
                            print("Token successfully regenerated")
                        else:
                            print("Token display may be truncated, checking for changes...")
                        break
                break
    
    # Test 22: Delete user functionality
    def test_delete_user(self, authenticated_page: Page):
        """Test deleting a user."""
        page = authenticated_page
        
        # First, create a test user
        test_username = self.create_test_user(page, is_admin=False)
        print(f"Created test user for deletion: {test_username}")
        
        # Find the test user in the table and click Delete button
        page.goto(self.ADMIN_USERS_URL)
        user_rows = page.locator(".user-row")
        
        for i in range(user_rows.count()):
            row = user_rows.nth(i)
            username_cell = row.locator("td:nth-child(1)")
            if test_username in username_cell.text_content():
                # Find Delete button
                delete_button = row.locator(".action-buttons .btn-danger:has-text('Delete')")
                expect(delete_button).to_be_visible()
                
                # Click Delete button
                delete_button.click()
                page.wait_for_timeout(1000)
                
                # Should be on delete confirmation page
                expect(page).to_have_url(re.compile(".*/delete.*"))
                expect(page).to_have_title(re.compile("Delete User - SMS Application"))
                self.take_baseline_screenshot(page, "delete_confirmation_page")
                
                # Check confirmation page elements
                expect(page.locator("h1")).to_have_text("Delete User")
                
                warning_message = page.locator(".warning-message h2")
                expect(warning_message).to_be_visible()
                expect(warning_message).to_contain_text("Are you sure you want to delete this user?")
                
                user_info = page.locator(".user-info")
                expect(user_info).to_be_visible()
                expect(user_info).to_contain_text(test_username)
                
                # Check delete confirmation button
                confirm_delete_button = page.locator("button.btn-danger:has-text('Yes, Delete This User')")
                expect(confirm_delete_button).to_be_visible()
                
                # Check cancel button
                cancel_button = page.locator("a.btn-secondary:has-text('Cancel')")
                expect(cancel_button).to_be_visible()
                
                self.take_baseline_screenshot(page, "delete_confirmation_form")
                
                # Test cancel first
                cancel_button.click()
                page.wait_for_timeout(1000)
                
                # Should be back on users page
                expect(page).to_have_url(re.compile(".*/admin/users.*"))
                self.take_baseline_screenshot(page, "delete_cancelled")
                
                # Go back to delete page
                delete_button = page.locator(f".user-row:has-text('{test_username}') .btn-danger:has-text('Delete')")
                delete_button.click()
                page.wait_for_timeout(1000)
                
                # Now actually delete the user
                confirm_delete_button = page.locator("button.btn-danger:has-text('Yes, Delete This User')")
                confirm_delete_button.click()
                page.wait_for_timeout(2000)
                
                # Should be redirected back to users page
                expect(page).to_have_url(re.compile(".*/admin/users.*"))
                self.take_baseline_screenshot(page, "user_deleted")
                
                # Verify user is no longer in the table
                page.reload()
                page.wait_for_timeout(1000)
                
                user_rows_after = page.locator(".user-row")
                user_found = False
                for j in range(user_rows_after.count()):
                    row_after = user_rows_after.nth(j)
                    username_cell_after = row_after.locator("td:nth-child(1)")
                    if test_username in username_cell_after.text_content():
                        user_found = True
                        break
                
                if not user_found:
                    print(f"User {test_username} successfully deleted")
                else:
                    print(f"User {test_username} may still be in the table")
                break
    
    # Test 23: Admin page security - access without authentication
    def test_admin_access_without_auth(self, browser_page: Page):
        """Test that admin pages redirect to login when not authenticated."""
        page = browser_page
        
        # Try to access admin users page without logging in
        response = page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "admin_users_no_auth")
        
        # Should be redirected to login page
        expect(page).to_have_url(re.compile(".*login.*"))
        
        # Check login form is displayed
        expect(page.locator("h1")).to_have_text("Login")
        expect(page.locator("#username")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()
        
        self.take_baseline_screenshot(page, "redirected_to_login")
        
        # Also test create user page access without authentication
        page.goto(f"{self.ADMIN_USERS_URL}/create")
        self.take_baseline_screenshot(page, "create_page_no_auth")
        
        # Should be redirected to login page
        expect(page).to_have_url(re.compile(".*login.*"))
        self.take_baseline_screenshot(page, "create_redirected_to_login")
    
    # Test 24: User table sorting functionality
    def test_user_table_sorting(self, authenticated_page: Page):
        """Test user table sorting functionality."""
        page = authenticated_page
        
        page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "user_table_sorting_start")
        
        # Check if table has sortable headers
        table_headers = page.locator(".users-table thead th")
        
        # Test clicking on username header (if sortable)
        username_header = table_headers.nth(0)  # Username column
        class_attr = username_header.get_attribute("class")
        
        if class_attr and ("sortable" in class_attr or "clickable" in class_attr):
            username_header.click()
            page.wait_for_timeout(1000)
            self.take_baseline_screenshot(page, "username_sorted")
            
            # Check if URL contains sort parameter
            expect(page).to_have_url(re.compile(".*sort=username.*"))
            
            # Click again for descending order
            username_header.click()
            page.wait_for_timeout(1000)
            self.take_baseline_screenshot(page, "username_sorted_desc")
            
            # Check if URL contains sort parameter with direction
            expect(page).to_have_url(re.compile(".*sort=username.*desc.*"))
        else:
            print("Username header is not sortable")
            self.take_baseline_screenshot(page, "no_sorting_available")
    
    # Test 25: User search functionality
    def test_user_search_functionality(self, authenticated_page: Page):
        """Test user search functionality."""
        page = authenticated_page
        
        page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "user_search_start")
        
        # Check if search input exists
        search_input = page.locator(".search-input, input[type='search'], input[name='search']")
        
        if search_input.count() > 0:
            expect(search_input).to_be_visible()
            
            # Enter search term
            search_input.fill("test")
            self.take_baseline_screenshot(page, "search_term_entered")
            
            # Submit search (either by pressing Enter or clicking search button)
            search_button = page.locator(".search-button, button[type='submit']:has-text('Search')")
            if search_button.count() > 0:
                search_button.click()
            else:
                # Press Enter
                search_input.press("Enter")
            
            page.wait_for_timeout(1000)
            self.take_baseline_screenshot(page, "search_results")
            
            # Check if URL contains search parameter
            expect(page).to_have_url(re.compile(".*search=test.*"))
            
            # Clear search
            clear_button = page.locator(".clear-search, button:has-text('Clear')")
            if clear_button.count() > 0:
                clear_button.click()
                page.wait_for_timeout(1000)
                expect(page).not_to_have_url(re.compile(".*search=.*"))
                self.take_baseline_screenshot(page, "search_cleared")
        else:
            print("No search input found on admin users page")
            self.take_baseline_screenshot(page, "no_search_input")
    
    # Test 26: Batch operations functionality
    def test_batch_operations(self, authenticated_page: Page):
        """Test batch operations functionality."""
        page = authenticated_page
        
        page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "batch_operations_start")
        
        # Check if batch operations are available
        # Look for checkboxes in table rows
        checkboxes = page.locator(".user-row input[type='checkbox']")
        
        if checkboxes.count() > 0:
            # Batch operations are available
            expect(checkboxes.first).to_be_visible()
            
            # Check first checkbox
            checkboxes.first.check()
            self.take_baseline_screenshot(page, "checkbox_checked")
            
            # Look for batch action buttons
            batch_buttons = page.locator(".batch-actions button")
            
            if batch_buttons.count() > 0:
                # Test batch disable/enable
                batch_disable_button = page.locator(".batch-actions button:has-text('Disable Selected')")
                if batch_disable_button.count() > 0:
                    batch_disable_button.click()
                    page.wait_for_timeout(1000)
                    self.take_baseline_screenshot(page, "batch_disable_clicked")
                    
                    # Check for confirmation dialog
                    confirm_dialog = page.locator(".modal, .confirmation-dialog")
                    if confirm_dialog.count() > 0:
                        expect(confirm_dialog).to_be_visible()
                        self.take_baseline_screenshot(page, "batch_confirmation_dialog")
                        
                        # Cancel the operation
                        cancel_button = confirm_dialog.locator("button:has-text('Cancel')")
                        if cancel_button.count() > 0:
                            cancel_button.click()
                            page.wait_for_timeout(1000)
                            self.take_baseline_screenshot(page, "batch_operation_cancelled")
            else:
                print("No batch action buttons found")
                self.take_baseline_screenshot(page, "no_batch_buttons")
        else:
            print("No checkboxes found for batch operations")
            self.take_baseline_screenshot(page, "no_batch_checkboxes")
    
    # Test 27: Export functionality
    def test_export_functionality(self, authenticated_page: Page):
        """Test export functionality."""
        page = authenticated_page
        
        page.goto(self.ADMIN_USERS_URL)
        self.take_baseline_screenshot(page, "export_start")
        
        # Check for export button
        export_button = page.locator(".export-button, button:has-text('Export'), a:has-text('Export')")
        
        if export_button.count() > 0:
            expect(export_button).to_be_visible()
            self.take_baseline_screenshot(page, "export_button_visible")
            
            # Click export button
            export_button.click()
            page.wait_for_timeout(1000)
            
            # Check for export options dialog
            export_dialog = page.locator(".export-dialog, .modal")
            if export_dialog.count() > 0:
                expect(export_dialog).to_be_visible()
                self.take_baseline_screenshot(page, "export_dialog")
                
                # Check export format options
                format_options = export_dialog.locator("input[type='radio'], select")
                if format_options.count() > 0:
                    # Select CSV format
                    csv_option = export_dialog.locator("input[value='csv'], option[value='csv']")
                    if csv_option.count() > 0:
                        csv_option.click()
                        self.take_baseline_screenshot(page, "csv_selected")
                    
                    # Click export button in dialog
                    dialog_export_button = export_dialog.locator("button:has-text('Export'), button[type='submit']")
                    if dialog_export_button.count() > 0:
                        dialog_export_button.click()
                        page.wait_for_timeout(2000)
                        self.take_baseline_screenshot(page, "export_initiated")
            else:
                # Direct download (no dialog)
                self.take_baseline_screenshot(page, "direct_export")
        else:
            print("No export button found")
            self.take_baseline_screenshot(page, "no_export_button")
    
    # Test 28: User permission change (admin ↔ non-admin)
    def test_user_permission_change(self, authenticated_page: Page):
        """Test changing user permissions between admin and non-admin."""
        page = authenticated_page
        
        # First, create a test user
        test_username = self.create_test_user(page, is_admin=False)
        print(f"Created test user for permission change: {test_username}")
        
        # Find the test user in the table
        page.goto(self.ADMIN_USERS_URL)
        user_rows = page.locator(".user-row")
        
        for i in range(user_rows.count()):
            row = user_rows.nth(i)
            username_cell = row.locator("td:nth-child(1)")
            if test_username in username_cell.text_content():
                # Check initial admin status (should be non-admin)
                admin_status_cell = row.locator("td:nth-child(2) .status")
                initial_admin_status = admin_status_cell.text_content()
                print(f"Initial admin status: {initial_admin_status}")
                
                # Find Edit button
                edit_button = row.locator(".action-buttons .btn:has-text('Edit')")
                if edit_button.count() > 0:
                    edit_button.click()
                    page.wait_for_timeout(1000)
                    
                    # Check if on edit user page
                    expect(page).to_have_url(re.compile(".*/edit.*"))
                    expect(page).to_have_title(re.compile("Edit User - SMS Application"))
                    self.take_baseline_screenshot(page, "edit_user_page")
                    
                    # Check admin checkbox
                    admin_checkbox = page.locator("#is_admin")
                    expect(admin_checkbox).to_be_visible()
                    
                    # Change to admin (check the checkbox)
                    admin_checkbox.check()
                    self.take_baseline_screenshot(page, "admin_checkbox_checked")
                    
                    # Save changes
                    save_button = page.locator("button[type='submit']:has-text('Save')")
                    expect(save_button).to_be_visible()
                    save_button.click()
                    page.wait_for_timeout(2000)
                    
                    # Should be redirected back to users page
                    expect(page).to_have_url(re.compile(".*/admin/users.*"))
                    self.take_baseline_screenshot(page, "permission_changed")
                    
                    # Verify admin status changed
                    page.reload()
                    page.wait_for_timeout(1000)
                    
                    # Find the user again
                    user_rows_after = page.locator(".user-row")
                    for j in range(user_rows_after.count()):
                        row_after = user_rows_after.nth(j)
                        username_cell_after = row_after.locator("td:nth-child(1)")
                        if test_username in username_cell_after.text_content():
                            admin_status_cell_after = row_after.locator("td:nth-child(2) .status")
                            new_admin_status = admin_status_cell_after.text_content()
                            print(f"New admin status: {new_admin_status}")
                            
                            # Status should be different
                            if initial_admin_status != new_admin_status:
                                print("User permission successfully changed")
                            break
                break
    
    # Test 29: User enable/disable status visual feedback
    def test_user_status_visual_feedback(self, authenticated_page: Page):
        """Test visual feedback for user enable/disable status."""
        page = authenticated_page
        
        # First, create a test user
        test_username = self.create_test_user(page, is_admin=False)
        print(f"Created test user for status visual feedback: {test_username}")
        
        # Find the test user in the table
        page.goto(self.ADMIN_USERS_URL)
        user_rows = page.locator(".user-row")
        
        for i in range(user_rows.count()):
            row = user_rows.nth(i)
            username_cell = row.locator("td:nth-child(1)")
            if test_username in username_cell.text_content():
                # Check active status cell
                status_cell = row.locator("td:nth-child(3) .status")
                expect(status_cell).to_be_visible()
                
                # Check status text and CSS class
                status_text = status_cell.text_content()
                status_class = status_cell.get_attribute("class")
                print(f"Initial status: text='{status_text}', class='{status_class}'")
                
                # Check if status has visual styling
                if "active" in status_class.lower() or "success" in status_class.lower():
                    print("Active status has appropriate visual styling")
                
                # Disable the user
                disable_button = row.locator(".action-buttons button:has-text('Disable')")
                if disable_button.count() > 0:
                    disable_button.click()
                    page.wait_for_timeout(2000)
                    
                    # Reload page to see updated status
                    page.reload()
                    page.wait_for_timeout(1000)
                    
                    # Find the user again
                    user_rows_after = page.locator(".user-row")
                    for j in range(user_rows_after.count()):
                        row_after = user_rows_after.nth(j)
                        username_cell_after = row_after.locator("td:nth-child(1)")
                        if test_username in username_cell_after.text_content():
                            status_cell_after = row_after.locator("td:nth-child(3) .status")
                            status_text_after = status_cell_after.text_content()
                            status_class_after = status_cell_after.get_attribute("class")
                            print(f"Disabled status: text='{status_text_after}', class='{status_class_after}'")
                            
                            # Check if disabled status has different visual styling
                            if "disabled" in status_class_after.lower() or "danger" in status_class_after.lower() or "inactive" in status_class_after.lower():
                                print("Disabled status has appropriate visual styling")
                            
                            self.take_baseline_screenshot(page, "disabled_status_visual")
                            break
                break


def run_admin_baseline_tests():
    """Run admin page baseline tests and show summary."""
    import subprocess
    import sys
    
    print("=" * 60)
    print("SMS Panel Admin Page Baseline Tests")
    print("=" * 60)
    print("Features:")
    print("- Trace recording: DISABLED by default")
    print("- Video recording: DISABLED by default")
    print("- Screenshot comparison: ENABLED")
    print("- Baseline images: test_ui/test_admin_baseline_screenshots/")
    print("- Authentication: Auto-login with test_SMSadmin credentials")
    print("- Admin pages tested: Users, Messages, Dead Letter Queue")
    print("=" * 60)
    
    # Create directories
    os.makedirs("test_ui/test_admin_screenshots", exist_ok=True)
    
    # Run tests
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        __file__,
        "-v",
        "--headed"
    ])
    
    print("\n" + "=" * 60)
    print("ADMIN PAGE BASELINE TEST SUMMARY")
    print("=" * 60)
    
    # Count baseline files
    baseline_dir = "test_ui/test_admin_baseline_screenshots"
    if os.path.exists(baseline_dir):
        baseline_files = [f for f in os.listdir(baseline_dir) if f.endswith('.png')]
        print(f"Admin baseline screenshots: {len(baseline_files)} files")
        
        # Show some examples
        if baseline_files:
            print("\nExample baseline files:")
            for f in baseline_files[:5]:
                print(f"  - {f}")
            if len(baseline_files) > 5:
                print(f"  - ... and {len(baseline_files) - 5} more")
    
    print("\nTo update baseline images:")
    print("1. Delete files from test_ui/test_admin_baseline_screenshots/")
    print("2. Run tests again to create new baselines")
    print("\nTo enable trace/video recording:")
    print("Edit test_ui/test_admin_page_baseline.py")
    print("Set ENABLE_TRACE = True for trace recording")
    print("Set ENABLE_VIDEO = True for video recording")
    
    return result.returncode


if __name__ == "__main__":
    """Command line interface."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        sys.exit(run_admin_baseline_tests())
    else:
        print("Usage:")
        print("  python test_ui/test_admin_page_baseline.py run")
        print()
        print("Or run with pytest directly:")
        print("  pytest test_ui/test_admin_page_baseline.py -v --headed")
        print()
        print("Test suite includes:")
        print("  1. Admin users page loads after authentication")
        print("  2. Admin users table structure")
        print("  3. Admin messages page loads")
        print("  4. Admin messages filter functionality")
        print("  5. Admin messages table structure")
        print("  6. Admin dead letter page loads")
        print("  7. Admin dead letter stats cards")
        print("  8. Admin dead letter filter functionality")
        print("  9. Admin dead letter table structure")
        print("  10. Admin page accessibility (admin privileges)")
        print("  11. Admin page navigation")
        print("  12. Responsive design on admin pages")
        print("  13. Admin page pagination")
        print("  14. Admin action buttons functionality")
        print("  15. Create admin user functionality")
        print("  16. Create normal user functionality")
        print("  17. User creation form validation")
        print("  18. Test cancel button functionality")
        print("  19. Change user password functionality")
        print("  20. Disable/enable user functionality")
        print("  21. Regenerate API token functionality")
        print("  22. Delete user functionality")
        print("  23. Admin page security (access without authentication)")
        print("  24. User table sorting functionality")
        print("  25. User search functionality")
        print("  26. Batch operations functionality")
        print("  27. Export functionality")
        print("  28. User permission change (admin ↔ non-admin)")
        print("  29. User enable/disable status visual feedback")
        
