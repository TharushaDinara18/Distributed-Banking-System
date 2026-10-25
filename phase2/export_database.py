import csv
import sqlite3

from pathlib import Path

def main():

    # Locate the SQLite database
    base_path = Path(__file__).resolve().parent
    database_path = base_path / "data" / "bank.db"
    export_path = base_path / "exports"

    if not database_path.exists():
        print("Database file not found")
        return

    # Create the exports folder
    export_path.mkdir(exist_ok=True)

    # Select the tables to export
    tables = {
        "accounts": """
            SELECT * FROM accounts
        """,

        "users": """
            SELECT username, full_name, account_id
            FROM users
        """,

        "transfers": """
            SELECT * FROM transfers
        """,

        "audit_logs": """
            SELECT * FROM audit_logs
        """
    }

    with sqlite3.connect(database_path) as connection:

        for table_name, query in tables.items():

            # Read the table records
            cursor = connection.execute(query)

            columns = [
                column[0]
                for column in cursor.description
            ]

            records = cursor.fetchall()

            # Save the records in CSV format
            file_path = export_path / f"{table_name}.csv"

            with open(
                file_path,
                "w",
                newline="",
                encoding="utf-8"
            ) as file:

                writer = csv.writer(file)
                writer.writerow(columns)
                writer.writerows(records)

            print(
                f"Exported {table_name}: "
                f"{len(records)} records"
            )

    print("\nDatabase export completed")


if __name__ == "__main__":
    main()

