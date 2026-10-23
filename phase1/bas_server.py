
import Pyro5.api
import hashlib
import hmac
import secrets
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


@Pyro5.api.expose

class BankApplicationServer:

    def __init__(self):
        self.users = {}
        self.sessions = {}

        # Mock users for testing
        mock_users = {

            "kasun": {
                "full_name": "Kasun Perera",
                "password": "kasun123",
                "account_id": "ACC001"
            },


            "nimal": {
                "full_name": "Nimal Fernando",
                "password": "nimal123",
                "account_id": "ACC002"
            }
        }

        # Create mock account balances
        self.accounts = {
            "ACC001": {
                "balance": Decimal("150000.00")
            },
            "ACC002": {
                "balance": Decimal("25000.00")
            }
        }

        # Store salted password hashes
        for username, details in mock_users.items():
            salt = secrets.token_bytes(16)
            password_hash = self.hash_password(
                details["password"], salt
            )

            self.users[username] = {
                "full_name": details["full_name"],
                "account_id": details["account_id"],
                "salt": salt,
                "password_hash": password_hash
            }

    def hash_password(self, password, salt):
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt, 200000
        )

    def ping(self):
        return "BAS server is running"

    def login(self, username, password):

        username = username.strip().lower()
        user = self.users.get(username)

        # Check the username and password
        if user is None:
            print("Failed login attempt:", username)
            return {
                "success": False,
                "message": "Invalid credentials"
            }

        entered_hash = self.hash_password(
            password, user["salt"]
        )


        if not hmac.compare_digest(
            entered_hash, user["password_hash"]
        ):
            print("Failed login attempt:", username)
            return {
                "success": False,
                "message": "Invalid credentials"
            }

        # Generate a session token
        token = secrets.token_urlsafe(32)
        self.sessions[token] = username

        print("User logged in:", username)

        return {
            "success": True,
            "message": "Login successful",
            "full_name": user["full_name"],
            "token": token
        }

    def get_balance(self, token):

        # Check if the session token is valid
        username = self.sessions.get(token)

        if username is None:
            return {
                "success": False,
                "message": "Unauthorized request"
            }

        user = self.users[username]
        account_id = user["account_id"]
        account = self.accounts[account_id]

        print("Balance requested by:", username)

        return {
            "success": True,
            "account_id": account_id,
            "balance": str(account["balance"])
        }

    def calculate_fee(self, token, amount_text):

        # Check if the user is logged in
        username = self.sessions.get(token)

        if username is None:
            return {
                "success": False,
                "message": "Unauthorized request"
            }

        # Validate the transfer amount
        try:
            amount = Decimal(amount_text.strip())

            if not amount.is_finite():
                return {
                    "success": False,
                    "message": "Invalid transfer amount"
                }

            if amount <= Decimal("0.00"):
                return {
                    "success": False,
                    "message": "Amount must be greater than zero"
                }

            if amount.as_tuple().exponent < -2:
                return {
                    "success": False,
                    "message": "Amount must have at most 2 decimal places"
                }

            amount = amount.quantize(Decimal("0.01"))

        except (InvalidOperation, ValueError, AttributeError):
            return {
                "success": False,
                "message": "Invalid transfer amount"
            }

        # Select the fee tier based on the amount
        if amount <= Decimal("2000.00"):
            tier = "Free"
            rate = Decimal("0.00")
            cap = None

        elif amount <= Decimal("10000.00"):
            tier = "Entry"
            rate = Decimal("0.0025")
            cap = Decimal("20.00")

        elif amount <= Decimal("20000.00"):
            tier = "Mid"
            rate = Decimal("0.0020")
            cap = Decimal("25.00")

        elif amount <= Decimal("50000.00"):
            tier = "Upper-mid"
            rate = Decimal("0.00125")
            cap = Decimal("40.00")

        elif amount <= Decimal("100000.00"):
            tier = "High"
            rate = Decimal("0.0008")
            cap = Decimal("60.00")

        else:
            tier = "Top"
            rate = Decimal("0.0006")
            cap = Decimal("250.00")

        # Calculate the raw fee
        raw_fee = amount * rate

        # Round half-up to 2 decimal places
        fee = raw_fee.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
            
        )

        # Apply the maximum fee for the selected tier
        if cap is not None and fee > cap:
            fee = cap

        # The sender pays the amount and the fee
        total_debit = amount + fee

        print("Fee calculated for:", username)
        print("Transfer amount:", amount)
        print("Transfer fee:", fee)

        return {
            "success": True,
            "tier": tier,
            "amount": str(amount),
            "fee": str(fee),
            "total_debit": str(total_debit)
        }


def main():
    server = BankApplicationServer()

    # Start the application server
    with Pyro5.api.Daemon(
        host="127.0.0.1", port=9090
    ) as daemon:

        uri = daemon.register(
            server, objectId="bank.bas"
        )

        print("Bank Application Server started")
        print("Server URI:", uri)

        # Wait for client requests
        daemon.requestLoop()


if __name__ == "__main__":
    main()

