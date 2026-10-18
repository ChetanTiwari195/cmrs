from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Branch, User


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "code", "name"]


class MeSerializer(serializers.ModelSerializer):
    branch = BranchSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role", "branch"]


class AgentCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all())

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "password", "branch"]
        extra_kwargs = {"first_name": {"required": True, "allow_blank": False}}

    def validate(self, data):
        validate_password(data["password"], User(username=data["username"], first_name=data["first_name"]))
        return data

    def create(self, data):
        return User.objects.create_user(role=User.Role.AGENT, **data)
