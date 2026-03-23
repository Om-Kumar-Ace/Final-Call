from django.urls import path
from auction_engine import views

urlpatterns = [
    path('', views.setup_view, name='setup'),
    path('dashboard/', views.dashboard_view, name='auction_dashboard'),
    
    # New Archive Routes
    path('archives/', views.archive_list, name='archive_list'),
    path('archives/<uuid:event_id>/', views.archive_detail, name='archive_detail'),

    # APIs
    path('api/state/', views.get_state),
    path('api/action/', views.api_action),
    path('api/verify-pin/', views.verify_pin, name='verify_pin'),
    path('export/', views.export_csv, name='export'),
    path('api/toggle-priority/', views.toggle_priority, name='toggle_priority'),
    path('api/assign-roles/', views.assign_team_roles, name='assign_roles'),

     path("proxy-image/", views.proxy_image, name="proxy_image"),
]