# Distributed Banking System

## Project Overview

This project is a three-tier distributed banking system developed in Python for CSI3344 Distributed Systems Assignment 2.

The system uses Pyro5 for remote procedure calls and SQLite for persistent storage. It uses mock customer accounts and does not involve real banking transactions.

## System Components

- **Banking Client (BC):** Allows customers to log in, view balances, calculate transfer fees, transfer money and check transfer statuses.
- **Bank Application Server (BAS):** Manages authenticated sessions, validates requests, calculates fees and communicates with BDB.
- **Bank Database Server (BDB):** Manages SQLite data, processes atomic transfers and stores transaction and audit records.

## Requirements

- Python 3.14
- Pyro5 5.17
- Windows PowerShell or Command Prompt

## Installation

1. Extract the project ZIP file.
2. Open PowerShell in the project root folder.
3. Create a Python virtual environment:

   `py -m venv .venv`

4. Install the required dependency:

   `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`

PowerShell virtual-environment activation is not required.

## Running the Application on One Computer

Open three separate terminals in the project root directory.

**Terminal 1 – Start BDB**

`.\.venv\Scripts\python.exe phase2\bdb_server.py`

BDB listens at `127.0.0.1:9091`. On first startup, it initializes the SQLite database and creates the mock accounts.

**Terminal 2 – Start BAS**

`.\.venv\Scripts\python.exe phase2\bas_server.py`

BAS listens at `127.0.0.1:9090` and connects to BDB.

**Terminal 3 – Start the Banking Client**

`.\.venv\Scripts\python.exe phase2\client.py`

Start BDB first, BAS second and the client last.

## Mock Customer Accounts

| Customer | Username | Password | Account ID | Initial balance |
| Kasun Perera | kasun | kasun123 | ACC001 | $150,000.00 |
| Nimal Fernando | nimal | nimal123 | ACC002 | $25,000.00 |

These credentials are for demonstration only. Account balances change when transfers are completed and are saved in SQLite.

## Banking Menu

1. View Balance – Retrieves the authenticated customer's current balance.
2. Calculate Transfer Fee – Calculates the fee and total debit.
3. Transfer Money – Sends money to another account.
4. Check Transfer Status – Retrieves a previous transfer using its transfer ID.
5. Retry Last Transfer – Resends the latest request with its original request ID.
0. Exit – Closes the banking client.

## Running on Two Computers

The intended deployment is:

- **Computer A:** Runs BDB and BAS.
- **Computer B:** Runs the banking client.
- Both computers connect through the same trusted private network.

On Computer A, find its local IPv4 address using `ipconfig`.

Change the BAS daemon host in `phase2/bas_server.py` from `127.0.0.1` to Computer A's private IPv4 address.

Keep BDB bound to `127.0.0.1:9091`.

On Computer B, install Python and Pyro5, then set the `uri` variable in `phase2/client.py` to:

`PYRO:bank.bas@<Computer-A-IP>:9090`

Replace `<Computer-A-IP>` with the server computer's actual private IPv4 address.

Start BDB and BAS on Computer A, then launch the client on Computer B. If necessary, configure the server's firewall to permit TCP port 9090 only from the trusted client computer.

Pyro5 connections are not encrypted by default. This demonstration should only be used on a trusted network with mock credentials. A production system would require transport encryption and stronger service-to-service authorization.

**Verification status:** The application has been tested locally. Physical two-computer deployment has not yet been verified.

## Automated Testing

Run the Phase 2 automated tests:

`.\.venv\Scripts\python.exe phase2\auto_test\testing_p2.py -v`

Run the rollback test:

`.\.venv\Scripts\python.exe phase2\auto_test\testing_rollback.py`

The automated database tests use temporary SQLite databases so that existing banking records are not changed.

## Database Exports

Generate CSV exports using:

`.\.venv\Scripts\python.exe phase2\export_database.py`

The exported tables are saved inside `phase2/exports/`.

## Design Notes

- Banking operations use synchronous Pyro5 RPC.
- SQLite transactions ensure that transfer updates are committed together or rolled back on database failure.
- Unique request IDs prevent repeated processing of the same transfer.
- Passwords are verified against salted password hashes stored in SQLite.
- The banking client communicates with BAS and does not access SQLite directly.

The application is an educational prototype using mock accounts and is not intended for real-world banking use.