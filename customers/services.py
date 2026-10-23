import csv
import io

from django.db import transaction
from rest_framework.exceptions import ValidationError

from customers.models import Customer
from customers.serializers import CustomerImportSerializer


REQUIRED_COLUMNS = {"name", "email"}
OPTIONAL_COLUMNS = {"phone", "company"}
ALLOWED_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS
BATCH_SIZE = 1000


def _format_row_errors(errors):
    return "; ".join(
        f"{field}: {message}"
        for field, messages in errors.items()
        for message in messages
    )


def _save_valid_rows(rows):
    created = 0
    updated = 0
    for start in range(0, len(rows), BATCH_SIZE):
        with transaction.atomic():
            for row in rows[start : start + BATCH_SIZE]:
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
    return created, updated


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
    rejected_rows = []
    seen_emails = set()
    try:
        for row_number, row in enumerate(reader, start=2):
            original_values = [row.get(column) or "" for column in headers]
            if None in row:
                rejected_rows.append(
                    {
                        "row_number": row_number,
                        "values": original_values + row[None],
                        "error": "Row has more values than the header.",
                    }
                )
                continue
            if all(not (value or "").strip() for value in row.values()):
                continue

            data = {column: (row.get(column) or "").strip() for column in ALLOWED_COLUMNS}
            serializer = CustomerImportSerializer(data=data)
            if serializer.is_valid():
                normalized_row = serializer.validated_data
                if normalized_row["email"] in seen_emails:
                    rejected_rows.append(
                        {
                            "row_number": row_number,
                            "values": original_values,
                            "error": "Duplicate email in this file; first occurrence kept.",
                        }
                    )
                    continue
                seen_emails.add(normalized_row["email"])
                valid_rows.append(normalized_row)
            else:
                rejected_rows.append(
                    {
                        "row_number": row_number,
                        "values": original_values,
                        "error": _format_row_errors(serializer.errors),
                    }
                )
    except csv.Error as error:
        raise ValidationError({"file": f"Invalid CSV format: {error}"}) from error

    if not valid_rows and not rejected_rows:
        raise ValidationError({"file": "The CSV file does not contain any customer rows."})

    created, updated = _save_valid_rows(valid_rows)

    return {
        "created": created,
        "updated": updated,
        "rejected": len(rejected_rows),
        "total": len(valid_rows),
        "rejected_rows": rejected_rows,
        "columns": headers,
    }
