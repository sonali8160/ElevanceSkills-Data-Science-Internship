import unittest
from datetime import datetime, timedelta

from task6.multilingual_chat import (
    MultilingualChatbot,
    Task6Config
)


class TestTask6MultilingualChat(unittest.TestCase):

    def setUp(self):
        self.config = Task6Config(
            languages=[
                "english",
                "hindi",
                "marathi",
                "spanish"
            ],
            language_threshold=0.60,
            intent_threshold=0.60,
            context_messages=10,
            inactivity_minutes=30,
            restore_hours=24
        )

        self.bot = MultilingualChatbot(self.config)

        self.start = datetime(2026, 9, 26, 10, 0, 0)

    def test_english_message(self):
        result = self.bot.process_message(
            "S1",
            "C1",
            "Where is my order ORD12345?",
            self.start
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["language"], "english")
        self.assertIn("ORD12345", result["entities"]["order_ids"])

    def test_hindi_message(self):
        result = self.bot.process_message(
            "S2",
            "C2",
            "Mera order ORD12345 kab ayega?",
            self.start
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["language"], "hindi")

    def test_marathi_message(self):
        result = self.bot.process_message(
            "S3",
            "C3",
            "माझा ऑर्डर ORD12345 कुठे आहे?",
            self.start
        )

        self.assertEqual(result["status"], "success")

    def test_spanish_message(self):
        result = self.bot.process_message(
            "S4",
            "C4",
            "Quiero ayuda con mi pedido ORD12345",
            self.start
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["language"], "spanish")

    def test_mixed_language(self):
        result = self.bot.process_message(
            "S5",
            "C5",
            "Mera order ORD12345 where is it?",
            self.start
        )

        self.assertIn(
            result["status"],
            ["success", "clarification_required"]
        )

    def test_order_id_preserved(self):
        result = self.bot.process_message(
            "S6",
            "C6",
            "My order ORD98765 is delayed.",
            self.start
        )

        self.assertIn(
            "ORD98765",
            result["entities"]["order_ids"]
        )

    def test_date_preserved(self):
        result = self.bot.process_message(
            "S7",
            "C7",
            "Order ORD12345 was placed on 26/09/2026",
            self.start
        )

        self.assertIn(
            "26/09/2026",
            result["entities"]["dates"]
        )

    def test_product_code_preserved(self):
        result = self.bot.process_message(
            "S8",
            "C8",
            "Product SKU-AB123 has a problem.",
            self.start
        )

        self.assertIn(
            "SKU-AB123",
            result["entities"]["product_codes"]
        )

    def test_context_limit_ten_messages(self):
        for i in range(12):
            result = self.bot.process_message(
                "S9",
                "C9",
                f"My order ORD{i + 1000} has a delivery problem.",
                self.start + timedelta(minutes=i)
            )

        self.assertEqual(
            result["context_messages"],
            10
        )

    def test_sessions_are_isolated(self):
        self.bot.process_message(
            "SESSION_A",
            "CUSTOMER_A",
            "My order ORD11111 is delayed.",
            self.start
        )

        self.bot.process_message(
            "SESSION_B",
            "CUSTOMER_B",
            "My order ORD22222 is delayed.",
            self.start
        )

        session_a = self.bot.get_session("SESSION_A")
        session_b = self.bot.get_session("SESSION_B")

        self.assertNotEqual(
            session_a.messages[0].text,
            session_b.messages[0].text
        )

        self.assertIn(
            "ORD11111",
            session_a.messages[0].text
        )

        self.assertIn(
            "ORD22222",
            session_b.messages[0].text
        )

    def test_language_switching(self):
        r1 = self.bot.process_message(
            "S10",
            "C10",
            "Where is my order ORD12345?",
            self.start
        )

        r2 = self.bot.process_message(
            "S10",
            "C10",
            "Mera order ORD12345 kab ayega?",
            self.start + timedelta(minutes=2)
        )

        self.assertEqual(r1["status"], "success")
        self.assertEqual(r2["status"], "success")

        session = self.bot.get_session("S10")

        self.assertEqual(len(session.messages), 2)
        self.assertNotEqual(
            session.messages[0].language,
            session.messages[1].language
        )

    def test_spelling_error(self):
        result = self.bot.process_message(
            "S11",
            "C11",
            "Where is my ordr ORD12345?",
            self.start
        )

        self.assertEqual(result["status"], "success")

    def test_transliterated_input(self):
        result = self.bot.process_message(
            "S12",
            "C12",
            "Mera order ORD12345 kab ayega?",
            self.start
        )

        self.assertEqual(result["status"], "success")

    def test_multiple_requests(self):
        result = self.bot.process_message(
            "S13",
            "C13",
            "Where is my order ORD12345 and also I need a refund",
            self.start
        )

        self.assertEqual(result["status"], "success")
        self.assertGreaterEqual(
            len(result["requests"]),
            2
        )

    def test_corrected_information(self):
        result = self.bot.process_message(
            "S14",
            "C14",
            "Actually my order is ORD55555, not ORD44444.",
            self.start
        )

        self.assertTrue(
            result["corrected_information"]
        )

    def test_low_confidence_clarification(self):
        result = self.bot.process_message(
            "S15",
            "C15",
            "xyz abc qqq",
            self.start
        )

        self.assertEqual(
            result["status"],
            "clarification_required"
        )

    def test_session_expires_after_30_minutes(self):
        self.bot.process_message(
            "S16",
            "C16",
            "Where is my order ORD12345?",
            self.start
        )

        result = self.bot.process_message(
            "S16",
            "C16",
            "Where is my order ORD12345?",
            self.start + timedelta(minutes=31)
        )

        self.assertEqual(
            result["status"],
            "success"
        )

        self.assertIn(
            "S16",
            self.bot.sessions
        )

    def test_restore_within_24_hours(self):
        self.bot.process_message(
            "S17",
            "C17",
            "My order ORD12345 is delayed.",
            self.start
        )

        self.bot.end_session(
            "S17",
            self.start + timedelta(minutes=31)
        )

        restored = self.bot.restore_session(
            "S17",
            self.start + timedelta(hours=5)
        )

        self.assertIsNotNone(restored)
        self.assertTrue(restored.active)

    def test_new_session_after_24_hours(self):
        self.bot.process_message(
            "S18",
            "C18",
            "My order ORD12345 is delayed.",
            self.start
        )

        self.bot.end_session(
            "S18",
            self.start + timedelta(minutes=31)
        )

        restored = self.bot.restore_session(
            "S18",
            self.start + timedelta(hours=25)
        )

        self.assertIsNotNone(restored)
        self.assertEqual(
            len(restored.messages),
            0
        )

    def test_configurable_session_timing(self):
        config = Task6Config(
            inactivity_minutes=10,
            restore_hours=2
        )

        bot = MultilingualChatbot(config)

        bot.process_message(
            "S19",
            "C19",
            "Where is my order ORD12345?",
            self.start
        )

        bot.process_message(
            "S19",
            "C19",
            "Where is my order ORD12345?",
            self.start + timedelta(minutes=11)
        )

        self.assertIn(
            "S19",
            bot.sessions
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)