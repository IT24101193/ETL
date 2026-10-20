from rest_framework import serializers

from customers.models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "email", "phone", "company", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CustomerImportSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, allow_blank=False)
    email = serializers.EmailField(max_length=254)
    phone = serializers.CharField(max_length=50, allow_blank=True, required=False)
    company = serializers.CharField(max_length=200, allow_blank=True, required=False)

    def validate_email(self, value):
        return value.casefold()
