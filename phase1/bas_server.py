import Pyro5.api

from banking.auth import AuthenticationService
from banking.fees import calculate_transfer_fee
from banking.storage import BankStorage
from banking.service import BankingService


@Pyro5.api.expose
class BankApplicationServer:

    def __init__(self):

        # Initialize authentication service
        self.auth = AuthenticationService()

        # Initialize banking data storage
        self.storage = BankStorage()

        # Initialize banking operations
        self.service = BankingService(self.storage)

    def ping(self):
        return "BAS server is running"

    def login(self, username, password):

        # Authenticate the user
        return self.auth.login(username, password)

    def get_balance(self, token):

        # Check if the user is logged in
        username = self.auth.get_username(token)

        if username is None:
            return {
                "success": False,
                "message": "Unauthorized request"
            }

        # Get the account linked to the user
        account_id = self.auth.get_account_id(username)

        result = self.service.get_balance(account_id)

        if result["success"]:
            print("Balance requested by:", username)

        return result

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

        # Get the sender account from the logged-in user
        sender_id = self.auth.get_account_id(username)

        # Process the transfer using the banking service
        return self.service.transfer_funds(
            sender_id,
            recipient_id,
            amount_text,
            reference,
            request_id
        )

    def get_transfer_status(self, token, transfer_id):

        # Check if the user is logged in
        username = self.auth.get_username(token)

        if username is None:
            return {
                "success": False,
                "message": "Unauthorized request"
            }

        # Get the account linked to the logged-in user
        account_id = self.auth.get_account_id(username)

        # Request the transfer status
        return self.service.get_transfer_status(
            account_id,
            transfer_id
        )


def main():
    server = BankApplicationServer()

    # Start the application server
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

        # Wait for client requests
        daemon.requestLoop()


if __name__ == "__main__":
    main()

