from django.contrib import admin
from django.urls import path
from market import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.index, name='index'),
    path('logout/', views.logout_view, name='logout'),
    path('stocks/', views.stocks, name='stocks'),
    path('stock/<str:stock_name>/', views.stock_detail, name='stock_detail'),
    path('buy/<str:stock_name>/', views.buy, name='buy'),
    path('sell/<str:stock_name>/', views.sell, name='sell'),
    path('redirect_to_buy/<str:stock_name>/', views.redirect_to_buy, name='redirect_to_buy'),
    path('redirect_to_sell/<str:stock_name>/', views.redirect_to_sell, name='redirect_to_sell'),
    path('portfolio/', views.portfolio, name='portfolio'),
]