
import Pyro5.api
import Pyro5.errors
import getpass
import uuid

from decimal import Decimal, InvalidOperation


def format_money(value):

    # Display money with commas and two decimal places
    try:
        amount = Decimal(value)
        return f"${amount:,.2f}"

    except (InvalidOperation, ValueError, TypeError):
        return str(value)


def show_balance(bank, token):

    # Request the account balance
    result = bank.get_balance(token)

    if result["success"]:

        print("\n=== Account Details ===")
        print("Account ID:", result["account_id"])
        print(
            "Current Balance:",
            format_money(result["balance"])
        )

    else:
        print(result["message"])

    return result["success"]


def show_fee(bank, token):

    print()
    print("=== Transfer Fee Calculator ===")

    amount = input("Enter Transfer Amount: $")

    # Request fee calculation from the server
    result = bank.calculate_fee(token, amount)

    if result["success"]:

        print()
        print("=== Fee Details ===")
        print("Fee Tier:", result["tier"])
        print(
            "Transfer Amount:",
            format_money(result["amount"])
        )
        print(
            "Transfer Fee:",
            format_money(result["fee"])
        )
        print(
            "Total Debit:",
            format_money(result["total_debit"])
        )

    else:
        print()
        print(result["message"])


def show_transfer(result):

    print()
    print("=== Transfer Result ===")

    # Display an error if the request was rejected
    if "transfer_id" not in result:
        print(result["message"])
        return

    if result.get("repeated"):
        print("This request was already processed")

    print("Transfer ID:", result["transfer_id"])
    print("Status:", result["status"])

    print(
        "Transfer Amount:",
        format_money(result["amount"])
    )

    print(
        "Transfer Fee:",
        format_money(result["fee"])
    )

    print(
        "Total Debit:",
        format_money(result["total_debit"])
    )

    print(result["message"])


def main():

    uri = "PYRO:bank.bas@127.0.0.1:9090"

    print("\n=== Distributed Banking System ===\n")

    username = input("Username: ")
    password = getpass.getpass("Password: ")

    try:

        # Connect to the application server
        with Pyro5.api.Proxy(uri) as bank:

            result = bank.login(username, password)

            print()
            print(result["message"])

            if not result["success"]:
                return

            print("Welcome,", result["full_name"])
            print("Authentication token received")

            # Save the token for banking operations
            token = result["token"]

            if not show_balance(bank, token):
                return

            last_request = None

            # Display the banking menu
            while True:

                print("\n=== Banking Menu ===\n")
                print("1. View Balance")
                print("2. Calculate Transfer Fee")
                print("3. Transfer Money")
                print("4. Check Transfer Status")
                print("5. Retry Last Transfer")
                print("0. Exit")

                choice = input("\nChoose an option: ").strip()

                if choice == "1":

                    # Display the latest account balance
                    show_balance(bank, token)

                elif choice == "2":

                    # Calculate a transfer fee
                    show_fee(bank, token)

                elif choice == "3":

                    print()
                    print("=== New Transfer ===")

                    recipient = input("Recipient Account ID: ")
                    amount = input("Transfer Amount: $")
                    reference = input("Reference (optional): ")

                    # Generate a unique ID for this request
                    request_id = uuid.uuid4().hex

                    last_request = (
                        recipient,
                        amount,
                        reference,
                        request_id
                    )

                    # Send the transfer request to the server
                    transfer_result = bank.transfer_funds(
                        token,
                        *last_request
                    )

                    show_transfer(transfer_result)

                elif choice == "4":

                    print()
                    print("=== Check Transfer Status ===")

                    transfer_id = input(
                        "Enter Transfer ID: "
                    ).strip()

                    # Request the transfer status
                    status_result = bank.get_transfer_status(
                        token,
                        transfer_id
                    )

                    if status_result["success"]:
                        show_transfer(status_result)

                    else:
                        print()
                        print(status_result["message"])

                elif choice == "5":

                    # Retry using the same request ID
                    if last_request is None:
                        print()
                        print("No previous transfer to retry")

                    else:
                        transfer_result = bank.transfer_funds(
                            token,
                            *last_request
                        )

                        show_transfer(transfer_result)

                elif choice == "0":

                    print()
                    print("Banking application closed")
                    break

                else:
                    print()
                    print("Invalid menu option")

    except Pyro5.errors.PyroError as error:

        print()
        print("Could not communicate with the bank server")
        print(error)

    except (KeyboardInterrupt, EOFError):
        print("\nBanking application closed")


if __name__ == "__main__":
    main()

