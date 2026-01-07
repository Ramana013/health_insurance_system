# import_policies.py

import os
import django
import re
from decimal import Decimal

# Configure Django settings environment
# NOTE: Replace 'your_project_name.settings' with the actual path to your settings file
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_insurance.settings')
django.setup()

# Import the model and data
from policy.models import Policy
from policies_data import SAMPLE_POLICIES  # Assuming policies_data.py is accessible


def clean_premium(premium_str):
    """
    Cleans the premium string by removing non-numeric characters
    (like ',', '/-', and currency symbols) and converts it to a Decimal.
    """
    # Remove commas, slashes, hyphens, and any non-digit/non-dot characters
    cleaned_str = re.sub(r'[^\d.]', '', premium_str)

    # Check if the result is empty or not a valid number
    if not cleaned_str:
        return Decimal('0.00')

    # Convert to Decimal
    return Decimal(cleaned_str)


def import_sample_policies():
    """Imports the sample policies into the Policy model."""
    print("Starting policy import...")

    records_created = 0
    records_skipped = 0

    for policy_data in SAMPLE_POLICIES:
        try:
            # Clean and convert the premium string
            cleaned_premium = clean_premium(policy_data['premium'])

            # Use update_or_create to avoid duplicates based on policy_id
            policy, created = Policy.objects.update_or_create(
                policy_id=policy_data['id'],
                defaults={
                    'name': policy_data['name'],
                    'description': policy_data['description'],
                    'premium': cleaned_premium,  # Use the cleaned Decimal value
                    'coverage_limit': policy_data['coverage_limit'],
                    'validity': policy_data['validity'],
                    'is_active': True
                }
            )

            if created:
                records_created += 1
                print(f"  [CREATED] Policy: {policy.name}")
            else:
                # This happens if you run the script again and the policy_id already exists
                records_skipped += 1
                print(f"  [UPDATED] Policy: {policy.name}")

        except Exception as e:
            print(f"  [ERROR] Failed to import policy {policy_data.get('name', 'Unknown')}: {e}")

    print("-" * 30)
    print(f"Import finished. Created: {records_created}, Updated: {records_skipped}.")
    print("Run 'python manage.py runserver' to view the changes.")


if __name__ == '__main__':
    # You must have run 'python manage.py makemigrations policy' and
    # 'python manage.py migrate' before running this script.
    import_sample_policies()