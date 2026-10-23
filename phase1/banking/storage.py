import json
import os
import tempfile

from decimal import Decimal
from pathlib import Path

class BankStorage:

    def __init__(self):

        # Location of the saved banking data
        self.data_file = (
            Path(__file__).resolve().parent.parent
            / "data"
            / "bank_data.json"
        )

    def load(self):

        # Create starting account data if no saved file exists
        if not self.data_file.exists():

            accounts = {
                "ACC001": {
                    "balance": Decimal("150000.00")
                },


                "ACC002": {
                    "balance": Decimal("25000.00")
                }
            }

            transfers = {}
            requests = {}

            self.save(accounts, transfers, requests)

            return accounts, transfers, requests

        # Load previously saved banking data
        with self.data_file.open("r", encoding="utf-8") as file:
            saved_data = json.load(file)

        accounts = {
            account_id: {
                "balance": Decimal(details["balance"])
            }

            for account_id, details in saved_data["accounts"].items()
        }

        transfers = saved_data["transfers"]
        requests = saved_data["requests"]

        return accounts, transfers, requests

    def save(self, accounts, transfers, requests):

        # Create the data folder if needed
        self.data_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        # Convert Decimal balances into strings for JSON
        saved_data = {
            "accounts": {
                account_id: {
                    "balance": str(details["balance"])
                }
                
                for account_id, details in accounts.items()
            },

            "transfers": transfers,
            "requests": requests
        }

        temp_path = None

        try:
            # Save to a temporary file first
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.data_file.parent,
                suffix=".tmp",
                delete=False
            ) as file:

                temp_path = file.name

                json.dump(saved_data, file, indent=2)

                file.flush()
                os.fsync(file.fileno())

            # Replace the saved file only after writing succeeds
            os.replace(temp_path, self.data_file)

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

