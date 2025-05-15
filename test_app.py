import unittest
from unittest.mock import patch, MagicMock
import app

class TestTwitterBot(unittest.TestCase):
    
    @patch('feedparser.parse')
    def test_fetch_tweet_entries(self, mock_parse):
        # Setup mock return value for feedparser.parse
        mock_entry = MagicMock()
        mock_entry.link = 'https://twitter.com/username/status/1234567890'
        mock_entry.title = 'Test Tweet Title'
        mock_entry.summary = 'Test Tweet Content'
        
        mock_feed = MagicMock()
        mock_feed.entries = [mock_entry]
        mock_parse.return_value = mock_feed
        
        # Call the function to test
        result = app.fetch_tweet_entries('fake_url')
        
        # Assert results
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], '1234567890')
        self.assertEqual(result[0]['title'], 'Test Tweet Title')
        self.assertEqual(result[0]['content'], 'Test Tweet Content')
    
    @patch('openai.ChatCompletion.create')
    def test_generate_reply(self, mock_create):
        # Setup mock return value for openai.ChatCompletion.create
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "This is a test reply"
        mock_create.return_value = mock_response
        
        # Call the function to test
        result = app.generate_reply('Test tweet text')
        
        # Assert results
        self.assertEqual(result, "This is a test reply")
        mock_create.assert_called_once()
    
    @patch('tweepy.API.update_status')
    def test_reply_to_tweet(self, mock_update_status):
        # Call the function to test
        app.reply_to_tweet('1234567890', 'Test reply message')
        
        # Assert that the API was called with correct parameters
        mock_update_status.assert_called_once_with(
            status='Test reply message',
            in_reply_to_status_id='1234567890',
            auto_populate_reply_metadata=True
        )
    
    @patch('app.fetch_tweet_entries')
    @patch('app.generate_reply')
    @patch('app.reply_to_tweet')
    def test_main_integration(self, mock_reply_to_tweet, mock_generate_reply, mock_fetch_entries):
        # Setup mocks
        mock_fetch_entries.return_value = [{
            'id': '1234567890',
            'title': 'Test Tweet Title',
            'content': 'Test Tweet Content'
        }]
        mock_generate_reply.return_value = 'Test reply message'
        
        # Run the main function
        with patch('app.__name__', '__main__'):
            exec(open('app.py').read())
        
        # Verify correct function calls
        mock_fetch_entries.assert_called_once()
        mock_generate_reply.assert_called_once_with('Test Tweet Title Test Tweet Content')
        mock_reply_to_tweet.assert_called_once_with('1234567890', 'Test reply message')

if __name__ == '__main__':
    unittest.main() 