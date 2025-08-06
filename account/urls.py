from django.contrib.auth import views as auth_views
from django.urls import path, include
from . import views

urlpatterns = [
    path('', include('django.contrib.auth.urls')),
#    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.home, name='home'),
    
    path('register/', views.register, name='register'),
    path('edit/', views.edit, name='edit'),
    path('users/add/', views.add_account, name='add_account'), # هذا هو المسار الجديد أو الموجود
   
    path('manage-users/', views.user_list, name='user_list'),
    path('manage-users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'), # هذا هو المسار الجديد للحذف

    # مسارات إدارة المجموعات
    path('manage-groups/', views.group_list, name='group_list'),
    path('manage-groups/create/', views.group_create, name='group_create'),
    path('manage-groups/<int:group_id>/edit/', views.group_edit, name='group_edit'),
    path('manage-groups/<int:group_id>/delete/', views.group_delete, name='group_delete'),
    path('add-account/', views.add_account, name='add_account'),



]