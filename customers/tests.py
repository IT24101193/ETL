import csv
import io
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from customers.models import Customer


class CustomerImportTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def upload(self, content, filename="customers.csv"):
        return self.client.post(
            "/api/imports/customers/",
            {"file": SimpleUploadedFile(filename, content, content_type="text/csv")},
            format="multipart",
        )

    def test_import_creates_customers_and_normalizes_email(self):
        response = self.upload(
            b"name,email,phone,company\n"
            b"Ada Lovelace,ADA@example.com,1234567,Analytical\n"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "created": 1,
            "updated": 0,
            "rejected": 0,
            "total": 1,
        })
        self.assertTrue(Customer.objects.filter(email="ada@example.com").exists())

    def test_reimport_updates_existing_customer(self):
        Customer.objects.create(name="Old Name", email="ada@example.com")

        response = self.upload(b"name,email\nAda Lovelace,ada@example.com\n"        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "created": 0,
            "updated": 1,
            "rejected": 0,
            "total": 1,
        })
        self.assertEqual(Customer.objects.get().name, "Ada Lovelace")

    def test_invalid_row_is_reported_and_valid_rows_are_imported(self):
        response = self.upload(
            b"name,email\nAda Lovelace,ada@example.com\n"
            b"Grace Hopper,not-an-email\n"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="rejected_rows.csv"')
        self.assertEqual(response["X-Import-Created"], "1")
        self.assertEqual(response["X-Import-Rejected"], "1")
        self.assertEqual(Customer.objects.count(), 1)
        report_rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        self.assertEqual(report_rows[0]["_row_number"], "3")
        self.assertIn("email:", report_rows[0]["_error"])

    def test_missing_required_column_is_rejected(self):
        response = self.upload(b"name,phone\nAda Lovelace,123\n")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Customer.objects.count(), 0)

    def test_missing_file_is_rejected(self):
        response = self.client.post("/api/imports/customers/", {}, format="multipart")

        self.assertEqual(response.status_code, 400)

    def test_utf8_bom_is_supported(self):
        response = self.upload(
            b"\xef\xbb\xbfname,email\nAda Lovelace,ada@example.com\n"
        )

        self.assertEqual(response.status_code, 200)

    def test_duplicate_email_is_reported_and_other_rows_are_imported(self):
        response = self.upload(
            b"name,email\nAda Lovelace,ada@example.com\n"
            b"Grace Hopper, ADA@example.com \n"
            b"Margaret Hamilton,margaret@example.com\n"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Import-Created"], "2")
        self.assertEqual(response["X-Import-Rejected"], "1")
        self.assertEqual(Customer.objects.count(), 2)
        self.assertEqual(Customer.objects.get(email="ada@example.com").name, "Ada Lovelace")
        self.assertTrue(Customer.objects.filter(email="margaret@example.com").exists())
        report_rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        self.assertEqual(report_rows[0]["_row_number"], "3")
        self.assertIn("Duplicate email", report_rows[0]["_error"])

    def test_invalid_phone_row_is_rejected_without_blocking_valid_rows(self):
        response = self.upload(
            b"name,email,phone\nAda Lovelace,ada@example.com,0771234567\n"
            b"Grace Hopper,grace@example.com,phone123\n"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Import-Created"], "1")
        self.assertEqual(response["X-Import-Rejected"], "1")
        self.assertTrue(Customer.objects.filter(email="ada@example.com").exists())
        self.assertFalse(Customer.objects.filter(email="grace@example.com").exists())

    def test_blank_optional_phone_is_allowed(self):
        response = self.upload(b"name,email,phone\nAda Lovelace,ada@example.com,\n")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Customer.objects.filter(email="ada@example.com", phone="").exists())

    @patch("customers.services.BATCH_SIZE", 2)
    def test_valid_rows_are_saved_across_batches(self):
        response = self.upload(
            b"name,email\nAda,ada@example.com\nGrace,grace@example.com\n"
            b"Margaret,margaret@example.com\n"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created"], 3)
        self.assertEqual(Customer.objects.count(), 3)


class CustomerListTests(TestCase):
    def test_list_customers(self):
        Customer.objects.create(name="Ada Lovelace", email="ada@example.com")

        response = APIClient().get("/api/customers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["email"], "ada@example.com")
