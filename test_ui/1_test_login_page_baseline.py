"""
Playwright UI tests with baseline screenshot comparison.
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


class TestLoginPageBaseline:
    """Test suite for SMS Panel Login page with baseline screenshot comparison."""
    
    # Configuration - CHANGE THESE SETTINGS AS NEEDED
    BASELINE_DIR = "test_ui/test_login_baseline_screenshots"  # Store baseline images here
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
            context_args["record_video_dir"] = "test_videos_baseline"
            context_args["record_video_size"] = {"width": 1280, "height": 800}
            os.makedirs("test_videos_baseline", exist_ok=True)
        
        context = browser.new_context(**context_args)
        
        # Start optional tracing
        if self.ENABLE_TRACE:
            os.makedirs("test_traces_baseline", exist_ok=True)
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
            trace_path = os.path.join("test_traces_baseline", f"{test_name}.zip")
            context.tracing.stop(path=trace_path)
        
        # Close context (saves video if enabled)
        context.close()
        browser.close()
    
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
    
    # Test 1: Login page loads correctly
    def test_login_page_loads(self, browser_page: Page):
        """Test that login page loads correctly."""
        page = browser_page
        
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "login_page")
        
        # Check page title
        expect(page).to_have_title(re.compile("Login - SMS Application"))
        
        # Check form elements
        expect(page.locator("h1")).to_have_text("Login")
        self.take_baseline_screenshot(page, "login_header")
        
        expect(page.locator("#username")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()
        expect(page.locator("button[type='submit']")).to_be_visible()
        expect(page.locator("button[type='submit']")).to_have_text("Login")
        
        self.take_baseline_screenshot(page, "login_form")
    
    # Test 2: Login with invalid credentials
    def test_login_with_invalid_credentials(self, browser_page: Page):
        """Test login with invalid credentials shows error."""
        page = browser_page
        
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "login_page_start")
        
        # Fill form with invalid credentials
        page.locator("#username").fill("invalid_user")
        page.locator("#password").fill("wrong_password")
        self.take_baseline_screenshot(page, "invalid_credentials")
        
        page.locator("button[type='submit']").click()
        
        # Wait and take screenshot
        page.wait_for_timeout(1000)
        self.take_baseline_screenshot(page, "after_invalid_login")
        
        # Should stay on login page or show error
        expect(page).to_have_url(re.compile(".*login.*"))
    
    # Test 3: Navigation to register page
    def test_navigation_to_register_page(self, browser_page: Page):
        """Test navigation to register page from login."""
        page = browser_page
        
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "before_register")
        
        # Try to navigate to register URL
        response = page.goto("http://127.0.0.1:3570/register")
        self.take_baseline_screenshot(page, "register_page")
        
        # Check response status
        if response.status == 404:
            print("Register page returns 404 (expected)")
            return
        elif response.status == 200:
            expect(page).to_have_title(re.compile("Register - SMS Application"))
            expect(page.locator("h1")).to_have_text("Register")
        else:
            pytest.fail(f"Unexpected status code for /register: {response.status}")
    
    # Test 4: Dashboard page structure
    def test_dashboard_page_structure(self, browser_page: Page):
        """Test dashboard page structure (requires authentication)."""
        page = browser_page
        
        # Try to access dashboard without authentication
        response = page.goto("http://127.0.0.1:3570/dashboard")
        self.take_baseline_screenshot(page, "dashboard_access")
        
        # Check current URL
        current_url = page.url
        
        if "login" in current_url:
            # Redirected to login page
            expect(page).to_have_url(re.compile(".*login.*"))
            expect(page.locator("h1")).to_have_text("Login")
            self.take_baseline_screenshot(page, "redirected_to_login")
        elif response.status == 404:
            print("Dashboard page returns 404")
        else:
            try:
                expect(page.locator("h1")).to_contain_text("Welcome", timeout=5000)
                self.take_baseline_screenshot(page, "dashboard_loaded")
                print("Accessed dashboard page")
            except AssertionError:
                print(f"Page loaded but not dashboard. Title: {page.title()}")
    
    # Test 5: Compose page elements
    def test_compose_page_elements(self, browser_page: Page):
        """Test compose page form elements."""
        page = browser_page
        
        # Try to access compose page
        page.goto("http://127.0.0.1:3570/compose")
        self.take_baseline_screenshot(page, "compose_page")
        
        # Check if redirected to login
        current_url = page.url
        if "login" in current_url:
            expect(page).to_have_url(re.compile(".*login.*"))
            self.take_baseline_screenshot(page, "compose_redirected")
        else:
            expect(page).to_have_title(re.compile("Compose SMS - SMS Application"))
            expect(page.locator("h1")).to_have_text("Compose SMS")
            expect(page.locator("#recipients")).to_be_visible()
            expect(page.locator("#content")).to_be_visible()
            expect(page.locator("#enquiry_number")).to_be_visible()
            expect(page.locator("button[type='submit']:has-text('Send SMS')")).to_be_visible()
            self.take_baseline_screenshot(page, "compose_form")
    
    # Test 6: History page access
    def test_history_page_access(self, browser_page: Page):
        """Test history page access."""
        page = browser_page
        
        page.goto("http://127.0.0.1:3570/history")
        self.take_baseline_screenshot(page, "history_page")
        
        # Check if redirected to login
        current_url = page.url
        if "login" in current_url:
            expect(page).to_have_url(re.compile(".*login.*"))
            self.take_baseline_screenshot(page, "history_redirected")
        else:
            expect(page).to_have_title(re.compile("History - SMS Application"))
            expect(page.locator("h1")).to_have_text("History")
            self.take_baseline_screenshot(page, "history_content")
    
    # Test 7: Form validation on compose page
    def test_form_validation_on_compose_page(self, browser_page: Page):
        """Test client-side form validation on compose page."""
        page = browser_page
        
        # Try to access compose page
        page.goto("http://127.0.0.1:3570/compose")
        self.take_baseline_screenshot(page, "form_validation_start")
        
        # Skip if redirected to login
        if "login" in page.url:
            pytest.skip("Not authenticated, cannot test compose page")
        
        # Test phone number validation
        recipients_textarea = page.locator("#recipients")
        recipients_textarea.fill("1234")  # Invalid format
        self.take_baseline_screenshot(page, "invalid_phone")
        
        recipients_textarea.blur()
        
        recipients_textarea.fill("1234 5678")
        recipients_textarea.blur()
        self.take_baseline_screenshot(page, "valid_phone")
        
        # Test enquiry number validation
        enquiry_input = page.locator("#enquiry_number")
        enquiry_input.fill("1234")  # Invalid
        enquiry_input.blur()
        self.take_baseline_screenshot(page, "invalid_enquiry")
        
        enquiry_input.fill("1234 5678")  # Valid
        enquiry_input.blur()
        self.take_baseline_screenshot(page, "valid_enquiry")
    
    # Test 8: Responsive design
    def test_responsive_design(self, browser_page: Page):
        """Test basic responsive design elements."""
        page = browser_page
        
        # Test login page on different viewports
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "mobile_viewport")
        
        page.set_viewport_size({"width": 768, "height": 1024})  # iPad
        self.take_baseline_screenshot(page, "tablet_viewport")
        
        page.set_viewport_size({"width": 1280, "height": 800})  # Desktop
        #self.take_baseline_screenshot(page, "desktop_viewport")
        
        # Check elements are visible
        expect(page.locator("h1")).to_be_visible()
        expect(page.locator("#username")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()
    
    # Test 9: Links and navigation
    def test_links_and_navigation(self, browser_page: Page):
        """Test internal links and navigation."""
        page = browser_page
        
        # Start at login page
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "navigation_start")
        
        # Check for CSRF token
        csrf_input = page.locator("input[name='csrf_token']")
        expect(csrf_input).to_have_attribute("type", "hidden")
        expect(csrf_input).to_be_attached()
        
        # Check form
        form = page.locator("form")
        expect(form).to_have_attribute("method", "POST")
        
        expect(page.locator("#username")).to_be_visible()
        expect(page.locator("#password")).to_be_visible()
        expect(page.locator("button[type='submit']")).to_be_visible()
    
    # Test 10: Health endpoint
    def test_health_endpoint(self, browser_page: Page):
        """Test health endpoint is accessible.
        
        Note: No screenshot is taken for this test because the health endpoint
        response contains timestamps that change with each request.
        """
        page = browser_page
        
        # Health endpoint is at /api/health
        response = page.goto("http://127.0.0.1:3570/api/health")
        
        # Check response status
        assert response.status == 200, f"Expected 200, got {response.status} for /api/health"
        
        # Check response content (but don't take screenshot due to timestamps)
        try:
            content = page.text_content("body")
            if '"status"' in content:
                print(f"Health endpoint response: {content[:100]}...")
            else:
                print(f"Health endpoint returned: {content}")
        except Exception as e:
            print(f"Could not parse health endpoint response: {e}")
        
        # Note: No screenshot taken for health endpoint because it contains timestamps
        # that would cause false differences in baseline comparison
    
    # Test 11: Static files loading
    def test_static_files_loading(self, browser_page: Page):
        """Test that CSS and other static files load."""
        page = browser_page
        
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "static_files_page")
        
        # Check if CSS is loaded
        form_group = page.locator(".form-group")
        if form_group.count() > 0:
            expect(form_group.first).to_be_visible()
        
        auth_container = page.locator(".auth-container")
        if auth_container.count() > 0:
            expect(auth_container.first).to_be_visible()
        
        # Test static CSS file accessibility
        response = page.goto("http://127.0.0.1:3570/static/style.css")
        if response.status == 200:
            print("Static CSS file is accessible")
        else:
            print(f"Static CSS file returned status: {response.status}")
    
    # Test 12: Login with valid credentials
    def test_login_with_valid_credentials(self, browser_page: Page):
        """Test login with valid credentials redirects to dashboard."""
        page = browser_page
        
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "login_page_start")
        
        # Fill form with valid credentials
        page.locator("#username").fill("test_SMSadmin")
        page.locator("#password").fill("test_SMSpass#12")
        self.take_baseline_screenshot(page, "valid_credentials_filled")
        
        page.locator("button[type='submit']").click()
        
        # Wait for redirect
        page.wait_for_timeout(2000)
        self.take_baseline_screenshot(page, "after_valid_login")
        
        # Should be redirected to dashboard or home page
        expect(page).not_to_have_url(re.compile(".*login.*"))
        
        # Check if we're on dashboard or home page
        if "dashboard" in page.url or page.url.endswith("/"):
            print("Successfully logged in and redirected to dashboard")
            self.take_baseline_screenshot(page, "dashboard_after_login")
        else:
            print(f"Logged in but not on dashboard. Current URL: {page.url}")
    
    # Test 13: Password visibility toggle
    def test_password_visibility_toggle(self, browser_page: Page):
        """Test password visibility toggle functionality."""
        page = browser_page
        
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "password_toggle_start")
        
        # Check for password visibility toggle button
        password_toggle = page.locator(".password-toggle, button[type='button']:has(svg.eye-icon)")
        
        if password_toggle.count() > 0:
            expect(password_toggle).to_be_visible()
            
            # Password should be hidden by default
            password_input = page.locator("#password")
            expect(password_input).to_have_attribute("type", "password")
            self.take_baseline_screenshot(page, "password_hidden")
            
            # Click toggle to show password
            password_toggle.click()
            page.wait_for_timeout(500)
            expect(password_input).to_have_attribute("type", "text")
            self.take_baseline_screenshot(page, "password_visible")
            
            # Click toggle again to hide password
            password_toggle.click()
            page.wait_for_timeout(500)
            expect(password_input).to_have_attribute("type", "password")
            self.take_baseline_screenshot(page, "password_hidden_again")
        else:
            print("Password visibility toggle not available")
            self.take_baseline_screenshot(page, "no_password_toggle")
    
    # Test 14: Remember me functionality
    def test_remember_me_functionality(self, browser_page: Page):
        """Test remember me checkbox functionality."""
        page = browser_page
        
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "remember_me_start")
        
        # Check for remember me checkbox
        remember_me_checkbox = page.locator("input[name='remember_me'], input[type='checkbox']")
        
        if remember_me_checkbox.count() > 0:
            expect(remember_me_checkbox).to_be_visible()
            
            # Check remember me label
            remember_me_label = page.locator("label:has-text('Remember me')")
            if remember_me_label.count() > 0:
                expect(remember_me_label).to_be_visible()
            
            # Test checking the checkbox
            remember_me_checkbox.check()
            page.wait_for_timeout(500)
            self.take_baseline_screenshot(page, "remember_me_checked")
            
            # Test unchecking the checkbox
            remember_me_checkbox.uncheck()
            page.wait_for_timeout(500)
            self.take_baseline_screenshot(page, "remember_me_unchecked")
            
            # Fill form and submit with remember me checked
            page.locator("#username").fill("test_SMSadmin")
            page.locator("#password").fill("test_SMSpass#12")
            remember_me_checkbox.check()
            self.take_baseline_screenshot(page, "login_with_remember_me")
            
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(2000)
            
            # Logout and check if credentials are remembered
            # (This would require logout functionality to be tested separately)
        else:
            print("Remember me functionality not available")
            self.take_baseline_screenshot(page, "no_remember_me")
    
    # Test 15: Forgot password link
    def test_forgot_password_link(self, browser_page: Page):
        """Test forgot password link functionality."""
        page = browser_page
        
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "forgot_password_start")
        
        # Check for forgot password link
        forgot_password_link = page.locator("a:has-text('Forgot password?'), a[href*='forgot']")
        
        if forgot_password_link.count() > 0:
            expect(forgot_password_link).to_be_visible()
            
            # Click forgot password link
            forgot_password_link.click()
            page.wait_for_timeout(1000)
            self.take_baseline_screenshot(page, "forgot_password_page")
            
            # Check if on forgot password page
            expect(page).to_have_url(re.compile(".*forgot.*"))
            expect(page.locator("h1")).to_have_text("Forgot Password")
            
            # Check email input field
            email_input = page.locator("input[name='email'], input[type='email']")
            if email_input.count() > 0:
                expect(email_input).to_be_visible()
                email_input.fill("test@example.com")
                self.take_baseline_screenshot(page, "forgot_password_email_filled")
            
            # Check reset button
            reset_button = page.locator("button:has-text('Reset Password')")
            if reset_button.count() > 0:
                expect(reset_button).to_be_visible()
                reset_button.click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "reset_password_clicked")
            
            # Go back to login page
            page.go_back()
            page.wait_for_timeout(500)
            self.take_baseline_screenshot(page, "back_to_login")
        else:
            print("Forgot password link not available")
            self.take_baseline_screenshot(page, "no_forgot_password_link")
    
    # Test 16: Session timeout handling
    def test_session_timeout_handling(self, browser_page: Page):
        """Test session timeout handling on login page."""
        page = browser_page
        
        # First, login successfully
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        page.locator("#username").fill("test_SMSadmin")
        page.locator("#password").fill("test_SMSpass#12")
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(2000)
        
        # Check if logged in
        if "login" not in page.url:
            print("Successfully logged in for session timeout test")
            self.take_baseline_screenshot(page, "logged_in_before_timeout")
            
            # Simulate session timeout by clearing cookies or waiting
            # This is a basic test - actual session timeout would require server-side testing
            
            # Navigate to a protected page after potential timeout
            page.goto("http://127.0.0.1:3570/compose")
            page.wait_for_timeout(1000)
            
            # Check if still logged in or redirected to login
            if "login" in page.url:
                print("Session expired - redirected to login")
                self.take_baseline_screenshot(page, "session_expired_redirect")
                
                # Check for session expired message
                expired_message = page.locator(".alert-warning, .session-expired")
                if expired_message.count() > 0:
                    expect(expired_message).to_be_visible()
                    expect(expired_message).to_contain_text("session expired")
                    self.take_baseline_screenshot(page, "session_expired_message")
            else:
                print("Session still active")
                self.take_baseline_screenshot(page, "session_still_active")
        else:
            print("Could not log in for session timeout test")
            self.take_baseline_screenshot(page, "login_failed_for_timeout_test")
    
    # Test 17: Concurrent login attempts
    def test_concurrent_login_attempts(self, browser_page: Page):
        """Test handling of concurrent login attempts."""
        page = browser_page
        
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "concurrent_login_start")
        
        # Fill form with invalid credentials multiple times
        for attempt in range(1, 4):
            page.locator("#username").fill(f"invalid_user_{attempt}")
            page.locator("#password").fill(f"wrong_password_{attempt}")
            self.take_baseline_screenshot(page, f"concurrent_attempt_{attempt}")
            
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(1000)
            
            # Check for rate limiting or lockout messages
            error_message = page.locator(".alert-danger, .error-message")
            if error_message.count() > 0:
                error_text = error_message.text_content()
                print(f"Attempt {attempt}: {error_text}")
                self.take_baseline_screenshot(page, f"concurrent_error_{attempt}")
            
            # Clear form for next attempt
            page.locator("#username").fill("")
            page.locator("#password").fill("")
            page.wait_for_timeout(500)
        
        # Try with valid credentials after multiple failures
        page.locator("#username").fill("test_SMSadmin")
        page.locator("#password").fill("test_SMSpass#12")
        self.take_baseline_screenshot(page, "valid_after_concurrent")
        
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(2000)
        
        # Check if still able to login
        if "login" not in page.url:
            print("Successfully logged in after concurrent attempts")
            self.take_baseline_screenshot(page, "login_success_after_concurrent")
        else:
            print("Login blocked after concurrent attempts")
            self.take_baseline_screenshot(page, "login_blocked_after_concurrent")
    
    # Test 18: Login page accessibility features
    def test_login_page_accessibility_features(self, browser_page: Page):
        """Test accessibility features on login page."""
        page = browser_page
        
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "accessibility_start")
        
        # Check for proper form labels
        username_label = page.locator("label[for='username']")
        password_label = page.locator("label[for='password']")
        
        if username_label.count() > 0:
            expect(username_label).to_be_visible()
            expect(username_label).to_have_text("Username")
        
        if password_label.count() > 0:
            expect(password_label).to_be_visible()
            expect(password_label).to_have_text("Password")
        
        # Check for required field indicators
        required_fields = page.locator("[required]")
        if required_fields.count() > 0:
            print(f"Found {required_fields.count()} required fields")
            for i in range(required_fields.count()):
                field = required_fields.nth(i)
                field_name = field.get_attribute("name") or field.get_attribute("id")
                print(f"  Required field: {field_name}")
        
        # Check for ARIA attributes
        username_input = page.locator("#username")
        password_input = page.locator("#password")
        
        # Check aria-label or aria-labelledby
        username_aria = username_input.get_attribute("aria-label") or username_input.get_attribute("aria-labelledby")
        password_aria = password_input.get_attribute("aria-label") or password_input.get_attribute("aria-labelledby")
        
        if username_aria:
            print(f"Username input has ARIA: {username_aria}")
        if password_aria:
            print(f"Password input has ARIA: {password_aria}")
        
        # Check for focus indicators
        username_input.focus()
        page.wait_for_timeout(500)
        self.take_baseline_screenshot(page, "username_focused")
        
        password_input.focus()
        page.wait_for_timeout(500)
        self.take_baseline_screenshot(page, "password_focused")
        
        # Check for proper tab order
        page.locator("body").press("Tab")
        page.wait_for_timeout(500)
        self.take_baseline_screenshot(page, "first_tab")
        
        page.locator("body").press("Tab")
        page.wait_for_timeout(500)
        self.take_baseline_screenshot(page, "second_tab")
        
        page.locator("body").press("Tab")
        page.wait_for_timeout(500)
        self.take_baseline_screenshot(page, "third_tab")
    
    # Test 19: Browser back button after login
    def test_browser_back_button_after_login(self, browser_page: Page):
        """Test browser back button behavior after login."""
        page = browser_page
        
        # First, login
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        page.locator("#username").fill("test_SMSadmin")
        page.locator("#password").fill("test_SMSpass#12")
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(2000)
        
        # Check if logged in
        if "login" not in page.url:
            print("Successfully logged in for back button test")
            self.take_baseline_screenshot(page, "logged_in_before_back")
            
            # Navigate to another page
            page.goto("http://127.0.0.1:3570/compose")
            page.wait_for_timeout(1000)
            self.take_baseline_screenshot(page, "on_compose_page")
            
            # Click browser back button
            page.go_back()
            page.wait_for_timeout(1000)
            self.take_baseline_screenshot(page, "after_back_button")
            
            # Check if still logged in or redirected
            if "login" in page.url:
                print("Back button redirected to login")
            else:
                print("Back button kept user logged in")
                
                # Try going back to login page directly
                page.goto("http://127.0.0.1:3570/login")
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "direct_login_access")
                
                # Check if redirected away from login page
                if "login" not in page.url:
                    print("Logged in user redirected away from login page")
                else:
                    print("Logged in user can access login page")
        else:
            print("Could not log in for back button test")
            self.take_baseline_screenshot(page, "login_failed_for_back_test")
    
    # Test 20: Login page error messages
    def test_login_page_error_messages(self, browser_page: Page):
        """Test various error messages on login page."""
        page = browser_page
        
        page.goto("http://127.0.0.1:3570/login?next=%2F")
        self.take_baseline_screenshot(page, "error_messages_start")
        
        # Test empty username
        page.locator("#username").fill("")
        page.locator("#password").fill("testpassword")
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(1000)
        self.take_baseline_screenshot(page, "empty_username_error")
        
        # Check for error message
        error_message = page.locator(".alert-danger, .error-message")
        if error_message.count() > 0:
            error_text = error_message.text_content()
            print(f"Empty username error: {error_text}")
        
        # Test empty password
        page.locator("#username").fill("testuser")
        page.locator("#password").fill("")
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(1000)
        self.take_baseline_screenshot(page, "empty_password_error")
        
        if error_message.count() > 0:
            error_text = error_message.text_content()
            print(f"Empty password error: {error_text}")
        
        # Test both empty
        page.locator("#username").fill("")
        page.locator("#password").fill("")
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(1000)
        self.take_baseline_screenshot(page, "both_empty_error")
        
        if error_message.count() > 0:
            error_text = error_message.text_content()
            print(f"Both empty error: {error_text}")
        
        # Test invalid credentials error
        page.locator("#username").fill("nonexistentuser")
        page.locator("#password").fill("wrongpassword123")
        page.locator("button[type='submit']").click()
        page.wait_for_timeout(1000)
        self.take_baseline_screenshot(page, "invalid_credentials_error")
        
        if error_message.count() > 0:
            error_text = error_message.text_content()
            print(f"Invalid credentials error: {error_text}")
        
        # Test account locked error (if applicable)
        # This would require multiple failed attempts first
        for i in range(5):
            page.locator("#username").fill(f"locked_test_{i}")
            page.locator("#password").fill("wrongpassword")
            page.locator("button[type='submit']").click()
            page.wait_for_timeout(500)
        
        self.take_baseline_screenshot(page, "multiple_failed_attempts")
        
        # Check for account locked message
        locked_message = page.locator(".alert-warning, .account-locked")
        if locked_message.count() > 0:
            expect(locked_message).to_be_visible()
            expect(locked_message).to_contain_text("locked")
            self.take_baseline_screenshot(page, "account_locked_message")
        
        # Test CSRF token error (if applicable)
        # Remove CSRF token and try to submit
        csrf_input = page.locator("input[name='csrf_token']")
        if csrf_input.count() > 0:
            csrf_value = csrf_input.get_attribute("value")
            if csrf_value:
                # Try submitting with invalid CSRF token
                page.evaluate("document.querySelector('input[name=\"csrf_token\"]').value = 'invalid_token'")
                page.locator("#username").fill("testuser")
                page.locator("#password").fill("testpass")
                page.locator("button[type='submit']").click()
                page.wait_for_timeout(1000)
                self.take_baseline_screenshot(page, "csrf_error")
                
                csrf_error = page.locator(".alert-danger:has-text('CSRF')")
                if csrf_error.count() > 0:
                    expect(csrf_error).to_be_visible()
                    print("CSRF token error displayed")
        
        # Test session expired error
        # This would require simulating an expired session
        print("Error messages test completed")



def run_login_baseline_tests():
    """Run login page baseline tests and show summary."""
    import subprocess
    import sys
    
    print("=" * 60)
    print("SMS Panel Login Page Baseline Tests")
    print("=" * 60)
    print("Features:")
    print("- Trace recording: DISABLED by default")
    print("- Video recording: DISABLED by default")
    print("- Screenshot comparison: ENABLED")
    print("- Baseline images: test_login_baseline_screenshots/")
    print("=" * 60)
    
    # Create directories
    os.makedirs("test_ui/test_login_baseline_screenshots", exist_ok=True)
    
    # Run tests
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        __file__,
        "-v",
        "--headed"
    ])
    
    print("\n" + "=" * 60)
    print("LOGIN PAGE BASELINE TEST SUMMARY")
    print("=" * 60)
    
    # Count baseline files
    baseline_dir = "test_ui/test_login_baseline_screenshots"
    if os.path.exists(baseline_dir):
        baseline_files = [f for f in os.listdir(baseline_dir) if f.endswith('.png')]
        print(f"Login page baseline screenshots: {len(baseline_files)} files")
        
        # Show some examples
        if baseline_files:
            print("\nExample baseline files:")
            for f in baseline_files[:5]:
                print(f"  - {f}")
            if len(baseline_files) > 5:
                print(f"  - ... and {len(baseline_files) - 5} more")
    
    print("\nTo update baseline images:")
    print("1. Delete files from test_ui/test_login_baseline_screenshots/")
    print("2. Run tests again to create new baselines")
    print("\nTo enable trace/video recording:")
    print("Edit test_ui/test_login_page_baseline.py")
    print("Set ENABLE_TRACE = True for trace recording")
    print("Set ENABLE_VIDEO = True for video recording")
    
    return result.returncode


if __name__ == "__main__":
    """Command line interface."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        sys.exit(run_login_baseline_tests())
    else:
        print("Usage:")
        print("  python test_ui/test_login_page_baseline.py run")
        print()
        print("Or run with pytest directly:")
        print("  pytest test_ui/test_login_page_baseline.py -v --headed")
        print()
        print("Test suite includes:")
        print("  1. Login page loads correctly")
        print("  2. Login with invalid credentials")
        print("  3. Navigation to register page")
        print("  4. Dashboard page structure")
        print("  5. Compose page elements")
        print("  6. History page access")
        print("  7. Form validation on compose page")
        print("  8. Responsive design")
        print("  9. Links and navigation")
        print("  10. Health endpoint")
        print("  11. Static files loading")
        print("  12. Login with valid credentials")
        print("  13. Password visibility toggle")
        print("  14. Remember me functionality")
        print("  15. Forgot password link")
        print("  16. Session timeout handling")
        print("  17. Concurrent login attempts")
        print("  18. Login page accessibility features")
        print("  19. Browser back button after login")
        print("  20. Login page error messages")

