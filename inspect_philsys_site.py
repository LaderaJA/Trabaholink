#!/usr/bin/env python3
"""
Inspect PhilSys verification website to find correct selectors.
"""
from playwright.sync_api import sync_playwright
import time

def inspect_philsys_site():
    """Navigate to PhilSys site and inspect the page structure."""
    
    with sync_playwright() as p:
        # Launch browser in visible mode to see what's happening
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        print("🌐 Navigating to PhilSys verification portal...")
        try:
            page.goto('https://verify.philsys.gov.ph/', wait_until='networkidle', timeout=30000)
            print("✅ Page loaded successfully!")
        except Exception as e:
            print(f"❌ Failed to load page: {e}")
            browser.close()
            return
        
        # Wait for page to fully load
        time.sleep(3)
        
        # Take screenshot
        screenshot_path = '/tmp/philsys_inspect.png'
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"📸 Screenshot saved to: {screenshot_path}")
        
        # Get page title
        title = page.title()
        print(f"📄 Page title: {title}")
        
        # Get page URL
        url = page.url()
        print(f"🔗 Current URL: {url}")
        
        # Check for file upload inputs
        print("\n🔍 Looking for file upload inputs...")
        file_inputs = page.locator('input[type="file"]').all()
        print(f"   Found {len(file_inputs)} file input(s)")
        
        for i, input_elem in enumerate(file_inputs):
            try:
                input_id = input_elem.get_attribute('id')
                input_name = input_elem.get_attribute('name')
                input_class = input_elem.get_attribute('class')
                input_accept = input_elem.get_attribute('accept')
                
                print(f"\n   Input #{i+1}:")
                print(f"     ID: {input_id}")
                print(f"     Name: {input_name}")
                print(f"     Class: {input_class}")
                print(f"     Accept: {input_accept}")
            except Exception as e:
                print(f"     Error reading input #{i+1}: {e}")
        
        # Check for buttons
        print("\n🔍 Looking for buttons...")
        buttons = page.locator('button').all()
        print(f"   Found {len(buttons)} button(s)")
        
        for i, button in enumerate(buttons[:10]):  # Show first 10
            try:
                button_text = button.inner_text()
                button_id = button.get_attribute('id')
                button_class = button.get_attribute('class')
                button_type = button.get_attribute('type')
                
                if button_text.strip():
                    print(f"\n   Button #{i+1}:")
                    print(f"     Text: {button_text.strip()}")
                    print(f"     ID: {button_id}")
                    print(f"     Class: {button_class}")
                    print(f"     Type: {button_type}")
            except Exception as e:
                print(f"     Error reading button #{i+1}: {e}")
        
        # Get page HTML structure (first 5000 chars)
        print("\n📝 Page HTML structure (first 5000 chars):")
        html = page.content()
        print(html[:5000])
        
        # Save full HTML
        html_path = '/tmp/philsys_page.html'
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n💾 Full HTML saved to: {html_path}")
        
        print("\n⏸️  Browser will stay open for 30 seconds so you can inspect...")
        print("    Press Ctrl+C to close early")
        
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n⏹️  Closing browser...")
        
        browser.close()
        print("\n✅ Inspection complete!")
        print(f"\nCheck these files:")
        print(f"  - Screenshot: {screenshot_path}")
        print(f"  - HTML: {html_path}")

if __name__ == '__main__':
    inspect_philsys_site()
