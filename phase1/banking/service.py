import threading
import uuid

from datetime import datetime, timezone
from decimal import Decimal

from banking.fees import calculate_transfer_fee


class BankingService:

    def __init__(self, storage):

        # Load saved banking data
        self.storage = storage

        self.accounts, self.transfers, self.requests = (
            self.storage.load()
        )

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

    def transfer_result(self, record, repeated=False):

        # Prepare the result returned to the client
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

    def transfer_funds(
        self, sender_id, recipient_id,
        amount_text, reference, request_id
    ):

        # Check the request details
        if not all(
            isinstance(value, str)
            for value in (
                sender_id, recipient_id,
                amount_text, reference, request_id
            )
        ):
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

        # Store the original request details for duplicate checking
        request_details = [
            sender_id,
            recipient_id,
            amount_text,
            reference
        ]

        with self.lock:

            # Check whether this request was already processed
            previous = self.requests.get(request_id)

            if previous is not None:

                if previous["details"] != request_details:
                    return {
                        "success": False,
                        "message": (
                            "Request ID already used "
                            "for different transfer details"
                        )
                    }

                transfer_id = previous["transfer_id"]
                record = self.transfers[transfer_id]

                return self.transfer_result(
                    record,
                    repeated=True
                )

            # Calculate the transfer fee
            fee_result = calculate_transfer_fee(amount_text)

            error = None

            if not fee_result["success"]:
                error = fee_result["message"]

            elif sender_id not in self.accounts:
                error = "Sender account not found"

            elif recipient_id not in self.accounts:
                error = "Recipient account not found"

            elif sender_id == recipient_id:
                error = "Cannot transfer to your own account"

            else:
                total_debit = Decimal(
                    fee_result["total_debit"]
                )

                # Check whether the sender has enough money
                sender_balance = self.accounts[
                    sender_id
                ]["balance"]

                if sender_balance < total_debit:
                    error = "Insufficient funds"

            # Decide the final transfer status
            if error is None:
                status = "COMPLETED"
                message = "Transfer completed"

            else:
                status = "FAILED"
                message = error

            # Copy balances before making any changes
            new_accounts = {
                account_id: {
                    "balance": account["balance"]
                }
                for account_id, account in self.accounts.items()
            }

            if status == "COMPLETED":

                amount = Decimal(
                    fee_result["amount"]
                )

                total_debit = Decimal(
                    fee_result["total_debit"]
                )

                # Deduct amount and fee from sender
                new_accounts[sender_id]["balance"] -= (
                    total_debit
                )

                # Add only the transfer amount to recipient
                new_accounts[recipient_id]["balance"] += (
                    amount
                )

            # Generate a unique transfer ID
            transfer_id = uuid.uuid4().hex

            # Create a record for the transfer
            record = {
                "transfer_id": transfer_id,
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "amount": (
                    fee_result["amount"]
                    if fee_result["success"]
                    else amount_text
                ),

                "fee": (
                    fee_result["fee"]
                    if fee_result["success"]
                    else "0.00"
                ),

                "total_debit": (
                    fee_result["total_debit"]
                    if fee_result["success"]
                    else "0.00"
                ),
                
                "reference": reference,
                "status": status,
                "message": message,
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(timespec="seconds")
            }

            # Prepare updated transfer records
            new_transfers = self.transfers.copy()
            new_transfers[transfer_id] = record

            # Save the request ID for duplicate protection
            new_requests = self.requests.copy()

            new_requests[request_id] = {
                "details": request_details,
                "transfer_id": transfer_id
            }

            try:

                # Save all banking changes together
                self.storage.save(
                    new_accounts,
                    new_transfers,
                    new_requests
                )

            except OSError:
                return {
                    "success": False,
                    "message": (
                        "Unable to save transfer. "
                        "Check its status before retrying"
                    )
                }

            # Update memory only after saving succeeds
            self.accounts = new_accounts
            self.transfers = new_transfers
            self.requests = new_requests

            print("Transfer:", transfer_id)
            print("Status:", status)
            print("Amount:", record["amount"])

            return self.transfer_result(record)

    def get_transfer_status(self, account_id, transfer_id):

        # Find an existing transfer
        with self.lock:
            record = self.transfers.get(transfer_id)

            if record is None:
                return {
                    "success": False,
                    "message": "Transfer not found"
                }

            # Allow only the sender or recipient to view it
            if account_id not in (
                record["sender_id"],
                record["recipient_id"]
            ):
                return {
                    "success": False,
                    "message": "Transfer not found"
                }

            result = self.transfer_result(record)

            # Status lookup succeeded even if the transfer failed
            result["success"] = True

            return result
