
import Pyro5.api
import Pyro5.errors
import getpass


def main():
    uri = "PYRO:bank.bas@127.0.0.1:9090"

    print("=== Distributed Banking System ===\n")

    username = input("Username: ")
    password = getpass.getpass("Password: ")

    try:

        # Connect to the application server
        with Pyro5.api.Proxy(uri) as bank:
            result = bank.login(username, password)

            print()
            print(result["message"])

            if result["success"]:
                print("Welcome,", result["full_name"])
                print("Authentication token received")

                # Save the token for future banking operations
                token = result["token"]

                # Request the account balance
                balance_result = bank.get_balance(token)

                if balance_result["success"]:
                    print()
                    print("=== Account Details ===")
                    print(
                        "Account ID:",
                        balance_result["account_id"]
                    )
                    print(
                        "Current Balance: $",
                        balance_result["balance"],
                        sep=""
                    )
                else:
                    print(balance_result["message"])

            print()

    except Pyro5.errors.PyroError as error:
        print("\nCould not connect to the bank server")
        print(error)


if __name__ == "__main__":
    main()
