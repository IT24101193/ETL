from rest_framework import serializers
import re

from customers.models import Customer


PHONE_PATTERN = re.compile(r"^\+?[0-9().\s-]+$")


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

    def validate_phone(self, value):
        if not value:
            return value
        digits = re.sub(r"\D", "", value)
        if not PHONE_PATTERN.fullmatch(value) or not 7 <= len(digits) <= 15:
            raise serializers.ValidationError(
                "Enter a phone number with 7 to 15 digits; spaces, +, hyphens, "
                "and parentheses are allowed."
            )
        return value
