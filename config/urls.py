from django.urls import path

from customers.views import CustomerImportView, CustomerListView, HealthCheckView


urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("api/customers/", CustomerListView.as_view(), name="customer-list"),
    path(
        "api/imports/customers/",
        CustomerImportView.as_view(),
        name="customer-import",
    ),
]
