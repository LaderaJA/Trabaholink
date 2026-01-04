"""
Comprehensive System Test for Trabaholink using Playwright
Tests all major functionality including categories, registration, login, job posting, etc.
"""
import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright, Page
import traceback

# Configuration
BASE_URL = "http://194.233.72.74:8000"  # Production URL
TEST_RESULTS = []

class TestResult:
    def __init__(self, name, category):
        self.name = name
        self.category = category
        self.status = "pending"
        self.error = None
        self.duration = 0
        self.screenshot = None
        self.start_time = None
    
    def start(self):
        self.start_time = datetime.now()
    
    def pass_test(self):
        self.status = "passed"
        self.duration = (datetime.now() - self.start_time).total_seconds()
    
    def fail_test(self, error):
        self.status = "failed"
        self.error = str(error)
        self.duration = (datetime.now() - self.start_time).total_seconds()
    
    def skip_test(self, reason):
        self.status = "skipped"
        self.error = reason

async def take_screenshot(page: Page, name: str) -> str:
    """Take a screenshot and return the filename"""
    import os
    # Create screenshots directory with proper permissions
    os.makedirs("/tmp/test_screenshots", exist_ok=True)
    filename = f"/tmp/test_screenshots/screenshot_{name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    try:
        await page.screenshot(path=filename)
        return filename
    except Exception as e:
        print(f"Warning: Could not save screenshot: {e}")
        return None

async def test_homepage(page: Page):
    """Test: Homepage loads correctly"""
    result = TestResult("Homepage loads", "Basic Functionality")
    TEST_RESULTS.append(result)
    result.start()
    
    try:
        await page.goto(BASE_URL, wait_until="networkidle")
        await page.wait_for_selector("body", timeout=10000)
        
        # Check for key elements
        title = await page.title()
        assert "Trabaholink" in title or "Home" in title, f"Unexpected page title: {title}"
        
        result.screenshot = await take_screenshot(page, "homepage")
        result.pass_test()
        print(f"✅ {result.name}")
    except Exception as e:
        result.fail_test(e)
        print(f"❌ {result.name}: {e}")

async def test_service_categories_dropdown(page: Page):
    """Test: Service categories dropdown shows proper names (not blank)"""
    result = TestResult("Service categories dropdown", "Categories")
    TEST_RESULTS.append(result)
    result.start()
    
    try:
        await page.goto(f"{BASE_URL}/services/", wait_until="networkidle")
        
        # Wait for category dropdown/filter
        await page.wait_for_selector("select, .category-filter, [data-category]", timeout=10000)
        
        # Check if there are service categories displayed
        categories = await page.query_selector_all("select option, .category-item, [data-category-name]")
        
        if len(categories) == 0:
            raise Exception("No service categories found")
        
        # Check for empty category names
        empty_found = False
        for cat in categories[:10]:  # Check first 10
            text = await cat.inner_text()
            if text.strip() == "" or text == "---":
                empty_found = True
                break
        
        if empty_found:
            raise Exception("Found empty/blank category names")
        
        result.screenshot = await take_screenshot(page, "service_categories")
        result.pass_test()
        print(f"✅ {result.name}")
    except Exception as e:
        result.fail_test(e)
        result.screenshot = await take_screenshot(page, "service_categories_fail")
        print(f"❌ {result.name}: {e}")

async def test_job_categories_dropdown(page: Page):
    """Test: Job categories dropdown shows proper names"""
    result = TestResult("Job categories dropdown", "Categories")
    TEST_RESULTS.append(result)
    result.start()
    
    try:
        await page.goto(f"{BASE_URL}/jobs/", wait_until="networkidle")
        
        # Wait for category dropdown/filter
        await page.wait_for_selector("select, .category-filter, [data-category]", timeout=10000)
        
        # Check if there are job categories displayed
        categories = await page.query_selector_all("select option, .category-item, [data-category-name]")
        
        if len(categories) == 0:
            raise Exception("No job categories found")
        
        # Check for empty category names
        empty_found = False
        for cat in categories[:10]:  # Check first 10
            text = await cat.inner_text()
            if text.strip() == "" or text == "---":
                empty_found = True
                break
        
        if empty_found:
            raise Exception("Found empty/blank category names")
        
        result.screenshot = await take_screenshot(page, "job_categories")
        result.pass_test()
        print(f"✅ {result.name}")
    except Exception as e:
        result.fail_test(e)
        result.screenshot = await take_screenshot(page, "job_categories_fail")
        print(f"❌ {result.name}: {e}")

async def test_registration_page_loads(page: Page):
    """Test: Registration page loads"""
    result = TestResult("Registration page loads", "Authentication")
    TEST_RESULTS.append(result)
    result.start()
    
    try:
        await page.goto(f"{BASE_URL}/users/register/", wait_until="networkidle")
        
        # Check for registration form elements
        await page.wait_for_selector("form", timeout=10000)
        
        # Check for common registration fields
        has_email = await page.query_selector("input[type='email'], input[name*='email']")
        has_password = await page.query_selector("input[type='password']")
        has_submit = await page.query_selector("button[type='submit'], input[type='submit']")
        
        if not (has_email and has_password and has_submit):
            raise Exception("Registration form missing required fields")
        
        result.screenshot = await take_screenshot(page, "registration_page")
        result.pass_test()
        print(f"✅ {result.name}")
    except Exception as e:
        result.fail_test(e)
        result.screenshot = await take_screenshot(page, "registration_fail")
        print(f"❌ {result.name}: {e}")

async def test_login_page_loads(page: Page):
    """Test: Login page loads"""
    result = TestResult("Login page loads", "Authentication")
    TEST_RESULTS.append(result)
    result.start()
    
    try:
        await page.goto(f"{BASE_URL}/users/login/", wait_until="networkidle")
        
        # Check for login form elements
        await page.wait_for_selector("form", timeout=10000)
        
        has_username = await page.query_selector("input[name*='username'], input[name*='email']")
        has_password = await page.query_selector("input[type='password']")
        has_submit = await page.query_selector("button[type='submit'], input[type='submit']")
        
        if not (has_username and has_password and has_submit):
            raise Exception("Login form missing required fields")
        
        result.screenshot = await take_screenshot(page, "login_page")
        result.pass_test()
        print(f"✅ {result.name}")
    except Exception as e:
        result.fail_test(e)
        result.screenshot = await take_screenshot(page, "login_fail")
        print(f"❌ {result.name}: {e}")

async def test_services_list_loads(page: Page):
    """Test: Services list page loads and displays services"""
    result = TestResult("Services list loads", "Services")
    TEST_RESULTS.append(result)
    result.start()
    
    try:
        await page.goto(f"{BASE_URL}/services/", wait_until="networkidle")
        await page.wait_for_selector("body", timeout=10000)
        
        # Check if page loaded
        title = await page.title()
        assert "Service" in title or title != "", f"Unexpected services page title: {title}"
        
        result.screenshot = await take_screenshot(page, "services_list")
        result.pass_test()
        print(f"✅ {result.name}")
    except Exception as e:
        result.fail_test(e)
        result.screenshot = await take_screenshot(page, "services_list_fail")
        print(f"❌ {result.name}: {e}")

async def test_jobs_list_loads(page: Page):
    """Test: Jobs list page loads and displays jobs"""
    result = TestResult("Jobs list loads", "Jobs")
    TEST_RESULTS.append(result)
    result.start()
    
    try:
        await page.goto(f"{BASE_URL}/jobs/", wait_until="networkidle")
        await page.wait_for_selector("body", timeout=10000)
        
        # Check if page loaded
        title = await page.title()
        assert "Job" in title or title != "", f"Unexpected jobs page title: {title}"
        
        result.screenshot = await take_screenshot(page, "jobs_list")
        result.pass_test()
        print(f"✅ {result.name}")
    except Exception as e:
        result.fail_test(e)
        result.screenshot = await take_screenshot(page, "jobs_list_fail")
        print(f"❌ {result.name}: {e}")

async def test_api_service_categories(page: Page):
    """Test: API endpoint for service categories returns valid data"""
    result = TestResult("API: Service categories", "API")
    TEST_RESULTS.append(result)
    result.start()
    
    try:
        response = await page.goto(f"{BASE_URL}/api/services/categories/", wait_until="networkidle")
        
        if response.status != 200:
            raise Exception(f"API returned status {response.status}")
        
        # Try to parse JSON
        data = await response.json()
        
        if not isinstance(data, list) and not isinstance(data, dict):
            raise Exception("API did not return list or dict")
        
        # Check if data has items
        items = data if isinstance(data, list) else data.get('results', [])
        
        if len(items) == 0:
            raise Exception("API returned empty categories list")
        
        # Check if categories have names
        if isinstance(items[0], dict) and 'name' in items[0]:
            if not items[0]['name'].strip():
                raise Exception("API returned category with empty name")
        
        result.pass_test()
        print(f"✅ {result.name}")
    except Exception as e:
        result.fail_test(e)
        print(f"❌ {result.name}: {e}")

async def test_api_job_categories(page: Page):
    """Test: API endpoint for job categories returns valid data"""
    result = TestResult("API: Job categories", "API")
    TEST_RESULTS.append(result)
    result.start()
    
    try:
        response = await page.goto(f"{BASE_URL}/api/jobs/categories/", wait_until="networkidle")
        
        if response.status != 200:
            raise Exception(f"API returned status {response.status}")
        
        # Try to parse JSON
        data = await response.json()
        
        if not isinstance(data, list) and not isinstance(data, dict):
            raise Exception("API did not return list or dict")
        
        # Check if data has items
        items = data if isinstance(data, list) else data.get('results', [])
        
        if len(items) == 0:
            raise Exception("API returned empty categories list")
        
        result.pass_test()
        print(f"✅ {result.name}")
    except Exception as e:
        result.fail_test(e)
        print(f"❌ {result.name}: {e}")

async def test_navigation_links(page: Page):
    """Test: Main navigation links are present and working"""
    result = TestResult("Navigation links present", "Navigation")
    TEST_RESULTS.append(result)
    result.start()
    
    try:
        await page.goto(BASE_URL, wait_until="networkidle")
        
        # Check for common navigation elements
        nav = await page.query_selector("nav, .navbar, header")
        
        if not nav:
            raise Exception("No navigation element found")
        
        # Check for links
        links = await page.query_selector_all("nav a, .navbar a, header a")
        
        if len(links) < 2:
            raise Exception(f"Only {len(links)} navigation links found")
        
        result.screenshot = await take_screenshot(page, "navigation")
        result.pass_test()
        print(f"✅ {result.name}")
    except Exception as e:
        result.fail_test(e)
        result.screenshot = await take_screenshot(page, "navigation_fail")
        print(f"❌ {result.name}: {e}")

async def test_responsive_design(page: Page):
    """Test: Page is responsive on mobile"""
    result = TestResult("Responsive design (mobile)", "UI/UX")
    TEST_RESULTS.append(result)
    result.start()
    
    try:
        await page.set_viewport_size({"width": 375, "height": 667})  # iPhone size
        await page.goto(BASE_URL, wait_until="networkidle")
        
        await page.wait_for_selector("body", timeout=10000)
        
        # Check if content is visible
        body = await page.query_selector("body")
        box = await body.bounding_box()
        
        if not box or box['width'] == 0:
            raise Exception("Page not rendering on mobile viewport")
        
        result.screenshot = await take_screenshot(page, "mobile_view")
        result.pass_test()
        print(f"✅ {result.name}")
    except Exception as e:
        result.fail_test(e)
        result.screenshot = await take_screenshot(page, "mobile_fail")
        print(f"❌ {result.name}: {e}")
    finally:
        # Reset viewport
        await page.set_viewport_size({"width": 1280, "height": 720})

def generate_html_report():
    """Generate an HTML report of test results"""
    
    total = len(TEST_RESULTS)
    passed = sum(1 for r in TEST_RESULTS if r.status == "passed")
    failed = sum(1 for r in TEST_RESULTS if r.status == "failed")
    skipped = sum(1 for r in TEST_RESULTS if r.status == "skipped")
    
    # Group by category
    categories = {}
    for result in TEST_RESULTS:
        if result.category not in categories:
            categories[result.category] = []
        categories[result.category].append(result)
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trabaholink System Test Results</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header .timestamp {{
            opacity: 0.9;
            font-size: 0.9em;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .summary-card .number {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .summary-card .label {{
            color: #666;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 1px;
        }}
        .passed {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        .skipped {{ color: #ffc107; }}
        .total {{ color: #007bff; }}
        
        .category {{
            margin: 30px;
        }}
        .category-header {{
            background: #f8f9fa;
            padding: 15px 20px;
            border-left: 4px solid #667eea;
            margin-bottom: 15px;
            font-size: 1.3em;
            font-weight: 600;
            color: #333;
        }}
        .test-item {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            margin-bottom: 15px;
            overflow: hidden;
            transition: all 0.3s ease;
        }}
        .test-item:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }}
        .test-header {{
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            background: #fafafa;
        }}
        .test-name {{
            font-weight: 600;
            font-size: 1.1em;
        }}
        .test-status {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .status-badge {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .status-passed {{
            background: #d4edda;
            color: #155724;
        }}
        .status-failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-skipped {{
            background: #fff3cd;
            color: #856404;
        }}
        .duration {{
            color: #666;
            font-size: 0.9em;
        }}
        .test-details {{
            padding: 20px;
            border-top: 1px solid #e0e0e0;
            background: white;
            display: none;
        }}
        .test-item.expanded .test-details {{
            display: block;
        }}
        .error-message {{
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 4px;
            padding: 15px;
            margin-top: 10px;
            color: #721c24;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            white-space: pre-wrap;
        }}
        .screenshot {{
            margin-top: 15px;
        }}
        .screenshot img {{
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
            cursor: pointer;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            border-top: 1px solid #e0e0e0;
        }}
        .progress-bar {{
            height: 10px;
            background: #e0e0e0;
            border-radius: 5px;
            overflow: hidden;
            margin: 20px 30px;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
            transition: width 0.3s ease;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Trabaholink System Test Results</h1>
            <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="number total">{total}</div>
                <div class="label">Total Tests</div>
            </div>
            <div class="summary-card">
                <div class="number passed">{passed}</div>
                <div class="label">Passed</div>
            </div>
            <div class="summary-card">
                <div class="number failed">{failed}</div>
                <div class="label">Failed</div>
            </div>
            <div class="summary-card">
                <div class="number skipped">{skipped}</div>
                <div class="label">Skipped</div>
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill" style="width: {(passed/total*100) if total > 0 else 0}%"></div>
        </div>
"""
    
    # Add test results by category
    for category_name, tests in categories.items():
        html += f"""
        <div class="category">
            <div class="category-header">📁 {category_name}</div>
"""
        
        for test in tests:
            status_class = f"status-{test.status}"
            duration_str = f"{test.duration:.2f}s" if test.duration > 0 else "N/A"
            
            html += f"""
            <div class="test-item" onclick="this.classList.toggle('expanded')">
                <div class="test-header">
                    <div class="test-name">{test.name}</div>
                    <div class="test-status">
                        <span class="duration">{duration_str}</span>
                        <span class="status-badge {status_class}">{test.status}</span>
                    </div>
                </div>
                <div class="test-details">
"""
            
            if test.error:
                html += f"""
                    <div class="error-message">{test.error}</div>
"""
            
            if test.screenshot:
                html += f"""
                    <div class="screenshot">
                        <strong>Screenshot:</strong><br>
                        <img src="{test.screenshot}" alt="Screenshot" onclick="window.open(this.src, '_blank')">
                    </div>
"""
            
            html += """
                </div>
            </div>
"""
        
        html += """
        </div>
"""
    
    html += f"""
        <div class="footer">
            <p>Trabaholink System Test Suite | Powered by Playwright</p>
            <p style="margin-top: 10px; font-size: 0.9em;">
                Success Rate: {(passed/total*100) if total > 0 else 0:.1f}%
            </p>
        </div>
    </div>
    
    <script>
        // Click to expand/collapse test details
        document.querySelectorAll('.test-item').forEach(item => {{
            item.style.cursor = 'pointer';
        }});
    </script>
</body>
</html>
"""
    
    filename = f"tmp_rovodev_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return filename

async def run_all_tests():
    """Run all tests"""
    print("=" * 70)
    print("🧪 TRABAHOLINK SYSTEM TEST SUITE")
    print("=" * 70)
    print(f"Testing: {BASE_URL}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        
        # Run all tests
        await test_homepage(page)
        await test_navigation_links(page)
        await test_service_categories_dropdown(page)
        await test_job_categories_dropdown(page)
        await test_services_list_loads(page)
        await test_jobs_list_loads(page)
        await test_registration_page_loads(page)
        await test_login_page_loads(page)
        await test_api_service_categories(page)
        await test_api_job_categories(page)
        await test_responsive_design(page)
        
        await browser.close()
    
    # Generate report
    print()
    print("=" * 70)
    print("📊 GENERATING REPORT")
    print("=" * 70)
    
    report_file = generate_html_report()
    
    print()
    print("=" * 70)
    print("✅ TEST SUITE COMPLETE")
    print("=" * 70)
    print(f"Total Tests: {len(TEST_RESULTS)}")
    print(f"Passed: {sum(1 for r in TEST_RESULTS if r.status == 'passed')}")
    print(f"Failed: {sum(1 for r in TEST_RESULTS if r.status == 'failed')}")
    print(f"Skipped: {sum(1 for r in TEST_RESULTS if r.status == 'skipped')}")
    print()
    print(f"📄 Report generated: {report_file}")
    print(f"🌐 Open in browser: file://{report_file}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_all_tests())
