
import sqlite3
import uuid

from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


class TransactionStorage:

    def __init__(self, storage):
        self.storage = storage

    def to_cents(self, value, allow_zero=False):

        # Validate money before saving it
        try:
            amount = Decimal(value.strip())

            if not amount.is_finite():
                raise ValueError()

            if amount < 0 or (amount == 0 and not allow_zero):
                raise ValueError()

            if amount.as_tuple().exponent < -2:
                raise ValueError()

            cents = int(amount * 100)

            if cents > 9000000000000000:
                raise ValueError()

            return cents

        except (InvalidOperation, ValueError, AttributeError):
            raise ValueError("Invalid amount or fee") from None

    def money(self, cents):
        return f"{Decimal(cents) / 100:.2f}"

    def result(self, record, repeated=False):

        # Prepare the transfer result
        return {
            "success": record["status"] == "COMPLETED",
            "transfer_id": record["transfer_id"],
            "status": record["status"],
            "message": record["message"],
            "amount": self.money(record["amount_cents"]),
            "fee": self.money(record["fee_cents"]),
            "total_debit": self.money(record["total_debit_cents"]),
            "repeated": repeated
        }

    def transfer(
        self, sender_id, recipient_id,
        amount_text, fee_text, reference, request_id
    ):

        # Check the request details
        values = (
            sender_id, recipient_id,
            amount_text, fee_text, reference, request_id
        )

        if not all(isinstance(value, str) for value in values):
            return {
                "success": False,
                "message": "Invalid request"
            }

        sender_id = sender_id.strip().upper()
        recipient_id = recipient_id.strip().upper()
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

        try:
            amount = self.to_cents(amount_text)
            fee = self.to_cents(fee_text, allow_zero=True)

        except ValueError as error:
            return {
                "success": False,
                "message": str(error)
            }

        total = amount + fee

        if total > 9000000000000000:
            return {
                "success": False,
                "message": "Amount too large"
            }

        # Process the transfer inside one SQLite transaction
        with closing(self.storage.connect()) as connection:
            connection.row_factory = sqlite3.Row

            try:
                # Lock the database for the transaction
                connection.execute("BEGIN IMMEDIATE")

                # Check if the request was already processed
                previous = connection.execute("""
                    SELECT * FROM transfers
                    WHERE request_id = ?
                """, (request_id,)).fetchone()

                if previous is not None:

                    same_request = (
                        previous["sender_id"] == sender_id
                        and previous["recipient_id"] == recipient_id
                        and previous["amount_cents"] == amount
                        and previous["fee_cents"] == fee
                        and previous["reference"] == reference
                    )

                    connection.commit()

                    if not same_request:
                        return {
                            "success": False,
                            "message": "Request ID already used"
                        }

                    return self.result(
                        previous,
                        repeated=True
                    )

                # Find the sender account
                sender = connection.execute("""
                    SELECT balance_cents FROM accounts
                    WHERE account_id = ?
                """, (sender_id,)).fetchone()

                # Find the recipient account
                recipient = connection.execute("""
                    SELECT balance_cents FROM accounts
                    WHERE account_id = ?
                """, (recipient_id,)).fetchone()

                # Validate the transfer
                if sender is None:
                    error = "Sender account not found"

                elif recipient is None:
                    error = "Recipient account not found"

                elif sender_id == recipient_id:
                    error = "Cannot transfer to your own account"

                elif sender["balance_cents"] < total:
                    error = "Insufficient funds"

                else:
                    error = None

                status = "FAILED" if error else "COMPLETED"
                message = error or "Transfer completed"

                if status == "COMPLETED":

                    # Deduct the amount and fee from the sender
                    connection.execute("""
                        UPDATE accounts
                        SET balance_cents = balance_cents - ?
                        WHERE account_id = ?
                    """, (total, sender_id))

                    # Credit the amount to the recipient
                    connection.execute("""
                        UPDATE accounts
                        SET balance_cents = balance_cents + ?
                        WHERE account_id = ?
                    """, (amount, recipient_id))

                # Generate the transfer ID and timestamp
                transfer_id = uuid.uuid4().hex

                created_at = datetime.now(
                    timezone.utc
                ).isoformat(timespec="seconds")

                # Save the transfer record
                connection.execute("""
                    INSERT INTO transfers (
                        transfer_id, request_id,
                        sender_id, recipient_id,
                        amount_text, amount_cents,
                        fee_cents, total_debit_cents,
                        reference, status, message, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transfer_id, request_id,
                    sender_id, recipient_id,
                    self.money(amount), amount,
                    fee, total, reference,
                    status, message, created_at
                ))

                # Save an audit record
                connection.execute("""
                    INSERT INTO audit_logs (
                        transfer_id, event, details, created_at
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    transfer_id,
                    status,
                    message,
                    created_at
                ))

                # Save all changes together
                connection.commit()

                record = {
                    "transfer_id": transfer_id,
                    "status": status,
                    "message": message,
                    "amount_cents": amount,
                    "fee_cents": fee,
                    "total_debit_cents": total
                }

                print("Transfer", status, transfer_id)

                return self.result(record)

            except sqlite3.Error:

                # Roll back changes if a database error occurs
                connection.rollback()

                return {
                    "success": False,
                    "message": "Database transaction failed"
                }

    def get_transfer_status(self, account_id, transfer_id):

        # Check the request details
        if not isinstance(account_id, str) or not isinstance(
            transfer_id, str
        ):
            return {
                "success": False,
                "message": "Invalid request"
            }

        try:
            # Find the transfer in SQLite
            with closing(self.storage.connect()) as connection:
                connection.row_factory = sqlite3.Row

                record = connection.execute("""
                    SELECT * FROM transfers
                    WHERE transfer_id = ?
                    AND (sender_id = ? OR recipient_id = ?)
                """, (
                    transfer_id.strip(),
                    account_id,
                    account_id
                )).fetchone()

        except sqlite3.Error:
            return {
                "success": False,
                "message": "Database query failed"
            }

        if record is None:
            return {
                "success": False,
                "message": "Transfer not found"
            }

        # Return the saved transfer details
        result = self.result(record)

        # A status lookup succeeds even for a failed transfer
        result["success"] = True

        return result
