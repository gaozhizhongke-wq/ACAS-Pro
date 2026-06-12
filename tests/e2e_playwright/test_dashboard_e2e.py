#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACAS Pro Playwright E2E Tests - Web Dashboard UI Tests

Tests the complete user journey through the ACAS Pro web dashboard.
"""

import re
from playwright.sync_api import Page, expect


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def wait_for_page_load(page: Page, timeout: int = 10000):
    """Wait for page to be fully loaded."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
    except Exception:
        # Fallback: wait for body to be visible
        page.wait_for_selector("body", state="visible", timeout=timeout)


def navigate_to_page(page: Page, page_name: str, timeout: int = 5000):
    """Navigate to a specific page using sidebar."""
    nav_item = page.locator(f"[data-page={page_name}]")
    nav_item.click()
    # Wait for page to be visible
    page_div = page.locator(f"#page-{page_name}")
    page_div.wait_for(state="visible", timeout=timeout)
    return page_div


def safe_goto(page: Page, url: str, timeout: int = 60000):
    """Safely navigate to a URL with error handling."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    except Exception:
        # Try again with networkidle
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception:
            # Last resort: just wait for body
            page.wait_for_selector("body", state="visible", timeout=10000)


# ─────────────────────────────────────────────────────────────────────────────
# Auth Flow Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthFlow:
    """Test authentication flow (login/register)."""
    
    def test_dashboard_loads(self, authenticated_page: Page, flask_server: str):
        """Dashboard should load and show sidebar."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Check sidebar exists
        sidebar = authenticated_page.locator(".sidebar")
        expect(sidebar).to_be_visible()
        
        # Check logo
        logo = authenticated_page.locator(".logo")
        expect(logo).to_contain_text("ACAS Pro")
        
        # Auth overlay should be hidden (token injected)
        auth_overlay = authenticated_page.locator("#auth-overlay")
        expect(auth_overlay).not_to_be_visible()
    
    def test_login_overlay_can_be_shown(self, authenticated_page: Page, flask_server: str):
        """Login overlay can be manually shown."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Manually show the overlay
        authenticated_page.evaluate("document.getElementById('auth-overlay').classList.remove('hidden')")
        
        auth_overlay = authenticated_page.locator("#auth-overlay")
        expect(auth_overlay).to_be_visible()
    
    def test_register_toggle(self, authenticated_page: Page, flask_server: str):
        """Register/Login toggle should switch auth mode."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Manually show the overlay
        authenticated_page.evaluate("document.getElementById('auth-overlay').classList.remove('hidden')")
        
        auth_overlay = authenticated_page.locator("#auth-overlay")
        expect(auth_overlay).to_be_visible()
        
        # Check initial state is login
        auth_title = authenticated_page.locator("#auth-title")
        expect(auth_title).to_contain_text("登录")
        
        # Toggle to register
        register_link = authenticated_page.locator("#auth-switch-link")
        register_link.click()
        
        expect(auth_title).to_contain_text("注册")
        
        # Register fields should appear
        nickname_field = authenticated_page.locator("#auth-nickname")
        expect(nickname_field).to_be_visible()
        
        # Toggle back to login
        login_link = authenticated_page.locator("#auth-switch-link")
        login_link.click()
        
        expect(auth_title).to_contain_text("登录")


# ─────────────────────────────────────────────────────────────────────────────
# Navigation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestNavigation:
    """Test sidebar navigation between pages."""
    
    def test_navigate_to_all_pages(self, authenticated_page: Page, flask_server: str):
        """All navigation items should switch pages."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # List of all pages
        pages = [
            ("dashboard", "欢迎回来"),
            ("llm", "AI 助手"),
            ("content", "内容创作"),
            ("accounts", "账号矩阵"),
            ("festival", "节日营销"),
            ("forecast", "销售预测"),
            ("inventory", "库存管理"),
            ("settings", "系统设置"),
        ]
        
        for page_name, page_title in pages:
            nav_item = authenticated_page.locator(f"[data-page={page_name}]")
            nav_item.click()
            
            # Wait for page to be visible
            page_div = authenticated_page.locator(f"#page-{page_name}")
            page_div.wait_for(state="visible", timeout=5000)
            expect(page_div).to_be_visible()
            
            # Check nav item is active
            expect(nav_item).to_have_class(re.compile("active"))
    
    def test_dashboard_page_default(self, authenticated_page: Page, flask_server: str):
        """Dashboard page should be shown by default."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Dashboard should be visible
        dashboard_page = authenticated_page.locator("#page-dashboard")
        expect(dashboard_page).to_be_visible()
        
        # Stats cards should exist
        revenue_card = authenticated_page.locator("#stat-revenue")
        expect(revenue_card).to_be_visible()
    
    def test_llm_page_has_chat(self, authenticated_page: Page, flask_server: str):
        """LLM page should have chat interface."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Navigate to LLM page
        navigate_to_page(authenticated_page, "llm")
        
        # Check chat elements
        chat_container = authenticated_page.locator(".chat-container")
        expect(chat_container).to_be_visible()
        
        chat_messages = authenticated_page.locator("#chat-messages")
        expect(chat_messages).to_be_visible()
        
        chat_input = authenticated_page.locator("#chat-input")
        expect(chat_input).to_be_visible()
        
        send_btn = authenticated_page.locator("button:has-text('发送')")
        expect(send_btn).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDashboard:
    """Test dashboard features."""
    
    def test_dashboard_stats_load(self, authenticated_page: Page, flask_server: str):
        """Dashboard stats should load from API."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Stats cards should exist (even if showing "--" or "加载中...")
        revenue_card = authenticated_page.locator("#stat-revenue")
        orders_card = authenticated_page.locator("#stat-orders")
        inventory_card = authenticated_page.locator("#stat-inventory")
        alerts_card = authenticated_page.locator("#stat-alerts")
        
        expect(revenue_card).to_be_visible()
        expect(orders_card).to_be_visible()
        expect(inventory_card).to_be_visible()
        expect(alerts_card).to_be_visible()
    
    def test_quick_action_buttons(self, authenticated_page: Page, flask_server: str):
        """Quick action buttons should navigate to correct pages."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Test each quick action button (using onclick navigation)
        quick_actions = [
            ("📈 查看预测", "forecast"),
            ("📦 库存检查", "inventory"),
            ("🤖 AI 助手", "llm"),
            ("⚙️ 系统设置", "settings"),
        ]
        
        for button_text, expected_page in quick_actions:
            # Re-navigate to dashboard for each test
            if expected_page != "dashboard":
                navigate_to_page(authenticated_page, "dashboard")
            
            # Find button and click
            btn = authenticated_page.locator(f"a:has-text('{button_text.split()[1]}')")
            if btn.count() == 0:
                # Try alternate selector
                btn = authenticated_page.locator(f"text={button_text.split()[1]}")
            btn.first.click()
            
            # Check page is visible
            page_div = authenticated_page.locator(f"#page-{expected_page}")
            page_div.wait_for(state="visible", timeout=5000)
            expect(page_div).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# Content Creation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestContentCreation:
    """Test content creation features."""
    
    def test_content_form_elements(self, authenticated_page: Page, flask_server: str):
        """Content creation form should have all required fields."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Navigate to content page
        navigate_to_page(authenticated_page, "content")
        
        # Check form elements
        platform_select = authenticated_page.locator("#content-platform")
        expect(platform_select).to_be_visible()
        
        topic_input = authenticated_page.locator("#content-topic")
        expect(topic_input).to_be_visible()
        
        style_select = authenticated_page.locator("#content-style")
        expect(style_select).to_be_visible()
        
        generate_btn = authenticated_page.locator("button:has-text('AI 生成文案')")
        expect(generate_btn).to_be_visible()
    
    def test_platform_options(self, authenticated_page: Page, flask_server: str):
        """Platform dropdown should have expected options."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        navigate_to_page(authenticated_page, "content")
        
        platform_select = authenticated_page.locator("#content-platform")
        
        # Check options exist by value
        expect(platform_select.locator("option[value=xiaohongshu]")).to_have_count(1)
        expect(platform_select.locator("option[value=douyin]")).to_have_count(1)
        expect(platform_select.locator("option[value=weibo]")).to_have_count(1)
        expect(platform_select.locator("option[value=wechat]")).to_have_count(1)


# ─────────────────────────────────────────────────────────────────────────────
# Accounts Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAccounts:
    """Test account matrix features."""
    
    def test_accounts_table_structure(self, authenticated_page: Page, flask_server: str):
        """Accounts table should have correct columns."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Navigate to accounts page
        navigate_to_page(authenticated_page, "accounts")
        
        # Check table exists
        accounts_table = authenticated_page.locator("#accounts-table")
        expect(accounts_table).to_be_visible()
        
        # Check table has content (headers are in first row or thead)
        # The table structure uses inline headers in thead
        table_content = accounts_table.inner_text()
        assert "平台" in table_content or "账号" in table_content
    
    def test_refresh_button(self, authenticated_page: Page, flask_server: str):
        """Refresh button should reload accounts data."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        navigate_to_page(authenticated_page, "accounts")
        
        # Scope refresh button to accounts page only
        refresh_btn = authenticated_page.locator("#page-accounts button:has-text('刷新')")
        expect(refresh_btn).to_be_visible()
        
        # Click should trigger data reload
        refresh_btn.click()
        
        # Table should still be visible after refresh
        accounts_table = authenticated_page.locator("#accounts-table")
        expect(accounts_table).to_be_visible()


# ─────────────────────────────────────────────────────────────────────────────
# Festival Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestFestival:
    """Test festival marketing features."""
    
    def test_festival_page_loads(self, authenticated_page: Page, flask_server: str):
        """Festival page should load correctly."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Navigate to festival page
        navigate_to_page(authenticated_page, "festival")
        
        # Check page content
        festival_page = authenticated_page.locator("#page-festival")
        expect(festival_page).to_be_visible()
        
        # Header should be visible
        header = authenticated_page.locator("#page-festival .header h1")
        expect(header).to_contain_text("节日营销")


# ─────────────────────────────────────────────────────────────────────────────
# Forecast Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestForecast:
    """Test sales forecast features."""
    
    def test_forecast_page_loads(self, authenticated_page: Page, flask_server: str):
        """Forecast page should load correctly."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Navigate to forecast page
        navigate_to_page(authenticated_page, "forecast")
        
        # Check page content
        forecast_page = authenticated_page.locator("#page-forecast")
        expect(forecast_page).to_be_visible()
        
        # Header should be visible
        header = authenticated_page.locator("#page-forecast .header h1")
        expect(header).to_contain_text("销售预测")


# ─────────────────────────────────────────────────────────────────────────────
# Inventory Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestInventory:
    """Test inventory management features."""
    
    def test_inventory_page_loads(self, authenticated_page: Page, flask_server: str):
        """Inventory page should load correctly."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Navigate to inventory page
        navigate_to_page(authenticated_page, "inventory")
        
        # Check page content
        inventory_page = authenticated_page.locator("#page-inventory")
        expect(inventory_page).to_be_visible()
        
        # Header should be visible
        header = authenticated_page.locator("#page-inventory .header h1")
        expect(header).to_contain_text("库存管理")


# ─────────────────────────────────────────────────────────────────────────────
# Settings Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSettings:
    """Test system settings features."""
    
    def test_settings_page_loads(self, authenticated_page: Page, flask_server: str):
        """Settings page should load correctly."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        # Navigate to settings page
        navigate_to_page(authenticated_page, "settings")
        
        # Check page content
        settings_page = authenticated_page.locator("#page-settings")
        expect(settings_page).to_be_visible()
        
        # Header should be visible
        header = authenticated_page.locator("#page-settings .header h1")
        expect(header).to_contain_text("系统设置")
    
    def test_llm_config_form(self, authenticated_page: Page, flask_server: str):
        """LLM config form should have all fields."""
        safe_goto(authenticated_page, flask_server)
        wait_for_page_load(authenticated_page)
        
        navigate_to_page(authenticated_page, "settings")
        
        # Check form elements
        provider_select = authenticated_page.locator("#llm-provider")
        expect(provider_select).to_be_visible()
        
        api_key_input = authenticated_page.locator("#llm-api-key")
        expect(api_key_input).to_be_visible()
        
        model_input = authenticated_page.locator("#llm-model")
        expect(model_input).to_be_visible()
        
        save_btn = authenticated_page.locator("button:has-text('保存配置')")
        expect(save_btn).to_be_visible()
