from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


def calculate_transfer_fee(amount_text):

    # Validate the transfer amount
    try:
        amount = Decimal(amount_text.strip())

        if not amount.is_finite():

            return {
                "success": False,
                "message": "Invalid transfer amount"
            }

        if amount <= Decimal("0.00"):

            return {
                "success": False,
                "message": "Amount must be greater than zero"
            }

        if amount.as_tuple().exponent < -2:

            return {
                "success": False,
                "message": "Amount must have at most 2 decimal places"
            }

        amount = amount.quantize(Decimal("0.01"))

    except (InvalidOperation, ValueError, AttributeError):
        return {
            "success": False,
            "message": "Invalid transfer amount"
        }

    # Select the fee tier based on the amount
    if amount <= Decimal("2000.00"):
        tier = "Free"
        rate = Decimal("0.00")
        cap = None

    elif amount <= Decimal("10000.00"):
        tier = "Entry"
        rate = Decimal("0.0025")
        cap = Decimal("20.00")

    elif amount <= Decimal("20000.00"):
        tier = "Mid"
        rate = Decimal("0.0020")
        cap = Decimal("25.00")

    elif amount <= Decimal("50000.00"):
        tier = "Upper-mid"
        rate = Decimal("0.00125")
        cap = Decimal("40.00")

    elif amount <= Decimal("100000.00"):
        tier = "High"
        rate = Decimal("0.0008")
        cap = Decimal("60.00")

    else:
        tier = "Top"
        rate = Decimal("0.0006")
        cap = Decimal("250.00")

    # Calculate the raw fee
    raw_fee = amount * rate

    # Round half-up to 2 decimal places
    fee = raw_fee.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    # Apply the maximum fee
    if cap is not None and fee > cap:
        fee = cap

    # The sender pays the amount and the fee
    total_debit = amount + fee


    return {
        "success": True,
        "tier": tier,
        "amount": str(amount),
        "fee": str(fee),
        "total_debit": str(total_debit)
    }

