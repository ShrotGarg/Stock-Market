from django.contrib import admin
from .models import Stock, Transaction, PriceHistory, GoodArticle, BadArticle, GoodMarketNews, BadMarketNews, Profile

admin.site.register(Stock)
admin.site.register(Profile)
admin.site.register(Transaction)
admin.site.register(PriceHistory)
admin.site.register(GoodArticle)
admin.site.register(BadArticle)
admin.site.register(GoodMarketNews)
admin.site.register(BadMarketNews)