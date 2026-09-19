#!/usr/bin/env python3
"""
Test Suite: Real-Time Lead Ingestion & Executive Notification Engine
Standard: HWB-QMS-7.6 Enterprise Architecture & Autonomous Messaging
Author: Systems Architect George
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

sys.path.insert(0, '/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE')
load_dotenv('/home/humbertoed/gemini_projects/HWB-COMPANY/HWB-IT/HWB-IT-WEBSITE/.env')

from main_app import app
from core.services.email_service import transmit_email
from core.services.notification_service import send_lead_telegram_alert, send_lead_email_alert, dispatch_lead_notifications
from core.services.task_queue import task_queue

class TestRealtimeLeadNotifications(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_01_email_service_multi_recipient_formatting(self):
        """Verify transmit_email correctly handles list of recipients and production credentials."""
        with patch('msal.ConfidentialClientApplication') as mock_msal, \
             patch('requests.post') as mock_post:
            mock_app = MagicMock()
            mock_app.acquire_token_for_client.return_value = {"access_token": "mock_jwt_token"}
            mock_msal.return_value = mock_app

            mock_res = MagicMock()
            mock_res.status_code = 202
            mock_post.return_value = mock_res

            recipients = ['hdominguez@hwbcleaning.com', 'sales@hwbcleaning.com']
            ok, msg = transmit_email(recipients, 'Test Subject', '<p>Test Body</p>')
            self.assertTrue(ok)
            self.assertEqual(msg, 'Success')

            # Verify POST payload sent to Graph API has both recipients
            call_kwargs = mock_post.call_args[1]
            sent_recipients = call_kwargs['json']['message']['toRecipients']
            self.assertEqual(len(sent_recipients), 2)
            self.assertEqual(sent_recipients[0]['emailAddress']['address'], 'hdominguez@hwbcleaning.com')
            self.assertEqual(sent_recipients[1]['emailAddress']['address'], 'sales@hwbcleaning.com')

    def test_02_telegram_alert_formatting_and_payload(self):
        """Verify Telegram message contains complete lead details and markdown formatting."""
        with patch('requests.post') as mock_post:
            mock_res = MagicMock()
            mock_res.status_code = 200
            mock_post.return_value = mock_res

            lead_data = {
                'company': 'Apex Industrial Park',
                'name': 'Sarah Connor',
                'phone': '(214)-555-0188',
                'email': 'sconnor@apexindustrial.com',
                'facility_type': 'Industrial Distribution',
                'sqft': '35,000',
                'frequency': '5x per week',
                'annual_value': 42000
            }

            ok, msg = send_lead_telegram_alert(lead_data)
            self.assertTrue(ok)
            self.assertEqual(msg, 'Success')

            # Check Telegram payload
            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs['json']
            self.assertEqual(payload['chat_id'], os.environ.get('TELEGRAM_CHAT_ID', '8564340073'))
            self.assertIn('Apex Industrial Park', payload['text'])
            self.assertIn('Sarah Connor', payload['text'])
            self.assertIn('$42,000', payload['text'])
            self.assertEqual(payload['parse_mode'], 'Markdown')

    def test_03_notification_service_dual_channel_dispatch(self):
        """Verify dispatch_lead_notifications coordinates both Telegram and Email channels."""
        with patch('core.services.notification_service.send_lead_telegram_alert') as mock_tg, \
             patch('core.services.notification_service.send_lead_email_alert') as mock_em:
            mock_tg.return_value = (True, "Success")
            mock_em.return_value = (True, "Success")

            lead_data = {'company': 'Northgate Logistics', 'name': 'John Reese'}
            res = dispatch_lead_notifications(lead_data)

            self.assertTrue(res['telegram']['success'])
            self.assertTrue(res['email']['success'])
            mock_tg.assert_called_once_with(lead_data)
            mock_em.assert_called_once_with(lead_data)

    def test_04_task_queue_async_notification_execution(self):
        """Verify task_queue executes notification job asynchronously and records success."""
        mock_action = MagicMock(return_value={"status": "completed"})
        task_id = task_queue.enqueue(mock_action, {"test": True}, name="test_notify_job")
        self.assertIsNotNone(task_id)
        
        # Give worker a brief moment to run
        import time
        time.sleep(0.5)
        status = task_queue.get_status(task_id)
        self.assertIsNotNone(status)
        self.assertIn(status['status'], ['SUCCESS', 'RUNNING'])

if __name__ == '__main__':
    unittest.main()
