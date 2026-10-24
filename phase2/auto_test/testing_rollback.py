import sys
import tempfile
from pathlib import Path
from contextlib import closing

# Import the Phase 2 database modules
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from database.storage import DatabaseStorage
from database.transactions import TransactionStorage


# Create a separate temporary database for testing
with tempfile.TemporaryDirectory() as temp_dir:

    storage = DatabaseStorage()
    storage.db_path = Path(temp_dir) / "test_bank.db"
    storage.initialize()

    # Save the original account balances
    before_kasun = storage.get_balance("ACC001")["balance"]
    before_nimal = storage.get_balance("ACC002")["balance"]

    # Simulate a database failure when crediting Nimal
    with closing(storage.connect()) as connection:
        with connection:
            connection.execute("""
                CREATE TRIGGER fail_credit
                BEFORE UPDATE OF balance_cents ON accounts
                WHEN NEW.account_id = 'ACC002'
                BEGIN
                    SELECT RAISE(ABORT, 'Simulated failure');
                END
            """)

    transactions = TransactionStorage(storage)

    # Attempt a transfer that should fail midway
    result = transactions.transfer(
        "ACC001",
        "ACC002",
        "3000",
        "7.50",
        "Rollback test",
        "rollback-test-001"
    )

    # Check balances after the failed transaction
    after_kasun = storage.get_balance("ACC001")["balance"]
    after_nimal = storage.get_balance("ACC002")["balance"]

    with closing(storage.connect()) as connection:
        transfer_count = connection.execute(
            "SELECT COUNT(*) FROM transfers"
        ).fetchone()[0]

        audit_count = connection.execute(
            "SELECT COUNT(*) FROM audit_logs"
        ).fetchone()[0]


    # Confirm all changes were rolled back
    assert result["success"] is False
    assert result["message"] == "Database transaction failed"
    assert before_kasun == after_kasun
    assert before_nimal == after_nimal
    assert transfer_count == 0
    assert audit_count == 0


    print("Transaction:", result["message"])
    print("Kasun balance:", after_kasun)
    print("Nimal balance:", after_nimal)
    print("Transfer records:", transfer_count)
    print("Audit records:", audit_count)
    print("Rollback test PASSED")

