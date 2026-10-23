
import Pyro5.api
import hashlib
import hmac
import secrets
from decimal import Decimal


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

