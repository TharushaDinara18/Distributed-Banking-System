import sqlite3
import hashlib
import hmac
import secrets

from pathlib import Path
from contextlib import closing
from decimal import Decimal

class DatabaseStorage:

    def __init__(self):

        # Set the location of the SQLite database
        self.db_path = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "bank.db"
        )

        # Create the data folder if it does not exist
        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

    def connect(self):

        # Connect to the SQLite database
        connection = sqlite3.connect(
            self.db_path,
            timeout=30
        )

        connection.execute("PRAGMA foreign_keys = ON")

        return connection

    def initialize(self):

        # Create the required banking tables
        with closing(self.connect()) as connection:
            with connection:

                # Store customer accounts and balances
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS accounts (
                        account_id TEXT PRIMARY KEY,
                        username TEXT NOT NULL UNIQUE,
                        balance_cents INTEGER NOT NULL
                            CHECK (balance_cents >= 0)
                    )
                """)

                # Store transfer information
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS transfers (
                        transfer_id TEXT PRIMARY KEY,
                        request_id TEXT NOT NULL UNIQUE,
                        sender_id TEXT NOT NULL,
                        recipient_id TEXT NOT NULL,
                        amount_text TEXT NOT NULL,
                        amount_cents INTEGER NOT NULL,
                        fee_cents INTEGER NOT NULL,
                        total_debit_cents INTEGER NOT NULL,
                        reference TEXT NOT NULL,
                        status TEXT NOT NULL
                            CHECK (status IN ('COMPLETED', 'FAILED')),
                        message TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)

                # Store banking audit records
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        transfer_id TEXT,
                        event TEXT NOT NULL,
                        details TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                """)

                # Create the two mock accounts
                mock_accounts = [
                    ("ACC001", "kasun", 15000000),
                    ("ACC002", "nimal", 2500000)
                ]

                connection.executemany("""
                    INSERT OR IGNORE INTO accounts
                    (account_id, username, balance_cents)
                    VALUES (?, ?, ?)
                """, mock_accounts)

                # Store mock users and password hashes
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        username TEXT PRIMARY KEY,
                        full_name TEXT NOT NULL,
                        account_id TEXT NOT NULL UNIQUE,
                        salt_hex TEXT NOT NULL,
                        password_hash_hex TEXT NOT NULL,
                        FOREIGN KEY (account_id)
                            REFERENCES accounts(account_id)
                    )
                """)

                # Mock users for testing
                mock_users = [
                    (
                        "kasun",
                        "Kasun Perera",
                        "ACC001",
                        "kasun123"
                    ),
                    (
                        "nimal",
                        "Nimal Fernando",
                        "ACC002",
                        "nimal123"
                    )
                ]

                # Add users without replacing existing records
                for username, full_name, account_id, password in mock_users:

                    existing = connection.execute("""
                        SELECT username
                        FROM users
                        WHERE username = ?
                    """, (username,)).fetchone()

                    if existing is not None:
                        continue

                    # Generate a random salt
                    salt = secrets.token_bytes(16)

                    # Create a salted password hash
                    password_hash = hashlib.pbkdf2_hmac(
                        "sha256",
                        password.encode("utf-8"),
                        salt,
                        200000
                    )

                    # Save the user in SQLite
                    connection.execute("""
                        INSERT INTO users (
                            username,
                            full_name,
                            account_id,
                            salt_hex,
                            password_hash_hex
                        )
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        username,
                        full_name,
                        account_id,
                        salt.hex(),
                        password_hash.hex()
                    ))

        print("SQLite database initialized")

    def authenticate_user(self, username, password):

        # Validate the login details
        if not isinstance(username, str) or not isinstance(
            password, str
        ):
            return {
                "success": False,
                "message": "Invalid credentials"
            }

        username = username.strip().lower()

        # Find the user in SQLite
        with closing(self.connect()) as connection:
            user = connection.execute("""
                SELECT
                    full_name,
                    account_id,
                    salt_hex,
                    password_hash_hex
                FROM users
                WHERE username = ?
            """, (username,)).fetchone()

        if user is None:
            return {
                "success": False,
                "message": "Invalid credentials"
            }

        full_name, account_id, salt_hex, hash_hex = user

        # Hash the entered password using the saved salt
        salt = bytes.fromhex(salt_hex)

        entered_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            200000
        )

        saved_hash = bytes.fromhex(hash_hex)

        # Compare the password hashes
        if not hmac.compare_digest(
            entered_hash,
            saved_hash
        ):
            return {
                "success": False,
                "message": "Invalid credentials"
            }

        return {
            "success": True,
            "username": username,
            "full_name": full_name,
            "account_id": account_id
        }

    def get_balance(self, account_id):

        # Find the account in SQLite
        with closing(self.connect()) as connection:
            result = connection.execute(
                """
                SELECT balance_cents
                FROM accounts
                WHERE account_id = ?
                """,
                (account_id,)
            ).fetchone()

        if result is None:
            return {
                "success": False,
                "message": "Account not found"
            }

        # Convert cents into dollars
        balance = Decimal(result[0]) / Decimal("100")

        return {
            "success": True,
            "account_id": account_id,
            "balance": f"{balance:.2f}"
        }


if __name__ == "__main__":
    storage = DatabaseStorage()
    storage.initialize()
