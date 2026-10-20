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
            b"name,email,phone,company\nAda Lovelace,ADA@example.com,123,Analytical\n"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"created": 1, "updated": 0, "total": 1})
        self.assertTrue(Customer.objects.filter(email="ada@example.com").exists())

    def test_reimport_updates_existing_customer(self):
        Customer.objects.create(name="Old Name", email="ada@example.com")

        response = self.upload(b"name,email\nAda Lovelace,ada@example.com\n")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"created": 0, "updated": 1, "total": 1})
        self.assertEqual(Customer.objects.get().name, "Ada Lovelace")

    def test_invalid_row_rejects_the_entire_import(self):
        response = self.upload(
            b"name,email\nAda Lovelace,ada@example.com\nGrace Hopper,not-an-email\n"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Customer.objects.count(), 0)

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

    def test_duplicate_email_in_file_is_rejected(self):
        response = self.upload(
            b"name,email\nAda Lovelace,ada@example.com\n"
            b"Grace Hopper,ada@example.com\n"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Customer.objects.count(), 0)


class CustomerListTests(TestCase):
    def test_list_customers(self):
        Customer.objects.create(name="Ada Lovelace", email="ada@example.com")

        response = APIClient().get("/api/customers/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["email"], "ada@example.com")
