from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from rest_framework import serializers


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = "USER", "Người dùng"
        COACH = "COACH", "Huấn luyện viên / Chuyên gia"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
        verbose_name="Vai trò"
    )


class HealthProfile(models.Model):
    class Goal(models.TextChoices):
        GAIN = "GAIN", "Tăng cơ / Tăng cân"
        LOSE = "LOSE", "Giảm cân"
        MAINTAIN = "MAINTAIN", "Duy trì"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="health_profile", verbose_name="Người dùng")
    height_cm = models.IntegerField(null=True, blank=True, verbose_name="Chiều cao (cm)")
    current_weight_kg = models.FloatField(null=True, blank=True, verbose_name="Cân nặng hiện tại (kg)")
    age = models.IntegerField(null=True, blank=True, verbose_name="Tuổi")
    goal = models.CharField(max_length=10, choices=Goal.choices, default=Goal.MAINTAIN, verbose_name="Mục tiêu")
    bmi = models.FloatField(null=True, blank=True, verbose_name="BMI")
    daily_calories = models.IntegerField(null=True, blank=True, verbose_name="Lượng calo hàng ngày")
    daily_protein = models.IntegerField(null=True, blank=True, verbose_name="Lượng protein hàng ngày")
    daily_carbs = models.IntegerField(null=True, blank=True, verbose_name="Lượng carb hàng ngày")
    daily_fats = models.IntegerField(null=True, blank=True, verbose_name="Lượng chất béo hàng ngày")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lúc")

    def save(self, *args, **kwargs):
    # 1) BMI chỉ tính khi đủ height + weight
        if self.height_cm is not None and self.current_weight_kg is not None and self.height_cm > 0:
            h = self.height_cm / 100
            self.bmi = round(self.current_weight_kg / (h * h), 2)
        else:
            self.bmi = None

        # 2) Calories/macros chỉ tính khi đủ age + height + weight
        can_calc = (
            self.current_weight_kg is not None
            and self.height_cm is not None
            and self.age is not None
        )

        if can_calc:
            if self.goal == self.Goal.GAIN:
                cal = self.calculate_calories(self.current_weight_kg, increase=True)
            elif self.goal == self.Goal.LOSE:
                cal = self.calculate_calories(self.current_weight_kg, increase=False)
            else:
                cal = self.calculate_calories(self.current_weight_kg, increase=False)

            self.daily_calories = cal
            self.daily_protein = self.calculate_protein(self.current_weight_kg)
            self.daily_carbs = self.calculate_carbs(cal)
            self.daily_fats = self.calculate_fats(cal)
        else:
            # Profile mới tạo thường chưa có đủ dữ liệu -> để None để không crash
            self.daily_calories = None
            self.daily_protein = None
            self.daily_carbs = None
            self.daily_fats = None

        super().save(*args, **kwargs)



    def calculate_calories(self, weight, increase=True):
        # Tính toán lượng calo cơ bản (BMR)
        bmr = 10 * weight + 6.25 * self.height_cm - 5 * self.age + 5  # Giả sử là nam
        if increase:
            return bmr * 1.2 + 300  # Tăng cơ (thêm 300 calo)
        else:
            return bmr * 1.2 - 300  # Giảm cân (bớt 300 calo)

    def calculate_protein(self, weight):
        return weight * 1.5  # 1.5g protein mỗi kg trọng lượng cơ thể

    def calculate_carbs(self, calories):
        return int(calories * 0.5 / 4)  # 50% calo từ carbs, mỗi gram carbs có 4 calo

    def calculate_fats(self, calories):
        return int(calories * 0.25 / 9)  # 25% calo từ chất béo, mỗi gram chất béo có 9 calo



    

class DailyMetric(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_metrics")
    date = models.DateField()
    heart_rate = models.IntegerField(null=True, blank=True, verbose_name="Nhịp tim (bpm)")
    water_ml = models.PositiveIntegerField(default=0)
    steps = models.PositiveIntegerField(default=0)
    avg_heart_rate = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]



class HealthJournal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    content = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user.username} - {self.date}"
    

class CoachLink(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coach_link")
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="clients")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} -> {self.coach}"


class ChatMessage(models.Model):
    SENDER_USER = "USER"
    SENDER_COACH = "COACH"
    SENDER_CHOICES = [
        (SENDER_USER, "User"),
        (SENDER_COACH, "Coach"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coach_chat_messages",
    )
    sender_role = models.CharField(max_length=10, choices=SENDER_CHOICES, default=SENDER_USER)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user_id}->{self.coach_id} {self.sender_role}: {self.content[:20]}"
    


