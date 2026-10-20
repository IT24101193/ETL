import csv
import io

from django.db import transaction
from rest_framework.exceptions import ValidationError

from customers.models import Customer
from customers.serializers import CustomerImportSerializer


REQUIRED_COLUMNS = {"name", "email"}
OPTIONAL_COLUMNS = {"phone", "company"}
ALLOWED_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS


def import_customers(csv_content):
    reader = csv.DictReader(io.StringIO(csv_content), strict=True)
    headers = reader.fieldnames
    if not headers:
        raise ValidationError({"file": "The CSV file must include a header row."})
    if len(headers) != len(set(headers)):
        raise ValidationError({"file": "The CSV file contains duplicate column names."})
    missing = sorted(REQUIRED_COLUMNS - set(headers))
    unknown = sorted(set(headers) - ALLOWED_COLUMNS)
    if missing or unknown:
        errors = {}
        if missing:
            errors["missing_columns"] = missing
        if unknown:
            errors["unknown_columns"] = unknown
        raise ValidationError({"file": errors})

    valid_rows = []
    row_errors = []
    try:
        for row_number, row in enumerate(reader, start=2):
            if None in row:
                row_errors.append({row_number: {"row": "Too many values for the header."}})
                continue
            if all(not (value or "").strip() for value in row.values()):
                continue

            data = {column: (row.get(column) or "").strip() for column in ALLOWED_COLUMNS}
            data["email"] = data["email"].casefold()
            serializer = CustomerImportSerializer(data=data)
            if serializer.is_valid():
                valid_rows.append(serializer.validated_data)
            else:
                row_errors.append({row_number: serializer.errors})
    except csv.Error as error:
        raise ValidationError({"file": f"Invalid CSV format: {error}"}) from error

    if row_errors:
        raise ValidationError({"rows": row_errors})
    if not valid_rows:
        raise ValidationError({"file": "The CSV file does not contain any customer rows."})

    seen_emails = set()
    for row in valid_rows:
        if row["email"] in seen_emails:
            raise ValidationError(
                {"rows": "The CSV file contains duplicate email addresses."}
            )
        seen_emails.add(row["email"])

    created = 0
    updated = 0
    with transaction.atomic():
        for row in valid_rows:
            _, was_created = Customer.objects.update_or_create(
                email=row["email"],
                defaults={
                    "name": row["name"],
                    "phone": row["phone"],
                    "company": row["company"],
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

    return {"created": created, "updated": updated, "total": len(valid_rows)}
