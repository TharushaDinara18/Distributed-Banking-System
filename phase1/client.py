
import Pyro5.api
import Pyro5.errors


def main():
    uri = "PYRO:bank.bas@127.0.0.1:9090"

    try:
        with Pyro5.api.Proxy(uri) as bank:
            response = bank.ping()
            print(response)

    except Pyro5.errors.PyroError as error:
        print("Could not connect to the bank server")
        print(error)


if __name__ == "__main__":
    main()
