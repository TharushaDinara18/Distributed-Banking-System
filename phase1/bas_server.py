
import Pyro5.api


# Allow the client to access the server methods
@Pyro5.api.expose
class BankApplicationServer:

    def ping(self):
        return "BAS server is running"


def main():
    server = BankApplicationServer()

    # Start the server on port 9090
    with Pyro5.api.Daemon(host="127.0.0.1", port=9090) as daemon:
        uri = daemon.register(server, objectId="bank.bas")

        print("Bank Application Server started")
        print("Server URI:", uri)

        # Wait for requests from the client
        daemon.requestLoop()


if __name__ == "__main__":
    main()
