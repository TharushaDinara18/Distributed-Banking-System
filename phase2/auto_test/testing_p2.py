import unittest
import tempfile
import sys
import threading

from pathlib import Path
from decimal import Decimal
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor


# Import the Phase 2 modules
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from banking.auth import AuthenticationService
from banking.fees import calculate_transfer_fee
from database.storage import DatabaseStorage
from database.transactions import TransactionStorage


class AuthenticationAndFeeTests(unittest.TestCase):

    def test_valid_login(self):
        auth = AuthenticationService()

        result = auth.login("kasun", "kasun123")

        self.assertTrue(result["success"])
        self.assertEqual(
            auth.get_username(result["token"]),
            "kasun"
        )

    def test_invalid_login(self):
        auth = AuthenticationService()

        result = auth.login("kasun", "wrongpassword")

        self.assertFalse(result["success"])

    def test_fee_calculations(self):

        # Test the fee tiers and their boundaries
        cases = {
            "2000": "0.00",
            "2000.01": "5.00",
            "4938": "12.35",
            "10000": "20.00",
            "15000": "25.00",
            "25000": "31.25",
            "50000": "40.00",
            "75000": "60.00",
            "100000": "60.00",
            "120000": "72.00",
            "500000": "250.00"
        }

        for amount, expected in cases.items():
            with self.subTest(amount=amount):
                result = calculate_transfer_fee(amount)

                self.assertTrue(result["success"])
                self.assertEqual(result["fee"], expected)

    def test_invalid_amounts(self):

        for amount in ["0", "-100", "abc", "123.456"]:
            with self.subTest(amount=amount):
                result = calculate_transfer_fee(amount)

                self.assertFalse(result["success"])


class DatabaseTests(unittest.TestCase):

    def setUp(self):

        # Create a temporary SQLite database
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.storage = DatabaseStorage()
        self.storage.db_path = (
            Path(self.temp_dir.name) / "test_bank.db"
        )

        self.storage.initialize()

        self.transactions = TransactionStorage(self.storage)

    def balance(self, account_id):

        result = self.storage.get_balance(account_id)

        return Decimal(result["balance"])

    def transfer(
        self,
        amount="3000",
        fee="7.50",
        recipient="ACC002",
        request_id="test-001"
    ):

        return self.transactions.transfer(
            "ACC001",
            recipient,
            amount,
            fee,
            "Automated test",
            request_id
        )

    def count_records(self, table):

        with closing(self.storage.connect()) as connection:
            return connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

    def test_initial_balances(self):

        self.assertEqual(
            self.balance("ACC001"),
            Decimal("150000.00")
        )

        self.assertEqual(
            self.balance("ACC002"),
            Decimal("25000.00")
        )

    def test_successful_transfer(self):

        result = self.transfer()

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["fee"], "7.50")

        self.assertEqual(
            self.balance("ACC001"),
            Decimal("146992.50")
        )

        self.assertEqual(
            self.balance("ACC002"),
            Decimal("28000.00")
        )

        self.assertEqual(self.count_records("transfers"), 1)
        self.assertEqual(self.count_records("audit_logs"), 1)

    def test_insufficient_funds(self):

        result = self.transfer(
            amount="200000",
            fee="120.00"
        )

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["message"],
            "Insufficient funds"
        )

        self.assertEqual(
            self.balance("ACC001"),
            Decimal("150000.00")
        )

    def test_invalid_recipient(self):

        result = self.transfer(recipient="ACC003")

        self.assertEqual(result["status"], "FAILED")

        self.assertEqual(
            result["message"],
            "Recipient account not found"
        )

    def test_self_transfer(self):

        result = self.transfer(recipient="ACC001")

        self.assertEqual(result["status"], "FAILED")

    def test_duplicate_request(self):

        first = self.transfer()
        second = self.transfer()

        self.assertEqual(
            first["transfer_id"],
            second["transfer_id"]
        )

        self.assertTrue(second["repeated"])

        self.assertEqual(self.count_records("transfers"), 1)
        self.assertEqual(self.count_records("audit_logs"), 1)

        self.assertEqual(
            self.balance("ACC001"),
            Decimal("146992.50")
        )

    def test_conflicting_request_id(self):

        first = self.transfer()

        # Reuse the ID with a different amount
        second = self.transfer(
            amount="4000",
            fee="10.00"
        )

        self.assertEqual(first["status"], "COMPLETED")
        self.assertFalse(second["success"])

        self.assertEqual(
            second["message"],
            "Request ID already used"
        )

        self.assertEqual(self.count_records("transfers"), 1)

    def test_transfer_status(self):

        result = self.transfer()

        status = self.transactions.get_transfer_status(
            "ACC001",
            result["transfer_id"]
        )

        self.assertTrue(status["success"])
        self.assertEqual(status["status"], "COMPLETED")

        # An unrelated account cannot see the transfer
        denied = self.transactions.get_transfer_status(
            "ACC003",
            result["transfer_id"]
        )

        self.assertFalse(denied["success"])

    def test_failed_transfer_status(self):

        result = self.transfer(
            amount="200000",
            fee="120.00"
        )

        status = self.transactions.get_transfer_status(
            "ACC001",
            result["transfer_id"]
        )

        self.assertTrue(status["success"])
        self.assertEqual(status["status"], "FAILED")

    def test_database_persistence(self):

        result = self.transfer()

        # Open the same database using another storage object
        restarted = DatabaseStorage()
        restarted.db_path = self.storage.db_path
        restarted.initialize()

        new_transactions = TransactionStorage(restarted)

        balance = restarted.get_balance("ACC001")

        status = new_transactions.get_transfer_status(
            "ACC001",
            result["transfer_id"]
        )

        self.assertEqual(balance["balance"], "146992.50")
        self.assertEqual(status["status"], "COMPLETED")

    def test_concurrent_transfers(self):

        # Two transfers try to use the same balance
        barrier = threading.Barrier(2)

        def send(number):
            barrier.wait()

            return self.transfer(
                amount="100000",
                fee="60.00",
                request_id=f"concurrent-{number}"
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(send, i)
                for i in range(2)
            ]

            results = [
                future.result(timeout=30)
                for future in futures
            ]

        statuses = [
            result["status"]
            for result in results
        ]

        self.assertEqual(statuses.count("COMPLETED"), 1)
        self.assertEqual(statuses.count("FAILED"), 1)

        self.assertEqual(
            self.balance("ACC001"),
            Decimal("49940.00")
        )

        self.assertEqual(
            self.balance("ACC002"),
            Decimal("125000.00")
        )

    def test_concurrent_duplicate_requests(self):

        # Two threads submit the same request ID
        barrier = threading.Barrier(2)

        def send():
            barrier.wait()

            return self.transfer(
                amount="500",
                fee="0.00",
                request_id="same-request"
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(send)
                for _ in range(2)
            ]

            results = [
                future.result(timeout=30)
                for future in futures
            ]

        self.assertEqual(
            results[0]["transfer_id"],
            results[1]["transfer_id"]
        )

        self.assertEqual(self.count_records("transfers"), 1)
        self.assertEqual(self.count_records("audit_logs"), 1)

        self.assertEqual(
            self.balance("ACC001"),
            Decimal("149500.00")
        )

        self.assertEqual(
            self.balance("ACC002"),
            Decimal("25500.00")
        )


if __name__ == "__main__":
    unittest.main()

