import Pyro5.api
import Pyro5.errors

from banking.auth import AuthenticationService
from banking.fees import calculate_transfer_fee

@Pyro5.api.expose

class BankApplicationServer:

    def __init__(self):

        # Initialize authentication
        self.auth = AuthenticationService()

        # Address of the Bank Database Server
        self.bdb_uri = "PYRO:bank.bdb@127.0.0.1:9091"

    def ping(self):
        return "BAS server is running"

    def login(self, username, password):

        # Authenticate the customer
        return self.auth.login(username, password)

    def get_balance(self, token):

        # Check if the user is logged in
        username = self.auth.get_username(token)

        if username is None:
            return {
                "success": False,
                "message": "Unauthorized request"
            }

        # Find the account linked to the customer
        account_id = self.auth.get_account_id(username)

        try:

            # Request the balance from BDB
            with Pyro5.api.Proxy(self.bdb_uri) as database:
                result = database.get_balance(account_id)

            if result["success"]:
                print("Balance requested by:", username)

            return result

        except (Pyro5.errors.PyroError, OSError):
            return {
                "success": False,
                "message": "Database server unavailable"
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

    def transfer_funds(
        self, token, recipient_id,
        amount_text, reference, request_id
    ):

        # Check if the user is logged in
        username = self.auth.get_username(token)

        if username is None:
            return {
                "success": False,
                "message": "Unauthorized request"
            }

        # Get the sender's account ID
        sender_id = self.auth.get_account_id(username)

        # Calculate and validate the transfer fee
        fee_result = calculate_transfer_fee(amount_text)

        if not fee_result["success"]:
            return fee_result

        try:

            # Send the transfer request to BDB
            with Pyro5.api.Proxy(self.bdb_uri) as database:
                result = database.transfer_funds(
                    sender_id,
                    recipient_id,
                    fee_result["amount"],
                    fee_result["fee"],
                    reference,
                    request_id
                )

            print("Transfer requested by:", username)

            return result

        except (Pyro5.errors.PyroError, OSError):
            return {
                "success": False,
                "message": (
                    "Database server unavailable. "
                    "Check the transfer status before retrying"
                )
            }

    def get_transfer_status(self, token, transfer_id):

        # Check if the user is logged in
        username = self.auth.get_username(token)

        if username is None:
            return {
                "success": False,
                "message": "Unauthorized request"
            }

        # Find the account linked to the customer
        account_id = self.auth.get_account_id(username)

        try:

            # Request the transfer status from BDB
            with Pyro5.api.Proxy(self.bdb_uri) as database:
                result = database.get_transfer_status(
                    account_id,
                    transfer_id
                )

            print("Transfer status requested by:", username)

            return result

        except (Pyro5.errors.PyroError, OSError):
            return {
                "success": False,
                "message": "Database server unavailable"
            }


def main():

    server = BankApplicationServer()

    # Start the Bank Application Server
    with Pyro5.api.Daemon(
        host="127.0.0.1",
        port=9090
    ) as daemon:

        uri = daemon.register(
            server,
            objectId="bank.bas"
        )

        print("Bank Application Server started")
        print("Server URI:", uri)

        # Wait for banking client requests
        daemon.requestLoop()


if __name__ == "__main__":
    main()

