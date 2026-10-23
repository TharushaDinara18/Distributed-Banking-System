
import Pyro5.api

from decimal import Decimal
from banking.auth import AuthenticationService
from banking.fees import calculate_transfer_fee


@Pyro5.api.expose
class BankApplicationServer:

    def __init__(self):

        # Initialize the authentication service
        self.auth = AuthenticationService()

        # Create mock account balances
        self.accounts = {
            "ACC001": {
                "balance": Decimal("150000.00")
            },

            "ACC002": {
                "balance": Decimal("25000.00")
            }
        }

    def ping(self):
        return "BAS server is running"

    def login(self, username, password):

        # Authenticate the user using the auth module
        return self.auth.login(username, password)

    def get_balance(self, token):

        # Check if the session token is valid
        username = self.auth.get_username(token)

        if username is None:
            return {
                "success": False,
                "message": "Unauthorized request"
            }

        # Find the account linked to the user
        account_id = self.auth.get_account_id(username)
        account = self.accounts[account_id]

        print("Balance requested by:", username)

        return {
            "success": True,
            "account_id": account_id,
            "balance": str(account["balance"])
        }

    def calculate_fee(self, token, amount_text):

        # Check if the user is logged in
        username = self.auth.get_username(token)

        if username is None:
            return {
                "success": False,
                "message": "Unauthorized request"
            }

        # Calculate the fee using the fees module
        result = calculate_transfer_fee(amount_text)

        if result["success"]:
            print("Fee calculated for:", username)
            print("Transfer amount:", result["amount"])
            print("Transfer fee:", result["fee"])

        return result


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

