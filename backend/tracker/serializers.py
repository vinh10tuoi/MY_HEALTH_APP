from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import HealthProfile, DailyMetric, HealthJournal, ChatMessage

User = get_user_model()

class HealthProfileSerializer(serializers.ModelSerializer):
    bmi = serializers.SerializerMethodField()

    class Meta:
        model = HealthProfile
        fields = ['height_cm', 'current_weight_kg', 'age', 'goal', 'bmi', 
                  'daily_calories', 'daily_protein', 'daily_carbs', 'daily_fats']

    def get_bmi(self, obj):
        if not obj.height_cm or not obj.current_weight_kg:
            return None
        h = obj.height_cm / 100.0
        return round(obj.current_weight_kg / (h * h), 2)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "password", "email", "first_name", "last_name", "role"]
        extra_kwargs = {
            'password': {'write_only': True},  # Mật khẩu chỉ được ghi, không hiển thị
        }

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email"),
            password=password,
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=validated_data.get("role", User.Role.USER),
        )
        HealthProfile.objects.get_or_create(user=user)
        return user




class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    # ✅ thêm role + giới hạn đúng theo model choices
    role = serializers.ChoiceField(choices=User.Role.choices, required=False, default=User.Role.USER)

    class Meta:
        model = User
        fields = ("username", "password", "email", "first_name", "last_name", "role")

    def create(self, validated_data):
        password = validated_data.pop("password")
        role = validated_data.pop("role", User.Role.USER)

        user = User(**validated_data)
        user.role = role  # ✅ gán role
        user.set_password(password)
        user.save()

        # ✅ tạo profile mặc định
        HealthProfile.objects.get_or_create(user=user)
        return user



class DailyMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMetric
        fields = ["id", "date", "water_ml", "steps", "avg_heart_rate"]

class HealthJournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthJournal
        fields = ["id", "date", "content", "created_at", "updated_at"]


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ["id", "content", "sender_role", "created_at"]
        read_only_fields = ["id", "sender_role", "created_at"]