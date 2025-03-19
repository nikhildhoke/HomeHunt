from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signingup, name='signup'),
    path('confirm/<str:username>', views.confirm_signup, name='confirm'),
    path('login/', views.login_view, name='login'),
    path('home/<str:username>/', views.home_page, name='home'),
    path('listings/<str:listing_type>/<str:username>/', views.listings, name='listings'),
    path('place-ad/<str:username>/', views.place_ad, name='place_ad'),
    path('property-details/<str:action_type>/<str:username>/<str:property_id>/', views.property_details, name='property-details'), 
    path('book-viewing/<str:username>/<str:property_id>/', views.book_viewing, name='book-viewing'),
    path('edit-property-details/<str:username>/<str:property_id>/', views.edit_property_details, name='edit_property_details'),
    path('delete-property/<str:username>/<str:property_id>/', views.delete_property, name='delete_property'),
]