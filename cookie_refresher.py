import os
import subprocess
import random
import time
import platform
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, expect
load_dotenv()

def get_twitter_cookies(username, password):
    with sync_playwright() as p:
        # Configure browser launch options based on the operating system
        launch_options = {
            'user_data_dir': "./user_data",
            'headless': True,
            'viewport': {'width': 1280, 'height': 720},
            'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',  # Overcome limited /dev/shm in VMs
                '--disable-gpu',  # Disable GPU hardware acceleration
            ]
        }

        # Additional args for Linux systems
        if platform.system() == 'Linux':
            # Check if running on Ubuntu
            is_ubuntu = os.path.exists('/etc/lsb-release') and 'Ubuntu' in open('/etc/lsb-release').read()
            
            launch_options['args'].extend([
                '--disable-software-rasterizer',
                '--disable-extensions',
                '--single-process',  # Helpful for environments with limited resources
            ])
            
            if is_ubuntu:
                # Ubuntu-specific optimizations
                launch_options['args'].extend([
                    '--use-gl=egl',  # Better performance on Ubuntu
                    '--disable-features=VizDisplayCompositor',  # Avoid compositor issues
                    '--no-zygote',  # Better process management on Ubuntu
                ])
                
                # Set specific environment variable for Ubuntu
                os.environ['PLAYWRIGHT_BROWSERS_PATH'] = os.path.expanduser('~/.cache/ms-playwright')
            
        try:
            browser_context = p.chromium.launch_persistent_context(**launch_options)
            page = browser_context.new_page()
            
            # Add random delays to mimic human behavior
            def random_delay():
                time.sleep(random.uniform(1, 3))

            # Navigate to Twitter login page
            page.goto("https://twitter.com/i/flow/login", wait_until="networkidle")
            random_delay()
            
            # Try different selectors for username input
            selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[type="text"]'
            ]
            
            username_input = None
            for selector in selectors:
                if page.locator(selector).count() > 0:
                    username_input = page.locator(selector).first
                    break
            
            if not username_input:
                raise Exception("Could not find username input field")
            
            username_input.fill(username)
            random_delay()
            
            # Click the Next button
            next_button = page.get_by_role("button", name="Next")
            next_button.click()
            random_delay()
            
            # Wait for and fill in the password field
            password_input = page.locator('input[type="password"]').first
            password_input.wait_for(state="visible", timeout=5000)
            password_input.fill(password)
            random_delay()
            
            # Click the Log in button
            login_button = page.get_by_role("button", name="Log in")
            login_button.click()
            
            # Wait for navigation and cookie setting
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)
            
            cookies = browser_context.cookies()
            
            # Extract the required cookies from the list
            cookie_map = {cookie['name']: cookie['value'] for cookie in cookies}
            result = {
                "auth_token": cookie_map.get("auth_token", ""),
                "ct0": cookie_map.get("ct0", ""),
                "guest_id": cookie_map.get("guest_id", "")
            }
            
            # Validate cookies were actually obtained
            if not all(result.values()):
                raise Exception("Failed to obtain all required cookies")
                
            return result
            
        except Exception as e:
            print(f"Error during login process: {str(e)}")
            print(f"Current URL: {page.url}")
            raise
        finally:
            browser_context.close()

def redeploy_rsshub(username, password, twitter_cookie, project_id):
    # Build the deployment command with the new cookie string.
    command = [
        "gcloud", "run", "deploy", "rsshub",
        "--image", f"gcr.io/{project_id}/rsshub",
        "--platform", "managed",
        "--region", "us-central1",
        "--port", "1200",
        "--allow-unauthenticated",
        "--set-env-vars", f"TWITTER_USERNAME={username},TWITTER_PASSWORD={password},TWITTER_COOKIE={twitter_cookie},CACHE_TYPE=none"
    ]
    print("Running deployment command:", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        print("Redeployment successful.")
    else:
        print("Error in redeployment:")
        print(result.stdout)
        print(result.stderr)

def main():
    # Read credentials and project ID from environment variables
    username = os.getenv("TWITTER_USERNAME")
    password = os.getenv("TWITTER_PASSWORD")
    project_id = os.getenv("YOUR_PROJECT_ID")

    if not username or not password or not project_id:
        print("Missing TWITTER_USERNAME, TWITTER_PASSWORD, or YOUR_PROJECT_ID environment variables.")
        return

    print("Fetching new Twitter cookies...")
    cookies = get_twitter_cookies(username, password)
    
    # Build the TWITTER_COOKIE string
    twitter_cookie = f"auth_token={cookies['auth_token']}; ct0={cookies['ct0']}; guest_id={cookies['guest_id']}"
    print("New Twitter cookie:", twitter_cookie)
    
    print("Redeploying RSSHub with updated cookie...")
    redeploy_rsshub(username, password, twitter_cookie, project_id)

if __name__ == "__main__":
    main()
