from django.urls import path
from . import views

urlpatterns = [
    # Auth / pages utilisateur
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('about/', views.about_view, name='about'),
    path('faq/', views.faq_view, name='faq'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),

    #  Ports
    path("ports/", views.ports_list, name="ports_list"),
    path("api/ports/", views.ports_api, name="ports_api"),
    path("api/ports/search/", views.ports_search_api, name="ports_search_api"),
    path("api/ships/", views.ships_api, name="ships_api"),
    path("api/ships/<str:mmsi>/track/", views.ship_track_api, name="ship_track_api"),
    path("api/wikipedia/", views.wikipedia_proxy, name="wikipedia_proxy"),
    path("api/ship-photo/", views.ship_photo_proxy, name="ship_photo_proxy"),
]