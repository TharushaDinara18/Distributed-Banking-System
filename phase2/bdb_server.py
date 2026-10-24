
import Pyro5.api

from database.storage import DatabaseStorage


@Pyro5.api.expose
class BankDatabaseServer:

    def __init__(self):

        # Initialize the SQLite database
        self.storage = DatabaseStorage()
        self.storage.initialize()

    def ping(self):
        return "BDB server is running"

    def get_balance(self, account_id):

        # Request the account balance from SQLite
        return self.storage.get_balance(account_id)


def main():

    server = BankDatabaseServer()

    # Start the Bank Database Server
    with Pyro5.api.Daemon(
        host="127.0.0.1",
        port=9091
    ) as daemon:

        uri = daemon.register(
            server,
            objectId="bank.bdb"
        )

        print("Bank Database Server started")
        print("Server URI:", uri)

        # Wait for remote requests
        daemon.requestLoop()


if __name__ == "__main__":
    main()
