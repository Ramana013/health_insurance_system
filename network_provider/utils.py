# network_provider/utils.py
import re


def convert_to_int(amount):
    """
    Convert various amount formats to integer.
    Handles:
    - Strings with commas (₹3,00,000 or 300,000)
    - Strings with decimals (500000.00 or 5,00,000.50)
    - Strings with "Lakh" or "L" (5 Lakh, 7L)
    - Integers (500000)
    - Floats (500000.0)
    - None or empty values
    """
    if amount is None:
        return 0

    if isinstance(amount, int):
        return amount

    if isinstance(amount, float):
        return int(amount)

    if isinstance(amount, str):
        # Handle "Lakh" and "L" notation
        amount = amount.upper()

        # Check for Lakh notation
        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(LAKH|L)', amount)
        if lakh_match:
            lakh_value = float(lakh_match.group(1))
            return int(lakh_value * 100000)

        # Check for "Cr" or "Crore" notation
        crore_match = re.search(r'(\d+(?:\.\d+)?)\s*(CRORE|CR)', amount)
        if crore_match:
            crore_value = float(crore_match.group(1))
            return int(crore_value * 10000000)

        # Remove all non-numeric characters except decimal point and minus sign
        clean_str = re.sub(r'[^\d.-]', '', amount.replace(',', ''))

        if not clean_str:
            return 0

        try:
            return int(float(clean_str))
        except (ValueError, TypeError):
            return 0

    return 0


def get_policy_coverage_amount(policy):
    """
    Find coverage amount from policy object.
    Checks multiple possible field names.
    """
    possible_coverage_fields = [
        'coverage_limit', 'coverage_amount', 'sum_insured',
        'limit', 'insured_amount', 'total_coverage', 'amount',
        'max_coverage', 'coverage'
    ]

    for field in possible_coverage_fields:
        if hasattr(policy, field):
            field_value = getattr(policy, field)
            if field_value not in [None, '', 0]:
                # Convert to integer using our conversion function
                return convert_to_int(str(field_value))

    return 0