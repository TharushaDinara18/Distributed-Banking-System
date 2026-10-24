
import unittest
import tempfile
import threading
import sys

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

# Allow tests to import the banking package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from banking.auth import AuthenticationService
from banking.fees import calculate_transfer_fee
from banking.storage import BankStorage
from banking.service import BankingService


class FeeAndAuthenticationTests(unittest.TestCase):

    def test_fee_calculations(self):
        # Check the fee tiers, caps and rounding
        cases = {
            "2000": "0.00",
            "2000.01": "5.00",
            "4938": "12.35",
            "15000": "25.00",
            "25000": "31.25",
            "75000": "60.00",
            "120000": "72.00"
        }

        for amount, expected_fee in cases.items():
            with self.subTest(amount=amount):
                result = calculate_transfer_fee(amount)

                self.assertTrue(result["success"])
                self.assertEqual(result["fee"], expected_fee)

    def test_invalid_amounts(self):
        for amount in ["-100", "0", "abc", "50.123"]:
            with self.subTest(amount=amount):
                result = calculate_transfer_fee(amount)
                self.assertFalse(result["success"])

    def test_valid_login(self):
        auth = AuthenticationService()

        result = auth.login("kasun", "kasun123")

        self.assertTrue(result["success"])
        self.assertEqual(
            auth.get_username(result["token"]), "kasun"
        )

    def test_invalid_login(self):
        auth = AuthenticationService()

        result = auth.login("kasun", "wrongpassword")

        self.assertFalse(result["success"])


class BankingServiceTests(unittest.TestCase):

    def setUp(self):
        # Use separate temporary banking data for every test
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.storage = BankStorage()
        self.storage.data_file = (
            Path(self.temp_dir.name) / "bank_data.json"
        )

        self.service = BankingService(self.storage)

    def balance(self, account_id):
        result = self.service.get_balance(account_id)
        return Decimal(result["balance"])

    def transfer(
        self, amount="3000", recipient="ACC002",
        request_id="test-1", sender="ACC001"
    ):
        return self.service.transfer_funds(
            sender, recipient, amount, "", request_id
        )

    def test_successful_transfer(self):
        result = self.transfer()

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["fee"], "7.50")
        self.assertEqual(
            self.balance("ACC001"), Decimal("146992.50")
        )
        self.assertEqual(
            self.balance("ACC002"), Decimal("28000.00")
        )

    def test_insufficient_funds(self):
        result = self.transfer(amount="200000")

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["message"], "Insufficient funds")
        self.assertEqual(
            self.balance("ACC001"), Decimal("150000.00")
        )

    def test_invalid_recipient(self):
        result = self.transfer(recipient="ACC003")

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            self.balance("ACC001"), Decimal("150000.00")
        )

    def test_self_transfer(self):
        result = self.transfer(recipient="ACC001")

        self.assertEqual(result["status"], "FAILED")

    def test_duplicate_request(self):
        first = self.transfer()
        second = self.transfer()

        self.assertEqual(
            first["transfer_id"], second["transfer_id"]
        )
        self.assertTrue(second["repeated"])
        self.assertEqual(len(self.service.transfers), 1)
        self.assertEqual(
            self.balance("ACC001"), Decimal("146992.50")
        )

    def test_transfer_status(self):
        result = self.transfer()

        status = self.service.get_transfer_status(
            "ACC001", result["transfer_id"]
        )

        self.assertTrue(status["success"])
        self.assertEqual(status["status"], "COMPLETED")

    def test_json_persistence(self):
        result = self.transfer()

        # Reload the saved banking data
        restarted_service = BankingService(self.storage)

        balance = restarted_service.get_balance("ACC001")
        status = restarted_service.get_transfer_status(
            "ACC001", result["transfer_id"]
        )

        self.assertEqual(balance["balance"], "146992.50")
        self.assertEqual(status["status"], "COMPLETED")

    def test_concurrent_transfers(self):
        # Two requests try to spend the same balance
        barrier = threading.Barrier(2)

        def send(number):
            barrier.wait()
            return self.transfer(
                amount="100000",
                request_id=f"concurrent-{number}"
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(send, i) for i in range(2)]
            results = [f.result(timeout=20) for f in futures]

        statuses = [result["status"] for result in results]

        self.assertEqual(statuses.count("COMPLETED"), 1)
        self.assertEqual(statuses.count("FAILED"), 1)

        self.assertEqual(
            self.balance("ACC001"), Decimal("49940.00")
        )
        self.assertEqual(
            self.balance("ACC002"), Decimal("125000.00")
        )

    def test_concurrent_duplicate_requests(self):
        # Two threads send the same request ID together
        barrier = threading.Barrier(2)

        def send():
            barrier.wait()
            return self.transfer(
                amount="500",
                request_id="same-request"
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(send) for _ in range(2)]
            results = [f.result(timeout=20) for f in futures]

        self.assertEqual(
            results[0]["transfer_id"],
            results[1]["transfer_id"]
        )

        self.assertEqual(len(self.service.transfers), 1)

        self.assertEqual(
            self.balance("ACC001"), Decimal("149500.00")
        )
        self.assertEqual(
            self.balance("ACC002"), Decimal("25500.00")
        )


if __name__ == "__main__":
    unittest.main()
