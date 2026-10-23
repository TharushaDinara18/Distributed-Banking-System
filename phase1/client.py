
import Pyro5.api
import Pyro5.errors
import getpass


def main():
    uri = "PYRO:bank.bas@127.0.0.1:9090"

    print("=== Distributed Banking System ===")

    username = input("Username: ")
    password = getpass.getpass("Password: ")

    try:
        # Connect to the bank application server
        with Pyro5.api.Proxy(uri) as bank:
            result = bank.login(username, password)

            print(result["message"])

            if result["success"]:
                print("Welcome,", result["full_name"])
                print("Authentication token received")

                # Save the token for future banking operations
                token = result["token"]

    except Pyro5.errors.PyroError as error:
        print("Could not connect to the bank server")
        print(error)


if __name__ == "__main__":
    main()
