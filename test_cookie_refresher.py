import unittest
from unittest.mock import MagicMock, patch
from cookie_refresher import get_twitter_cookies, redeploy_rsshub
import os
from dotenv import load_dotenv

class TestCookieRefresher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv()
        cls.username = os.getenv("TWITTER_USERNAME")
        cls.password = os.getenv("TWITTER_PASSWORD")
        cls.project_id = os.getenv("YOUR_PROJECT_ID")
        
        if not cls.username or not cls.password or not cls.project_id:
            raise ValueError("Please set TWITTER_USERNAME, TWITTER_PASSWORD, and YOUR_PROJECT_ID in your .env file")

    def test_cookie_extraction_and_deployment(self):
        """Test that we can successfully extract cookies and deploy to Cloud Run"""
        # First get the cookies
        cookies = get_twitter_cookies(self.username, self.password)
        
        # Check if all required cookies are present
        self.assertIn('auth_token', cookies)
        self.assertIn('ct0', cookies)
        self.assertIn('guest_id', cookies)
        
        # Check if cookies are non-empty strings
        self.assertIsInstance(cookies['auth_token'], str)
        self.assertIsInstance(cookies['ct0'], str)
        self.assertIsInstance(cookies['guest_id'], str)
        
        self.assertNotEqual(cookies['auth_token'], '')
        self.assertNotEqual(cookies['ct0'], '')
        self.assertNotEqual(cookies['guest_id'], '')
        
        print("\nExtracted cookies:")
        print(f"auth_token: {cookies['auth_token'][:10]}...")
        print(f"ct0: {cookies['ct0'][:10]}...")
        print(f"guest_id: {cookies['guest_id'][:10]}...")

        # Build the cookie string
        twitter_cookie = f"auth_token={cookies['auth_token']}; ct0={cookies['ct0']}; guest_id={cookies['guest_id']}"
        
        print("\nDeploying to Cloud Run with new cookies...")
        # Now deploy to Cloud Run
        redeploy_rsshub(
            username=self.username,
            password=self.password,
            twitter_cookie=twitter_cookie,
            project_id=self.project_id
        )

if __name__ == '__main__':
    unittest.main() 