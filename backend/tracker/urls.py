from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    UserViewSet,
    HealthProfileViewSet,
    DailyMetricViewSet,
    HealthJournalViewSet,
    ChatMessageViewSet,
    RegisterAPIView,
    CoachClientsView,
    CoachChatView,
    weekly_stats,
    monthly_stats,
    dashboard,
    coaches, 
    coach_link,
   
    
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="users")
router.register("health-profile", HealthProfileViewSet, basename="health-profile")
router.register("health-metrics", DailyMetricViewSet, basename="health-metrics")
router.register("journals", HealthJournalViewSet, basename="journals")
router.register("chat-messages", ChatMessageViewSet, basename="chat-messages")



urlpatterns = [
    path("", include(router.urls)),
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("stats/weekly/", weekly_stats, name="weekly-stats"),
    path("stats/monthly/", monthly_stats, name="monthly-stats"),
    path("dashboard/", dashboard, name="dashboard"),
    path("coaches/", coaches, name="coaches"),
    path("coach-link/", coach_link, name="coach-link"),
    path("coach/clients/", CoachClientsView.as_view(), name="coach-clients"),
    path("coach/chats/<int:user_id>/", CoachChatView.as_view(), name="coach-chats"),
] 


