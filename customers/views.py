import csv
import io

from django.http import HttpResponse
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.models import Customer
from customers.serializers import CustomerSerializer
from customers.services import import_customers


MAX_UPLOAD_BYTES = 10 * 1024 * 1024


class HealthCheckView(APIView):
    def get(self, request):
        return Response({"status": "ok"})


class CustomerListView(generics.ListAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


class CustomerImportView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response(
                {"file": "Upload a CSV file using the 'file' field."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if uploaded_file.size > MAX_UPLOAD_BYTES:
            return Response(
                {"file": "The CSV file must be 10 MB or smaller."},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )
        try:
            csv_content = uploaded_file.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return Response(
                {"file": "The CSV file must use UTF-8 encoding."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = import_customers(csv_content)
        rejected_rows = result.pop("rejected_rows")
        columns = result.pop("columns")
        if rejected_rows:
            output = io.StringIO(newline="")
            writer = csv.writer(output)
            writer.writerow([*columns, "_row_number", "_error"])
            for rejected_row in rejected_rows:
                writer.writerow(
                    [
                        *rejected_row["values"],
                        rejected_row["row_number"],
                        rejected_row["error"],
                    ]
                )
            response = HttpResponse(
                output.getvalue(),
                content_type="text/csv; charset=utf-8",
            )
            response["Content-Disposition"] = (
                'attachment; filename="rejected_rows.csv"'
            )
            response["X-Import-Created"] = str(result["created"])
            response["X-Import-Updated"] = str(result["updated"])
            response["X-Import-Rejected"] = str(result["rejected"])
            response["X-Import-Total"] = str(result["total"])
            return response
        return Response(result, status=status.HTTP_200_OK)
