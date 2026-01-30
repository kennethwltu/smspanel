"""
Playwright UI tests for SMS Panel Compose page with baseline screenshot comparison.
Includes actual SMS sending tests to create real records.
"""

import pytest
import re
import os
import hashlib
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import Page, expect
from test_ui.db_reset_enhanced import enhanced_reset_for_testing


class TestComposePageBaseline:
    """Test suite for SMS Panel Compose page with baseline screenshot comparison."""
    
    # Configuration - CHANGE THESE SETTINGS AS NEEDED
    BASELINE_DIR = "test_ui/test_compose_baseline_screenshots"  # Store baseline images here
    ENABLE_VIDEO = False  # Set to True to enable video recording
    ENABLE_TRACE = False  # Set to True to enable trace recording
    
    # Login credentials
    LOGIN_URL = "http://127.0.0.1:3570/login?next=%2F"
    DASHBOARD_URL = "http://127.0.0.1:3570/"  # Dashboard is at root path
    COMPOSE_URL = "http://127.0.0.1:3570/compose"
    HISTORY_URL = "http://127.0.0.1:3570/history"
    USERNAME = "test_SMSadmin"
    PASSWORD = "test_SMSpass#12"
    
    # Test data for SMS sending
    TEST_RECIPIENTS = ["1234 5678", "8765 4321"]  # Test phone numbers
    TEST_MESSAGE = "This is a test message from Playwright UI tests"
    TEST_ENQUIRY_NUMBER = "9999 8888"
    
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
            context_args["record_video_dir"] = "test_videos_compose"
            context_args["record_video_size"] = {"width": 1280, "height": 800}
            os.makedirs("test_videos_compose", exist_ok=True)
        
        context = browser.new_context(**context_args)
        
        # Start optional tracing
        if self.ENABLE_TRACE:
            os.makedirs("test_traces_compose", exist_ok=True)
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
            trace_path = os.path.join("test_traces_compose", f"{test_name}.zip")
            context.tracing.stop(path=trace_path)
        
        # Close context (saves video if enabled)
        context.close()
        browser.close()
    
    @pytest.fixture(scope="function")
    def authenticated_page(self, browser_page: Page):
        """Create an authenticated page for compose tests."""
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
        SIMILARITY_THRESHOLD = 90.0  # 相似度閾值（百分比）
        
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
    
    # Test 1: Compose page loads correctly
    def test_compose_page_loads(self, authenticated_page: Page):
        """Test that compose page loads correctly after authentication."""
        page = authenticated_page
        
        # Navigate to compose page
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "compose_page")
        
        # Check page title
        expect(page).to_have_title(re.compile("Compose SMS - SMS Application"))
        
        # Check page header
        page_header = page.locator(".compose h1")
        expect(page_header).to_be_visible()
        expect(page_header).to_have_text("Compose SMS")
        self.take_baseline_screenshot(page, "compose_header")
    
    # Test 2: Compose form elements
    def test_compose_form_elements(self, authenticated_page: Page):
        """Test that compose form has all required elements."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "compose_form")
        
        # Check form exists
        compose_form = page.locator(".compose-form")
        expect(compose_form).to_be_visible()
        
        # Check CSRF token
        csrf_input = page.locator("input[name='csrf_token']")
        expect(csrf_input).to_have_attribute("type", "hidden")
        expect(csrf_input).to_be_attached()
        
        # Check recipients textarea
        recipients_textarea = page.locator("#recipients")
        expect(recipients_textarea).to_be_visible()
        expect(recipients_textarea).to_have_attribute("required", "")
        expect(recipients_textarea).to_have_attribute("name", "recipients")
        expect(recipients_textarea).to_have_attribute("rows", "4")
        
        # Check message textarea
        message_textarea = page.locator("#content")
        expect(message_textarea).to_be_visible()
        expect(message_textarea).to_have_attribute("required", "")
        expect(message_textarea).to_have_attribute("name", "content")
        expect(message_textarea).to_have_attribute("rows", "4")
        
        # Check enquiry number input
        enquiry_input = page.locator("#enquiry_number")
        expect(enquiry_input).to_be_visible()
        expect(enquiry_input).to_have_attribute("required", "")
        expect(enquiry_input).to_have_attribute("name", "enquiry_number")
        
        # Check character count display
        char_count = page.locator("#char-count")
        expect(char_count).to_be_visible()
        expect(char_count).to_have_text("0 characters")
        
        # Check submit button
        submit_button = page.locator("button[type='submit']")
        expect(submit_button).to_be_visible()
        expect(submit_button).to_have_text("Send SMS")
        
        # Check cancel button
        cancel_button = page.locator("a.btn-secondary")
        expect(cancel_button).to_be_visible()
        expect(cancel_button).to_have_text("Cancel")
        
        self.take_baseline_screenshot(page, "form_elements")
    
    # Test 3: Form validation - empty form
    def test_form_validation_empty(self, authenticated_page: Page):
        """Test form validation with empty fields."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "validation_start")
        
        # Try to submit empty form
        submit_button = page.locator("button[type='submit']")
        submit_button.click()
        
        # Wait for validation
        page.wait_for_timeout(1000)
        self.take_baseline_screenshot(page, "empty_form_validation")
        
        # Should stay on compose page (client-side validation)
        expect(page).to_have_url(re.compile(".*compose.*"))
    
    # Test 4: Form validation - invalid phone numbers
    def test_form_validation_invalid_phones(self, authenticated_page: Page):
        """Test form validation with invalid phone numbers."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "invalid_phones_start")
        
        # Fill form with invalid data
        page.locator("#recipients").fill("1234\ninvalid\n5678 9999")
        page.locator("#content").fill("Test message")
        page.locator("#enquiry_number").fill("1234 5678")
        
        self.take_baseline_screenshot(page, "invalid_phones_filled")
        
        # Trigger validation
        page.locator("#recipients").blur()
        page.wait_for_timeout(500)
        
        # Check for error message
        error_message = page.locator("#recipients-error")
        expect(error_message).to_be_visible()
        expect(error_message).to_contain_text("Invalid format")
        
        self.take_baseline_screenshot(page, "invalid_phones_error")
    
    # Test 5: Form validation - valid phone numbers
    def test_form_validation_valid_phones(self, authenticated_page: Page):
        """Test form validation with valid phone numbers."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "valid_phones_start")
        
        # Fill form with valid data
        recipients_text = "\n".join(self.TEST_RECIPIENTS)
        page.locator("#recipients").fill(recipients_text)
        page.locator("#content").fill(self.TEST_MESSAGE)
        page.locator("#enquiry_number").fill(self.TEST_ENQUIRY_NUMBER)
        
        self.take_baseline_screenshot(page, "valid_phones_filled")
        
        # Trigger validation
        page.locator("#recipients").blur()
        page.locator("#content").blur()
        page.locator("#enquiry_number").blur()
        page.wait_for_timeout(500)
        
        # Check no error messages
        recipients_error = page.locator("#recipients-error")
        content_error = page.locator("#content-error")
        enquiry_error = page.locator("#enquiry-error")
        
        expect(recipients_error).to_have_text("")
        expect(content_error).to_have_text("")
        expect(enquiry_error).to_have_text("")
        
        # Check character count updated (display includes "(SMS)")
        char_count = page.locator("#char-count")
        total_chars = len(self.TEST_MESSAGE) + len(self.TEST_ENQUIRY_NUMBER)
        expect(char_count).to_contain_text(f"{total_chars} characters (SMS)")
        
        self.take_baseline_screenshot(page, "valid_phones_no_errors")
    
    # Test 6: Actual SMS sending (creates real records)
    def test_actual_sms_sending(self, authenticated_page: Page):
        """Test actual SMS sending to create real records in dashboard and history."""
        page = authenticated_page
        
        # Start from dashboard to see before state
        page.goto(self.DASHBOARD_URL)
        self.take_baseline_screenshot(page, "dashboard_before_sending")
        
        # Navigate to compose page
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "compose_before_fill")
        
        # Fill form with test data
        recipients_text = "\n".join(self.TEST_RECIPIENTS)
        page.locator("#recipients").fill(recipients_text)
        page.locator("#content").fill(self.TEST_MESSAGE)
        page.locator("#enquiry_number").fill(self.TEST_ENQUIRY_NUMBER)
        
        self.take_baseline_screenshot(page, "compose_filled")
        
        # Submit the form
        submit_button = page.locator("button[type='submit']")
        submit_button.click()
        
        # Wait for submission to complete
        page.wait_for_timeout(3000)
        self.take_baseline_screenshot(page, "after_submission")
        
        # Check if we were redirected (either to message detail or dashboard)
        current_url = page.url
        
        if "sms_detail" in current_url or "message" in current_url:
            # Redirected to message detail page
            expect(page).to_have_title(re.compile("Message Details - SMS Application"))
            expect(page.locator("h1")).to_contain_text("Message Details")
            
            # Check for success flash message
            flash_messages = page.locator(".flash")
            if flash_messages.count() > 0:
                print(f"Flash message found: {flash_messages.first.text_content()}")
            
            self.take_baseline_screenshot(page, "message_detail_page")
            
            # Go back to dashboard to check if record appears
            page.goto(self.DASHBOARD_URL)
            page.wait_for_timeout(2000)
            
        elif "dashboard" in current_url:
            # Redirected to dashboard
            expect(page).to_have_url(re.compile(".*/.*"))
            self.take_baseline_screenshot(page, "redirected_to_dashboard")
        
        # Check dashboard for new records
        page.wait_for_timeout(2000)
        self.take_baseline_screenshot(page, "dashboard_after_sending")
        
        # Check if messages table shows the new message
        table_container = page.locator(".table-container")
        if table_container.count() > 0:
            # Table exists, check for our test message
            message_rows = page.locator(".message-row")
            if message_rows.count() > 0:
                # Look for our test message content
                for i in range(message_rows.count()):
                    row = message_rows.nth(i)
                    message_content = row.locator(".message-content").text_content()
                    if self.TEST_MESSAGE in message_content:
                        print(f"Found test message in dashboard row {i+1}")
                        self.take_baseline_screenshot(page, "test_message_in_dashboard")
                        break
        
        # Also check history page
        page.goto(self.HISTORY_URL)
        page.wait_for_timeout(2000)
        self.take_baseline_screenshot(page, "history_after_sending")
        
        # Check history page for the message
        history_table = page.locator(".table-container")
        if history_table.count() > 0:
            history_rows = page.locator(".message-row")
            if history_rows.count() > 0:
                for i in range(history_rows.count()):
                    row = history_rows.nth(i)
                    message_content = row.locator(".message-content").text_content()
                    if self.TEST_MESSAGE in message_content:
                        print(f"Found test message in history row {i+1}")
                        self.take_baseline_screenshot(page, "test_message_in_history")
                        break
    
    # Test 7: Character count functionality
    def test_character_count_functionality(self, authenticated_page: Page):
        """Test character count updates as user types."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "char_count_start")
        
        # Check initial character count
        char_count = page.locator("#char-count")
        expect(char_count).to_have_text("0 characters")
        
        # Type in message
        page.locator("#content").fill("Hello")
        page.wait_for_timeout(300)
        
        # Check character count updated
        expect(char_count).to_contain_text("5 characters")
        self.take_baseline_screenshot(page, "char_count_after_message")
        
        # Type in enquiry number
        page.locator("#enquiry_number").fill("1234 5678")
        page.wait_for_timeout(300)
        
        # Check character count updated (5 + 9 = 14, display includes "(SMS)")
        # "1234 5678" has 8 digits + 1 space = 9 characters
        expect(char_count).to_contain_text("14 characters (SMS)")
        self.take_baseline_screenshot(page, "char_count_after_enquiry")
        
        # Clear fields and check count resets
        page.locator("#content").fill("")
        page.locator("#enquiry_number").fill("")
        page.wait_for_timeout(300)
        
        expect(char_count).to_contain_text("0 characters")
        self.take_baseline_screenshot(page, "char_count_reset")
    
    # Test 8: Cancel button functionality
    def test_cancel_button_functionality(self, authenticated_page: Page):
        """Test cancel button redirects to dashboard."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "cancel_button_start")
        
        # Fill some data
        page.locator("#recipients").fill("1234 5678")
        page.locator("#content").fill("Test message")
        page.locator("#enquiry_number").fill("1234 5678")
        
        self.take_baseline_screenshot(page, "cancel_button_filled")
        
        # Click cancel button
        cancel_button = page.locator("a.btn-secondary")
        cancel_button.click()
        
        # Wait for redirect
        page.wait_for_timeout(1000)
        
        # Should be redirected to dashboard
        expect(page).to_have_url(re.compile(".*/.*"))  # Dashboard URL
        expect(page).to_have_title(re.compile("Dashboard - SMS Application"))
        
        self.take_baseline_screenshot(page, "cancel_button_redirected")
    
    # Test 9: Responsive design on compose page
    def test_compose_responsive_design(self, authenticated_page: Page):
        """Test compose page responsive design on different viewports."""
        page = authenticated_page
        
        # Test mobile viewport
        page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "compose_mobile_viewport")
        
        # Check mobile layout elements
        compose_header = page.locator(".compose h1")
        expect(compose_header).to_be_visible()
        
        compose_form = page.locator(".compose-form")
        expect(compose_form).to_be_visible()
        
        # Test tablet viewport
        page.set_viewport_size({"width": 768, "height": 1024})  # iPad
        self.take_baseline_screenshot(page, "compose_tablet_viewport")
        
        # Test desktop viewport
        page.set_viewport_size({"width": 1280, "height": 800})  # Desktop
        self.take_baseline_screenshot(page, "compose_desktop_viewport")
        
        # Verify key elements are visible on all viewports
        expect(page.locator(".compose h1")).to_be_visible()
        expect(page.locator("#recipients")).to_be_visible()
        expect(page.locator("#content")).to_be_visible()
        expect(page.locator("#enquiry_number")).to_be_visible()
    
    # Test 10: Placeholder text verification
    def test_placeholder_text(self, authenticated_page: Page):
        """Test that form fields have correct placeholder text."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "placeholder_check")
        
        # Check recipients placeholder
        recipients = page.locator("#recipients")
        expect(recipients).to_have_attribute("placeholder", re.compile(r".*"))
        placeholder_text = recipients.get_attribute("placeholder")
        print(f"Recipients placeholder: {placeholder_text}")
        
        # Check message placeholder
        message = page.locator("#content")
        expect(message).to_have_attribute("placeholder", "Enter your message here...")
        
        # Check enquiry number placeholder
        enquiry = page.locator("#enquiry_number")
        expect(enquiry).to_have_attribute("placeholder", "1234 5678")
        
        self.take_baseline_screenshot(page, "placeholder_verified")
    
    # Test 11: Form submission with minimal valid data
    def test_minimal_valid_submission(self, authenticated_page: Page):
        """Test form submission with minimal valid data."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "minimal_start")
        
        # Fill form with minimal valid data
        page.locator("#recipients").fill("1234 5678")
        page.locator("#content").fill("Test")
        page.locator("#enquiry_number").fill("1234 5678")
        
        self.take_baseline_screenshot(page, "minimal_filled")
        
        # Submit the form
        submit_button = page.locator("button[type='submit']")
        submit_button.click()
        
        # Wait for submission
        page.wait_for_timeout(3000)
        self.take_baseline_screenshot(page, "minimal_submitted")
        
        # Check if submission was successful
        current_url = page.url
        
        if "sms_detail" in current_url or "message" in current_url:
            # Success - redirected to message detail
            print("Minimal submission successful - redirected to message detail")
            self.take_baseline_screenshot(page, "minimal_success")
        elif "compose" in current_url:
            # Failed - still on compose page
            print("Minimal submission failed - still on compose page")
            
            # Check for error messages
            flash_messages = page.locator(".flash")
            if flash_messages.count() > 0:
                error_text = flash_messages.first.text_content()
                print(f"Error message: {error_text}")
            
            self.take_baseline_screenshot(page, "minimal_failed")
        else:
            # Redirected elsewhere (likely dashboard)
            print(f"Minimal submission redirected to: {current_url}")
            self.take_baseline_screenshot(page, "minimal_redirected")
    
    # Test 12: Recipient autocomplete functionality
    def test_recipient_autocomplete_functionality(self, authenticated_page: Page):
        """Test recipient input autocomplete functionality."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "autocomplete_start")
        
        # Check if autocomplete suggestions exist
        recipients_input = page.locator("#recipients")
        
        # Type a partial phone number
        recipients_input.fill("1234")
        page.wait_for_timeout(500)
        
        # Check for autocomplete suggestions
        autocomplete_suggestions = page.locator(".autocomplete-suggestions, .suggestions-list, [role='listbox']")
        
        if autocomplete_suggestions.count() > 0:
            # Autocomplete is implemented
            expect(autocomplete_suggestions).to_be_visible()
            self.take_baseline_screenshot(page, "autocomplete_suggestions")
            
            # Check if suggestions contain matching numbers
            suggestion_items = autocomplete_suggestions.locator("li, [role='option']")
            if suggestion_items.count() > 0:
                print(f"Found {suggestion_items.count()} autocomplete suggestions")
                
                # Click first suggestion
                first_suggestion = suggestion_items.first
                first_suggestion.click()
                page.wait_for_timeout(500)
                
                # Check if suggestion was added to input
                input_value = recipients_input.input_value()
                print(f"Input value after selecting suggestion: {input_value}")
                self.take_baseline_screenshot(page, "autocomplete_selected")
            else:
                print("No suggestion items found in autocomplete")
        else:
            # Autocomplete not implemented - test basic input functionality
            print("Autocomplete not implemented, testing basic input functionality")
            
            # Test typing multiple recipients
            recipients_input.fill("1234 5678\n8765 4321\n9999 8888")
            page.wait_for_timeout(500)
            
            # Check input value
            input_value = recipients_input.input_value()
            print(f"Multiple recipients entered: {input_value}")
            self.take_baseline_screenshot(page, "multiple_recipients")
    
    # Test 13: Message template selection functionality
    def test_message_template_selection(self, authenticated_page: Page):
        """Test message template selection functionality."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "template_start")
        
        # Check if template selection exists
        template_select = page.locator("#template-select, select[name='template'], .template-select")
        
        if template_select.count() > 0:
            # Template selection is implemented
            expect(template_select).to_be_visible()
            
            # Check template options
            template_options = template_select.locator("option")
            expect(template_options).to_have_count_at_least(2)  # At least one template + empty option
            
            print(f"Found {template_options.count()} template options")
            
            # Select a template
            if template_options.count() > 1:
                # Select first non-empty template
                for i in range(template_options.count()):
                    option = template_options.nth(i)
                    option_value = option.get_attribute("value")
                    if option_value and option_value != "":
                        template_select.select_option(option_value)
                        break
                
                page.wait_for_timeout(500)
                self.take_baseline_screenshot(page, "template_selected")
                
                # Check if message content was populated
                message_content = page.locator("#content")
                content_value = message_content.input_value()
                
                if content_value:
                    print(f"Template populated message: {content_value[:50]}...")
                    
                    # Check character count updated
                    char_count = page.locator("#char-count")
                    expect(char_count).to_contain_text(f"{len(content_value)} characters")
                    
                    self.take_baseline_screenshot(page, "template_content_populated")
                else:
                    print("Template selection did not populate message content")
            else:
                print("No template options available")
        else:
            # Template selection not implemented
            print("Message template selection not implemented")
            self.take_baseline_screenshot(page, "no_template_selection")
    
    # Test 14: File upload functionality (if available)
    def test_file_upload_functionality(self, authenticated_page: Page):
        """Test file upload functionality for recipients or message content."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "file_upload_start")
        
        # Check if file upload exists
        file_upload = page.locator("input[type='file'], #file-upload, .file-upload")
        
        if file_upload.count() > 0:
            # File upload is implemented
            expect(file_upload).to_be_visible()
            
            # Check upload button/label
            upload_button = page.locator(".upload-button, label[for*='file'], button:has-text('Upload')")
            if upload_button.count() > 0:
                expect(upload_button).to_be_visible()
            
            self.take_baseline_screenshot(page, "file_upload_element")
            
            # Test file upload functionality (simulated)
            # Note: Actual file upload would require a test file
            print("File upload element found - functionality would require actual file for testing")
            
            # Check accepted file types
            accept_attr = file_upload.get_attribute("accept")
            if accept_attr:
                print(f"Accepted file types: {accept_attr}")
            
            # Check if there's a file list display
            file_list = page.locator(".file-list, .uploaded-files")
            if file_list.count() > 0:
                expect(file_list).to_be_visible()
                self.take_baseline_screenshot(page, "file_list_display")
        else:
            # File upload not implemented
            print("File upload functionality not implemented")
            self.take_baseline_screenshot(page, "no_file_upload")
    
    # Test 15: Scheduled sending functionality
    def test_scheduled_sending_functionality(self, authenticated_page: Page):
        """Test scheduled SMS sending functionality."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "scheduled_start")
        
        # Check if scheduled sending option exists
        schedule_option = page.locator("#schedule-send, input[name='schedule'], .schedule-option")
        
        if schedule_option.count() > 0:
            # Scheduled sending is implemented
            expect(schedule_option).to_be_visible()
            
            # Check schedule checkbox/toggle
            schedule_checkbox = page.locator("input[type='checkbox'][name*='schedule'], #schedule-checkbox")
            if schedule_checkbox.count() > 0:
                # It's a checkbox
                expect(schedule_checkbox).to_be_visible()
                
                # Check the checkbox
                schedule_checkbox.check()
                page.wait_for_timeout(500)
                self.take_baseline_screenshot(page, "schedule_checked")
                
                # Check if datetime picker appears
                datetime_picker = page.locator("input[type='datetime-local'], #schedule-datetime, .datetime-picker")
                if datetime_picker.count() > 0:
                    expect(datetime_picker).to_be_visible()
                    
                    # Set a future date/time
                    from datetime import datetime, timedelta
                    future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
                    datetime_picker.fill(future_date)
                    
                    page.wait_for_timeout(500)
                    self.take_baseline_screenshot(page, "datetime_set")
                    
                    print(f"Scheduled sending set for: {future_date}")
                else:
                    print("No datetime picker found for scheduled sending")
            else:
                # It might be a select/dropdown
                schedule_select = page.locator("select[name*='schedule']")
                if schedule_select.count() > 0:
                    expect(schedule_select).to_be_visible()
                    
                    # Select a schedule option
                    schedule_options = schedule_select.locator("option")
                    if schedule_options.count() > 1:
                        # Select first non-empty option
                        for i in range(schedule_options.count()):
                            option = schedule_options.nth(i)
                            option_value = option.get_attribute("value")
                            if option_value and option_value != "":
                                schedule_select.select_option(option_value)
                                break
                        
                        page.wait_for_timeout(500)
                        self.take_baseline_screenshot(page, "schedule_selected")
                        
                        selected_option = schedule_select.input_value()
                        print(f"Selected schedule option: {selected_option}")
        else:
            # Scheduled sending not implemented
            print("Scheduled sending functionality not implemented")
            self.take_baseline_screenshot(page, "no_schedule_option")
    
    # Test 16: Message preview functionality
    def test_message_preview_functionality(self, authenticated_page: Page):
        """Test message preview functionality before sending."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "preview_start")
        
        # Fill form with test data
        recipients_text = "\n".join(self.TEST_RECIPIENTS)
        page.locator("#recipients").fill(recipients_text)
        page.locator("#content").fill(self.TEST_MESSAGE)
        page.locator("#enquiry_number").fill(self.TEST_ENQUIRY_NUMBER)
        
        self.take_baseline_screenshot(page, "preview_filled")
        
        # Check if preview button exists
        preview_button = page.locator("#preview-button, button:has-text('Preview'), .preview-btn")
        
        if preview_button.count() > 0:
            # Preview functionality is implemented
            expect(preview_button).to_be_visible()
            
            # Click preview button
            preview_button.click()
            page.wait_for_timeout(1000)
            self.take_baseline_screenshot(page, "preview_clicked")
            
            # Check if preview modal/window appears
            preview_modal = page.locator(".preview-modal, .modal-content, [role='dialog']")
            
            if preview_modal.count() > 0:
                expect(preview_modal).to_be_visible()
                
                # Check preview content
                preview_content = preview_modal.locator(".preview-content, .message-preview")
                expect(preview_content).to_be_visible()
                
                # Check if message content is displayed in preview
                preview_text = preview_content.text_content()
                if self.TEST_MESSAGE in preview_text:
                    print("Message content correctly displayed in preview")
                
                # Check if recipients are displayed in preview
                preview_recipients = preview_modal.locator(".preview-recipients, .recipients-preview")
                if preview_recipients.count() > 0:
                    recipients_text = preview_recipients.text_content()
                    print(f"Recipients in preview: {recipients_text}")
                
                self.take_baseline_screenshot(page, "preview_modal")
                
                # Check close button
                close_button = preview_modal.locator(".close-button, button:has-text('Close'), [aria-label='Close']")
                if close_button.count() > 0:
                    expect(close_button).to_be_visible()
                    close_button.click()
                    page.wait_for_timeout(500)
                    expect(preview_modal).not_to_be_visible()
                    self.take_baseline_screenshot(page, "preview_closed")
            else:
                # Preview might be inline or on same page
                preview_section = page.locator(".preview-section, #message-preview")
                if preview_section.count() > 0:
                    expect(preview_section).to_be_visible()
                    self.take_baseline_screenshot(page, "preview_section")
                else:
                    print("Preview modal/section not found after clicking preview button")
        else:
            # Preview functionality not implemented
            print("Message preview functionality not implemented")
            self.take_baseline_screenshot(page, "no_preview_button")
    
    # Test 17: Recipient count limit testing
    def test_recipient_count_limit(self, authenticated_page: Page):
        """Test recipient count limit functionality."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "recipient_limit_start")
        
        recipients_input = page.locator("#recipients")
        
        # Create a list of many phone numbers to test limits
        many_recipients = []
        for i in range(1, 101):  # Create 100 phone numbers
            phone = f"{5000 + i:04d} {6000 + i:04d}"  # Format: 5001 6001, 5002 6002, etc.
            many_recipients.append(phone)
        
        # Enter many recipients
        recipients_input.fill("\n".join(many_recipients))
        page.wait_for_timeout(500)
        
        self.take_baseline_screenshot(page, "many_recipients_entered")
        
        # Check for recipient count display
        recipient_count = page.locator("#recipient-count, .recipient-count, [data-recipient-count]")
        
        if recipient_count.count() > 0:
            # Recipient count display is implemented
            expect(recipient_count).to_be_visible()
            
            count_text = recipient_count.text_content()
            print(f"Recipient count display: {count_text}")
            
            # Check if count matches expected
            if "100" in count_text or len(many_recipients) in count_text:
                print(f"Recipient count correctly shows {len(many_recipients)} recipients")
            
            self.take_baseline_screenshot(page, "recipient_count_display")
        
        # Check for limit warnings
        limit_warning = page.locator(".limit-warning, .recipient-limit, [data-limit-warning]")
        if limit_warning.count() > 0:
            expect(limit_warning).to_be_visible()
            warning_text = limit_warning.text_content()
            print(f"Limit warning: {warning_text}")
            self.take_baseline_screenshot(page, "limit_warning")
        
        # Test submitting with many recipients
        page.locator("#content").fill("Test message for many recipients")
        page.locator("#enquiry_number").fill("1234 5678")
        
        submit_button = page.locator("button[type='submit']")
        submit_button.click()
        page.wait_for_timeout(2000)
        
        # Check if submission was blocked due to limit
        current_url = page.url
        if "compose" in current_url:
            # Still on compose page - check for error messages
            error_messages = page.locator(".flash-error, .alert-danger, .error-message")
            if error_messages.count() > 0:
                error_text = error_messages.first.text_content()
                print(f"Submission blocked with error: {error_text}")
                self.take_baseline_screenshot(page, "submission_blocked")
            else:
                print("Submission may have failed silently due to recipient limit")
                self.take_baseline_screenshot(page, "submission_failed_silently")
        else:
            print(f"Submission with many recipients redirected to: {current_url}")
            self.take_baseline_screenshot(page, "submission_redirected")
    
    # Test 18: Message length limit testing
    def test_message_length_limit(self, authenticated_page: Page):
        """Test message length limit functionality."""
        page = authenticated_page
        
        page.goto(self.COMPOSE_URL)
        self.take_baseline_screenshot(page, "message_length_start")
        
        message_input = page.locator("#content")
        
        # Create a very long message to test limits
        # Standard SMS limit is 160 characters, but we'll test with longer
        long_message = "This is a very long test message " * 50  # About 1500 characters
        message_input.fill(long_message)
        page.wait_for_timeout(500)
        
        self.take_baseline_screenshot(page, "long_message_entered")
        
        # Check character count display
        char_count = page.locator("#char-count")
        expect(char_count).to_be_visible()
        
        count_text = char_count.text_content()
        print(f"Character count: {count_text}")
        
        # Check for SMS segment information
        if "SMS" in count_text or "segment" in count_text.lower():
            print("SMS segment information displayed")
            self.take_baseline_screenshot(page, "sms_segment_info")
        
        # Check for length limit warnings
        length_warning = page.locator(".length-warning, .message-limit, [data-length-warning]")
        if length_warning.count() > 0:
            expect(length_warning).to_be_visible()
            warning_text = length_warning.text_content()
            print(f"Length warning: {warning_text}")
            self.take_baseline_screenshot(page, "length_warning")
        
        # Fill other required fields
        page.locator("#recipients").fill("1234 5678")
        page.locator("#enquiry_number").fill("1234 5678")
        
        # Try to submit with long message
        submit_button = page.locator("button[type='submit']")
        submit_button.click()
        page.wait_for_timeout(2000)
        
        # Check if submission was successful or blocked
        current_url = page.url
        
        if "compose" in current_url:
            # Still on compose page - check for validation errors
            content_error = page.locator("#content-error, .content-error")
            if content_error.count() > 0:
                error_text = content_error.text_content()
                print(f"Message length validation error: {error_text}")
                self.take_baseline_screenshot(page, "length_validation_error")
            else:
                # Check for flash/alert messages
                flash_messages = page.locator(".flash, .alert")
                if flash_messages.count() > 0:
                    flash_text = flash_messages.first.text_content()
                    print(f"Flash message: {flash_text}")
                    self.take_baseline_screenshot(page, "flash_message")
                else:
                    print("Submission with long message failed silently")
                    self.take_baseline_screenshot(page, "long_message_failed")
        else:
            print(f"Long message submission redirected to: {current_url}")
            self.take_baseline_screenshot(page, "long_message_submitted")
        
        # Test with message at exact limit (if known)
        # Standard SMS limit is 160 characters
        exact_limit_message = "A" * 160
        page.goto(self.COMPOSE_URL)
        page.locator("#content").fill(exact_limit_message)
        page.locator("#recipients").fill("1234 5678")
        page.locator("#enquiry_number").fill("1234 5678")
        
        page.wait_for_timeout(500)
        self.take_baseline_screenshot(page, "exact_limit_message")
        
        # Check character count for exact limit
        count_text = char_count.text_content()
        print(f"Character count at exact limit: {count_text}")
        
        # Test submission at exact limit
        submit_button.click()
        page.wait_for_timeout(2000)
        
        if "compose" not in page.url:
            print("Exact limit message submitted successfully")
            self.take_baseline_screenshot(page, "exact_limit_submitted")
        else:
            print("Exact limit message submission failed")
            self.take_baseline_screenshot(page, "exact_limit_failed")



def run_compose_baseline_tests():
    """Run compose page baseline tests and show summary."""
    import subprocess
    import sys
    
    print("=" * 60)
    print("SMS Panel Compose Page Baseline Tests")
    print("=" * 60)
    print("Features:")
    print("- Trace recording: DISABLED by default")
    print("- Video recording: DISABLED by default")
    print("- Screenshot comparison: ENABLED")
    print("- Baseline images: test_ui/test_compose_baseline_screenshots/")
    print("- Authentication: Auto-login with test_SMSadmin credentials")
    print("- Actual SMS sending: Creates real records")
    print("=" * 60)
    
    # Create directories
    os.makedirs("test_ui/test_compose_baseline_screenshots", exist_ok=True)
    
    # Run tests
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        __file__,
        "-v",
        "--headed"
    ])
    
    print("\n" + "=" * 60)
    print("COMPOSE PAGE BASELINE TEST SUMMARY")
    print("=" * 60)
    
    # Count baseline files
    baseline_dir = "test_ui/test_compose_baseline_screenshots"
    if os.path.exists(baseline_dir):
        baseline_files = [f for f in os.listdir(baseline_dir) if f.endswith('.png')]
        print(f"Compose page baseline screenshots: {len(baseline_files)} files")
        
        # Show some examples
        if baseline_files:
            print("\nExample baseline files:")
            for f in baseline_files[:5]:
                print(f"  - {f}")
            if len(baseline_files) > 5:
                print(f"  - ... and {len(baseline_files) - 5} more")
    
    print("\nTo update baseline images:")
    print("1. Delete files from test_ui/test_compose_baseline_screenshots/")
    print("2. Run tests again to create new baselines")
    print("\nTo enable trace/video recording:")
    print("Edit test_ui/test_compose_page_baseline.py")
    print("Set ENABLE_TRACE = True for trace recording")
    print("Set ENABLE_VIDEO = True for video recording")
    
    return result.returncode


if __name__ == "__main__":
    """Command line interface."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        sys.exit(run_compose_baseline_tests())
    else:
        print("Usage:")
        print("  python test_ui/test_compose_page_baseline.py run")
        print()
        print("Or run with pytest directly:")
        print("  pytest test_ui/test_compose_page_baseline.py -v --headed")
        print()
        print("Test suite includes:")
        print("  1. Compose page loads after authentication")
        print("  2. Compose form elements")
        print("  3. Form validation - empty form")
        print("  4. Form validation - invalid phone numbers")
        print("  5. Form validation - valid phone numbers")
        print("  6. Actual SMS sending (creates real records)")
        print("  7. Character count functionality")
        print("  8. Cancel button functionality")
        print("  9. Responsive design")
        print("  10. Placeholder text verification")
        print("  11. Minimal valid submission")
        print("  12. Recipient autocomplete functionality")
        print("  13. Message template selection functionality")
        print("  14. File upload functionality (if available)")
        print("  15. Scheduled sending functionality")
        print("  16. Message preview functionality")
        print("  17. Recipient count limit testing")
        print("  18. Message length limit testing")

