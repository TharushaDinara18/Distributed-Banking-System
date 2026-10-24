import sqlite3

from pathlib import Path
from contextlib import closing


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

        print("SQLite database initialized")


if __name__ == "__main__":
    storage = DatabaseStorage()
    storage.initialize()
