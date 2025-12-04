import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add parent dir to path to import notifications
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from notifications.slack_notifier import SlackNotifier

class TestSlackNotifier(unittest.TestCase):

    def setUp(self):
        self.notifier = SlackNotifier()
        self.notifier.webhook_url = "https://hooks.slack.com/services/TEST/URL"

    @patch('requests.post')
    def test_send_message_success(self, mock_post):
        mock_post.return_value.status_code = 200
        result = self.notifier.send_message("Test message")
        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_send_message_failure_retry(self, mock_post):
        # Fail twice, succeed third time
        mock_post.side_effect = [
            Exception("Connection Error"),
            MagicMock(status_code=500),
            MagicMock(status_code=200)
        ]
        result = self.notifier.send_message("Test retry")
        self.assertTrue(result)
        self.assertEqual(mock_post.call_count, 3)

    def test_format_block(self):
        blocks = self.notifier._format_block("Hello", ":wave:")
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]['type'], 'section')
        self.assertIn(":wave: Hello", blocks[0]['text']['text'])

    @patch('notifications.slack_notifier.SlackNotifier.send_message')
    def test_notify_methods(self, mock_send):
        self.notifier.notify_info("Info")
        mock_send.assert_called_with("Info", blocks=unittest.mock.ANY, level="info")
        
        self.notifier.notify_error("Error")
        mock_send.assert_called_with("Error", blocks=unittest.mock.ANY, level="error")

if __name__ == '__main__':
    unittest.main()
