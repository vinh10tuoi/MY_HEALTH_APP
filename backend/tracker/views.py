from datetime import timedelta
from django.utils import timezone
from django.db.models.functions import Coalesce
from rest_framework.decorators import api_view
import random
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Sum, Avg
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from .models import HealthProfile, DailyMetric, HealthJournal, CoachLink, ChatMessage, User
from .serializers import UserSerializer, HealthProfileSerializer, DailyMetricSerializer, HealthJournalSerializer, ChatMessageSerializer, RegisterSerializer
from .permissions import IsOwner
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import csrf_exempt
from rest_framework.exceptions import PermissionDenied


User = get_user_model()




class UserViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
        
    # POST /api/users/
    def create(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
    
    # GET|PATCH /api/users/current-user/
    @action(
        methods=["get", "patch"],
        detail=False,
        url_path="current-user",
        permission_classes=[permissions.IsAuthenticated],
    )
    def current_user(self, request):
        if request.method.lower() == "get":
            return Response(UserSerializer(request.user).data)

        ser = self.get_serializer(request.user, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(UserSerializer(request.user).data)


class HealthProfileViewSet(viewsets.GenericViewSet):
    serializer_class = HealthProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(methods=["get", "patch"], detail=False, url_path="me")
    def me(self, request):
        profile, _ = HealthProfile.objects.get_or_create(user=request.user)

        if request.method.lower() == "get":
            # Trả về hồ sơ sức khỏe với các chỉ số dinh dưỡng mới
            return Response(self.get_serializer(profile).data)

        # Cập nhật các giá trị dinh dưỡng và tính toán lại chúng
        ser = self.get_serializer(profile, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        profile = ser.save()  # Lưu lại và tính toán các giá trị dinh dưỡng

        # Trả về các giá trị cập nhật
        return Response(self.get_serializer(profile).data)
    
    

    # def retrieve(self, request, *args, **kwargs):
    #     user_profile = self.get_object()
    #     return Response({
    #         "height_cm": user_profile.height_cm,
    #         "current_weight_kg": user_profile.current_weight_kg,
    #         "age": user_profile.age,
    #         "goal": user_profile.goal,
    #         "bmi": user_profile.bmi,
    #         "daily_calories": user_profile.daily_calories,
    #         "daily_protein": user_profile.daily_protein,
    #         "daily_carbs": user_profile.daily_carbs,
    #         "daily_fats": user_profile.daily_fats,
    #     })
    
    # def get_queryset(self):
    #     return HealthProfile.objects.filter(user=self.request.user)
    
    # def perform_update(self, serializer):
    #     # Khi cập nhật hồ sơ sức khỏe, tính toán lại các giá trị dinh dưỡng
    #     serializer.save()

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []  # quan trọng: đăng ký không cần auth

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = ser.save()

        return Response(
            {
                "message": "Đăng ký thành công!",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class DailyMetricViewSet(viewsets.ModelViewSet):
    queryset = DailyMetric.objects.all()
    serializer_class = DailyMetricSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DailyMetric.objects.filter(user=self.request.user)

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        return qs.order_by("-date")


    def create(self, request, *args, **kwargs):
        # FE gửi date + các field còn lại
        date = request.data.get("date")
        if not date:
            return Response({"date": "Thiếu ngày (date)."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate dữ liệu bằng serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        obj, created = DailyMetric.objects.update_or_create(
            user=request.user,
            date=data["date"],
            defaults={
                "water_ml": data.get("water_ml"),
                "steps": data.get("steps"),
                "avg_heart_rate": data.get("avg_heart_rate"),
            },
        )

        out = self.get_serializer(obj).data
        return Response(out, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    

    @action(detail=False, methods=["post"], url_path="seed")
    def seed(self, request):
        days = int(request.data.get("days", 14))
        today = timezone.localdate()
        start_date = today - timedelta(days=days - 1)

        created = 0
        updated = 0

        for i in range(days):
            d = start_date + timedelta(days=i)

            defaults = {
                "water_ml": random.randint(1200, 2600),
                "steps": random.randint(3000, 12000),
                "avg_heart_rate": random.randint(60, 95),
            }

            _, was_created = DailyMetric.objects.update_or_create(
                user=request.user,
                date=d,
                defaults=defaults,
            )

            if was_created:
                created += 1
            else:
                updated += 1

        return Response({
            "from_date": str(start_date),
            "to_date": str(today),
            "created": created,
            "updated": updated,
        })
    

@api_view(["GET"])
@authentication_classes([OAuth2Authentication])
@permission_classes([IsAuthenticated])
def weekly_stats(request):
    # Nếu FE truyền date_from/date_to thì dùng, không thì default 7 ngày gần nhất
    to_date = parse_date(request.query_params.get("date_to", "") or "")
    from_date = parse_date(request.query_params.get("date_from", "") or "")

    if not to_date:
        to_date = timezone.localdate()
    if not from_date:
        from_date = to_date - timedelta(days=6)

    # Nếu nhập ngược (from > to) thì báo lỗi cho rõ
    if from_date > to_date:
        return Response(
            {"detail": "date_from phải nhỏ hơn hoặc bằng date_to"},
            status=status.HTTP_400_BAD_REQUEST
        )

    qs = DailyMetric.objects.filter(
        user=request.user,
        date__gte=from_date,
        date__lte=to_date
    ).order_by("date")

    summary = qs.aggregate(
        total_steps=Coalesce(Sum("steps"), 0),
        total_water_ml=Coalesce(Sum("water_ml"), 0),
        avg_heart_rate=Avg("avg_heart_rate"),
    )

    avg_hr = summary["avg_heart_rate"]
    avg_hr = round(float(avg_hr), 2) if avg_hr is not None else None

    daily = list(qs.values("date", "steps", "water_ml", "avg_heart_rate"))

    return Response({
        "from_date": str(from_date),
        "to_date": str(to_date),
        "total_steps": summary["total_steps"],
        "total_water_ml": summary["total_water_ml"],
        "avg_heart_rate": avg_hr,
        "daily": daily,
    })

@api_view(["GET"])
@authentication_classes([OAuth2Authentication])
@permission_classes([IsAuthenticated])
def monthly_stats(request):
    # 30 ngày gần nhất (tính cả hôm nay)
    to_date = timezone.localdate()
    from_date = to_date - timedelta(days=29)

    qs = DailyMetric.objects.filter(
        user=request.user,
        date__gte=from_date,
        date__lte=to_date
    ).order_by("date")

    summary = qs.aggregate(
        total_steps=Coalesce(Sum("steps"), 0),
        total_water_ml=Coalesce(Sum("water_ml"), 0),
        avg_heart_rate=Avg("avg_heart_rate"),
    )

    avg_hr = summary["avg_heart_rate"]
    if avg_hr is not None:
        avg_hr = round(float(avg_hr), 2)

    daily = list(qs.values("date", "steps", "water_ml", "avg_heart_rate"))

    return Response({
        "from_date": str(from_date),
        "to_date": str(to_date),
        "total_steps": summary["total_steps"],
        "total_water_ml": summary["total_water_ml"],
        "avg_heart_rate": avg_hr,
        "daily": daily,
    })


def _lay_khoang_ngay(request, mac_dinh_ngay=7):
    # Ưu tiên lấy từ query, không có thì default 7 ngày gần nhất (tính cả hôm nay)
    to_date = parse_date(request.query_params.get("date_to", "") or "")
    from_date = parse_date(request.query_params.get("date_from", "") or "")

    if not to_date:
        to_date = timezone.localdate()
    if not from_date:
        from_date = to_date - timedelta(days=mac_dinh_ngay - 1)

    if from_date > to_date:
        return None, None, Response(
            {"detail": "date_from phải nhỏ hơn hoặc bằng date_to"},
            status=status.HTTP_400_BAD_REQUEST
        )

    return from_date, to_date, None


@api_view(["GET"])
@authentication_classes([OAuth2Authentication])   # <--- QUAN TRỌNG nếu bạn đang dùng Bearer token OAuth2
@permission_classes([IsAuthenticated])
def dashboard(request):
    from_date, to_date, err = _lay_khoang_ngay(request, mac_dinh_ngay=7)
    if err:
        return err

    profile, _ = HealthProfile.objects.get_or_create(user=request.user)

    qs = (
        DailyMetric.objects
        .filter(user=request.user, date__gte=from_date, date__lte=to_date)
        .order_by("date")
    )

    weekly = qs.aggregate(
        total_steps=Coalesce(Sum("steps"), 0),
        total_water_ml=Coalesce(Sum("water_ml"), 0),
        avg_heart_rate=Avg("avg_heart_rate"),
    )

    avg_hr = weekly["avg_heart_rate"]
    weekly["avg_heart_rate"] = round(float(avg_hr), 2) if avg_hr is not None else None

    # làm đẹp số avg cho FE
    if weekly["avg_heart_rate"] is not None:
        weekly["avg_heart_rate"] = round(float(weekly["avg_heart_rate"]), 2)

    return Response({
        "user": UserSerializer(request.user).data,
        "profile": HealthProfileSerializer(profile).data,
        "range": {"from_date": str(from_date), "to_date": str(to_date)},
        "weekly": weekly,
        "daily": DailyMetricSerializer(qs, many=True).data,
    })


class HealthJournalViewSet(viewsets.ModelViewSet):
    serializer_class = HealthJournalSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [OAuth2Authentication]

    def get_queryset(self):
        return HealthJournal.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        obj, created = HealthJournal.objects.update_or_create(
            user=request.user,
            date=data["date"],
            defaults={"content": data.get("content", "")},
        )
        out = self.get_serializer(obj).data
        return Response(out, status=201 if created else 200)
    

    

@api_view(["GET"])
@authentication_classes([OAuth2Authentication])
@permission_classes([IsAuthenticated])
def coaches(request):
    # List user có role = COACH (✅ loại trừ chính mình)
    qs = (
        User.objects.filter(role="COACH")
        .exclude(id=request.user.id)
        .values("id", "username", "first_name", "last_name", "role")
    )
    return Response(list(qs))



@api_view(["GET", "POST", "DELETE"])
@authentication_classes([OAuth2Authentication])
@permission_classes([IsAuthenticated])
def coach_link(request):
    if getattr(request.user, "role", None) == "COACH":
        raise PermissionDenied("Tài khoản COACH không được chọn coach.")
        # ✅ CHẶN COACH: coach-link chỉ dành cho USER
    if getattr(request.user, "role", None) == "COACH":
        return Response(
            {"detail": "Tài khoản COACH không được chọn coach."},
            status=status.HTTP_403_FORBIDDEN,
        )
    # Xem coach hiện tại
    if request.method == "GET":
        link = CoachLink.objects.filter(user=request.user).select_related("coach").first()
        if not link:
            return Response({"coach": None})

        c = link.coach
        return Response({
            "coach": {
                "id": c.id,
                "username": c.username,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "role": c.role,
            }
        })

    # Kết nối / đổi coach
    if request.method == "POST":
        coach_id = request.data.get("coach_id")
        if not coach_id:
            return Response({"detail": "Thiếu coach_id"}, status=400)
        if str(coach_id) == str(request.user.id):
            return Response(
                {"detail": "Không thể chọn chính mình."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        coach = get_object_or_404(User, id=coach_id, role="COACH")
        

        obj, _ = CoachLink.objects.update_or_create(
            user=request.user,
            defaults={"coach": coach}
        )
        return Response({"ok": True, "coach_id": obj.coach_id})

    # Hủy kết nối
    CoachLink.objects.filter(user=request.user).delete()
    return Response({"ok": True})


class ChatMessageViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [OAuth2Authentication]

    def _get_coach(self):
        link = CoachLink.objects.filter(user=self.request.user).select_related("coach").first()
        return link.coach if link else None

    def get_queryset(self):
        coach = self._get_coach()
        if not coach:
            return ChatMessage.objects.none()
        return ChatMessage.objects.filter(user=self.request.user, coach=coach)

    def perform_create(self, serializer):
        coach = self._get_coach()
        if not coach:
            raise ValidationError({"detail": "Bạn chưa kết nối coach."})
        serializer.save(user=self.request.user, coach=coach, sender_role=ChatMessage.SENDER_USER)



class CoachClientsView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, "role", None) != "COACH":
            raise PermissionDenied("Bạn không phải COACH.")

        links = CoachLink.objects.filter(coach=request.user).select_related("user")
        data = []
        for lk in links:
            u = lk.user
            data.append({
                "id": u.id,
                "username": u.username,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "role": u.role,
            })
        return Response(data)


class CoachChatView(APIView):
    authentication_classes = [OAuth2Authentication]
    permission_classes = [IsAuthenticated]

    def _check_link(self, request, user_id: int):
        if getattr(request.user, "role", None) != "COACH":
            raise PermissionDenied("Bạn không phải COACH.")

        ok = CoachLink.objects.filter(coach=request.user, user_id=user_id).exists()
        if not ok:
            raise PermissionDenied("User này không thuộc danh sách client của bạn.")

    def get(self, request, user_id: int):
        self._check_link(request, user_id)

        qs = ChatMessage.objects.filter(user_id=user_id, coach=request.user).order_by("created_at")
        return Response(ChatMessageSerializer(qs, many=True).data)

    def post(self, request, user_id: int):
        self._check_link(request, user_id)

        content = (request.data.get("content") or "").strip()
        if not content:
            return Response({"content": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

        msg = ChatMessage.objects.create(
            user_id=user_id,
            coach=request.user,
            sender_role=ChatMessage.SENDER_COACH,
            content=content
        )
        return Response(ChatMessageSerializer(msg).data, status=status.HTTP_201_CREATED)






