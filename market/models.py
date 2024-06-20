from django.contrib.auth.models import User
from django.db import models
from django.conf import settings

class Stock(models.Model):
    name = models.CharField(max_length=10)
    price = models.DecimalField(decimal_places=2, max_digits=10)

    def __str__(self):
        return self.name

class Transaction(models.Model):
    quantity = models.PositiveIntegerField()
    transaction_type = models.CharField(max_length=4)
    timestamp = models.DateTimeField(auto_now_add=True)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)  # Add on_delete=models.CASCADE
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    purchase_price = models.DecimalField(decimal_places=2, max_digits=10, blank=True, default=1.0, null=True)

class PriceHistory(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)  # Add on_delete=models.CASCADE
    timestamp = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

class Profile(models.Model):
    balance = models.DecimalField(decimal_places=2, default=10000, max_digits=10)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stocks = models.ManyToManyField(Stock)

    def __str__(self):
        return f"Profile of {self.user.username}"

class IP(models.Model):
    ip_address = models.CharField(max_length=100, null=True)

class GoodArticle(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image_url = models.URLField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class BadArticle(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image_url = models.URLField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class GoodMarketNews(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image_url = models.URLField(max_length=200)

    def __str__(self):
        return self.title

class BadMarketNews(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image_url = models.URLField(max_length=200)

    def __str__(self):
        return self.title