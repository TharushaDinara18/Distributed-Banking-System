
import Pyro5.api
import Pyro5.errors
import getpass
from decimal import Decimal


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

            if result["success"]:
                
                print("Welcome,", result["full_name"])
                print("Authentication token received")

                # Save the token for banking operations
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

                    balance = Decimal(
                        balance_result["balance"]
                    )

                    print(f"Current Balance: ${balance:,.2f}")

                else:
                    print(balance_result["message"])
                    return
                

                # Enter an amount to calculate the fee
                print()
                print("=== Transfer Fee Calculator ===")
                amount = input("Enter Transfer Amount: $")

                # Request fee calculation from the server
                fee_result = bank.calculate_fee(token, amount)

                if fee_result["success"]:

                    transfer_amount = Decimal(
                        fee_result["amount"]
                    )

                    fee = Decimal(
                        fee_result["fee"]
                    )

                    total_debit = Decimal(
                        fee_result["total_debit"]
                    )

                    print()
                    print("=== Fee Details ===")
                    print("Fee Tier:", fee_result["tier"])
                    print(
                        f"Transfer Amount: ${transfer_amount:,.2f}"
                    )
                    print(f"Transfer Fee: ${fee:,.2f}")
                    print(f"Total Debit: ${total_debit:,.2f}")

                else:
                    print()
                    print(fee_result["message"])

            print()

    except Pyro5.errors.PyroError as error:
        print("\nCould not connect to the bank server")
        print(error)


if __name__ == "__main__":
    main()

