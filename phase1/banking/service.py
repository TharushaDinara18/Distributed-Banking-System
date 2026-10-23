import threading
import uuid

from datetime import datetime, timezone
from decimal import Decimal

from banking.fees import calculate_transfer_fee


class BankingService:

    def __init__(self, storage):
        self.storage = storage

        # Load saved banking data
        self.accounts, self.transfers, self.requests = storage.load()

        # Prevent simultaneous balance updates
        self.lock = threading.Lock()

    def get_balance(self, account_id):

        # Get the latest account balance
        with self.lock:
            account = self.accounts.get(account_id)

            if account is None:
                return {
                    "success": False,
                    "message": "Account not found"
                }

            return {
                "success": True,
                "account_id": account_id,
                "balance": str(account["balance"])
            }

    def transfer_funds(
        self, sender_id, recipient_id,
        amount_text, reference, request_id
    ):

        # Check the request inputs
        values = (
            sender_id, recipient_id,
            amount_text, reference, request_id
        )

        if not all(isinstance(value, str) for value in values):
            return {
                "success": False,
                "message": "Invalid transfer request"
            }

        recipient_id = recipient_id.strip().upper()
        amount_text = amount_text.strip()
        reference = reference.strip()
        request_id = request_id.strip()

        if not request_id or len(request_id) > 100:
            return {
                "success": False,
                "message": "Invalid request ID"
            }

        if len(reference) > 100:
            return {
                "success": False,
                "message": "Reference is too long"
            }

        details = [
            sender_id, recipient_id,
            amount_text, reference
        ]

        # Keep checking and saving in one locked operation
        with self.lock:

            # Prevent processing the same request twice
            previous = self.requests.get(request_id)

            if previous:
                if previous["details"] != details:
                    return {
                        "success": False,
                        "message": "Request ID used for different transfer details"
                    }

                record = self.transfers[previous["transfer_id"]]
                return self._result(record, repeated=True)

            # Calculate the transfer fee
            fee = calculate_transfer_fee(amount_text)
            error = None

            if not fee["success"]:
                error = fee["message"]

            elif sender_id not in self.accounts:
                error = "Sender account not found"

            elif recipient_id not in self.accounts:
                error = "Recipient account not found"

            elif sender_id == recipient_id:
                error = "Cannot transfer to your own account"

            elif self.accounts[sender_id]["balance"] < Decimal(
                fee["total_debit"]
            ):
                error = "Insufficient funds"

            status = "FAILED" if error else "COMPLETED"

            # Copy balances before updating them
            new_accounts = {
                key: {"balance": value["balance"]}
                for key, value in self.accounts.items()
            }

            if not error:
                # Deduct amount and fee from sender
                new_accounts[sender_id]["balance"] -= Decimal(
                    fee["total_debit"]
                )

                # Credit the recipient
                new_accounts[recipient_id]["balance"] += Decimal(
                    fee["amount"]
                )

            # Create a transfer record
            transfer_id = uuid.uuid4().hex

            record = {
                "transfer_id": transfer_id,
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "amount": fee.get("amount", amount_text),
                "fee": fee.get("fee", "0.00"),
                "total_debit": fee.get("total_debit", "0.00"),
                "reference": reference,
                "status": status,
                "message": error or "Transfer completed",
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(timespec="seconds")
            }

            new_transfers = {
                **self.transfers,
                transfer_id: record
            }

            new_requests = {
                **self.requests,
                request_id: {
                    "details": details,
                    "transfer_id": transfer_id
                }
            }

            try:
                # Save balances and records together
                self.storage.save(
                    new_accounts,
                    new_transfers,
                    new_requests
                )

            except OSError:
                return {
                    "success": False,
                    "message": "Could not save transfer; check status before retrying"
                }

            # Update memory after saving succeeds
            self.accounts = new_accounts
            self.transfers = new_transfers
            self.requests = new_requests

            print("Transfer", status, transfer_id)

            return self._result(record)

    def get_transfer_status(self, account_id, transfer_id):

        with self.lock:
            record = self.transfers.get(transfer_id)

            # Only sender or recipient can view the transfer
            if record is None or account_id not in (
                record["sender_id"],
                record["recipient_id"]
            ):
                return {
                    "success": False,
                    "message": "Transfer not found"
                }

            result = self._result(record)
            result["success"] = True

            return result

    def _result(self, record, repeated=False):

        return {
            "success": record["status"] == "COMPLETED",
            "transfer_id": record["transfer_id"],
            "status": record["status"],
            "message": record["message"],
            "amount": record["amount"],
            "fee": record["fee"],
            "total_debit": record["total_debit"],
            "repeated": repeated
        }
