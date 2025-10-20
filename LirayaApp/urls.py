from django.urls import path, include
from . import views
from django.conf import settings
from django.conf.urls.static import static

########################### USER ###########################
urlpatterns = [
    path('', views.user_homepage, name='user_homepage'),
    path('about-us/', views.user_aboutus, name='user_aboutus'),
    path('search/', views.user_search, name='user_search'),
    path('view-info/', views.view_info, name='user_viewinfo'),
    path('suggest/', views.user_suggestions, name='user_suggestions'),

########################### LIBRARIAN ###########################
    path('librarian/homepage/', views.librarian_homepage, name='librarian_homepage'),
    path('librarian_suggestions/', views.librarian_suggestions, name='librarian_suggestions'),  
    path('librarian/addbook/', views.librarian_addbook, name='librarian_addbook'),
    path('librarian/profile/', views.librarian_profile, name='librarian_profile'),
    path('librarian/viewbook/<int:book_id>/', views.librarian_view_details, name='view_book_details'),
    path('librarian/search-history/', views.librarian_search_history, name='librarian_search_history'),

    # Add the logout path under librarian
    path('librarian/logout/', views.logout_view, name='librarian_logout'),  # New logout path

########################### LOGIN ###########################
    path('login/', views.login_view, name='login'),
    path('login/forgot_password/', views.forgot_password_view, name='forgot_password'),
    path('login/forgot_password/verification/', views.verification_view, name='email_verification'),
    path('login/forgot_password/verification/change_password/', views.change_password_view, name='change_password'),
    path('login/first_login/', views.first_login_view, name='first_login'),

    ######### log in using email ############
    
    path('auth/', include('social_django.urls', namespace='social')),  # ← Google login flow
    path('google/login/redirect/', views.google_login_redirect, name='google_login_redirect'),

    ############ OTP for Forgot Pass ###################
    
    path('login/forgot_password/verification/resend/', views.resend_otp_view, name='resend_otp'),
    path('cancel-otp/', views.cancel_otp_view, name='cancel_otp'),

    #### Spell Checker ######

    path('check-spelling/', views.check_spelling, name='check_spelling'),

########################### ADMIN ###########################
    path('adminhomepage/', views.admin_homepage, name='admin_homepage'),
    path('admin_suggestions/', views.admin_suggestions, name='admin_suggestions'),
    path('adminbookdetails/', views.admin_bookdetails, name='admin_bookdetails'),
    path('adminmanageaccount/', views.admin_manageaccount, name='admin_manageaccount'),
    path('adminmanageaccount/viewprofile/<int:account_id>/', views.admin_manageaccount_viewprofile, name='admin_viewprofile'), 
    path('admincreateaccount/', views.admin_createaccount, name='admin_createaccount'),
    path('adminprofile/', views.admin_profile, name='admin_profile'),
    path('adminrecords/', views.admin_records, name='admin_records'),
    path('adminrecordsview/<int:account_id>/', views.admin_records_view, name='admin_records_view'),
    path('admininheritance/', views.admin_templateinheritance, name='admin_templateinheritance'),
    path('generate-pdf/<str:report_type>/', views.generate_pdf, name='generate_pdf'),
    path('check-username/', views.check_username, name='check_username'),
    path('deactivate_account/', views.deactivate_account, name='deactivate_account'),
    path('logout/', views.admin_logout, name='logout'),  
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

