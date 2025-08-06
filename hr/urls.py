from django.urls import path
from . import views
urlpatterns = [
    path('attendance/', views.attendance_dashboard, name='attendance_dashboard'),
    path('attendance/checkin/', views.check_in, name='check_in'),
    path('attendance/checkout/', views.check_out, name='check_out'),
   # path('register-device/', views.register_device, name='register_device'), # مسار جديد
    path('attendance/history/', views.attendance_history, name='attendance_history'),


    path('request-permission/', views.request_permission_view, name='request_permission'),
    path('my-permission-requests/', views.permission_request_list_view, name='permission_request_list'),
    path('permission-requests/<int:pk>/approve/', views.approve_permission_request, name='approve_permission_request'),
    # path('permission-requests/<int:pk>/detail/', views.permission_request_detail_view, name='permission_request_detail'), # يمكنك إضافة صفحة تفصيلية منفصلة إذا أردت

]
