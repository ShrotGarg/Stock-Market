from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from .models import Profile, Stock, Transaction, PriceHistory, IP, GoodArticle, BadArticle, BadMarketNews, GoodMarketNews
from random import sample, choice
from decimal import Decimal
from django.db.models import Sum
from collections import defaultdict
from django.core.serializers.json import DjangoJSONEncoder
import json, requests

def index(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'sign_up':
            form = UserCreationForm(request.POST)
            if form.is_valid():
                user = form.save()
                private_ip = get_public_ip()
                IP.objects.create(ip_address=private_ip)
                Profile.objects.get_or_create(user=user, defaults={'balance': 10000, 'net_worth_history': []})
                return redirect('/stocks')
            else:
                print("Sign up form errors:", form.errors)
        elif form_type == 'sign_in':
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('/stocks')
            else:
                print("Sign in failed")

    return render(request, 'market/index.html', {'sign_up_form': UserCreationForm()})

@login_required
def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def buy(request, stock_name):
    stock = get_object_or_404(Stock, name=stock_name)
    profile = request.user.profile

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        if quantity <= 0:
            return render(request, 'market/buy.html', {'stock': stock, 'error': 'Quantity must be greater than zero.'})

        total_price = stock.price * quantity

        if profile.balance >= total_price:
            # Deduct the purchase price from user balance
            profile.balance -= total_price
            profile.save()

            # Record the transaction
            Transaction.objects.create(
                user=request.user,
                stock=stock,
                quantity=quantity,
                transaction_type='BUY',
                purchase_price=stock.price  # Record the purchase price

            )

            # Update the stock price after buy
            update_stock_price_buy(stock)

            # Log transaction and update net worth
            log_transaction_and_update_net_worth(request, request.user)

            return redirect('stock_detail', stock_name=stock_name)
        else:
            return render(request, 'market/buy.html', {'stock': stock, 'error': 'Insufficient funds'})

    return render(request, 'market/buy.html', {'stock': stock})

@login_required
def sell(request, stock_name):
    stock = get_object_or_404(Stock, name=stock_name)
    profile = request.user.profile

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        if quantity <= 0:
            return render(request, 'market/sell.html', {'stock': stock, 'error': 'Quantity must be greater than zero.'})

        total_price = stock.price * quantity

        # Calculate total quantity owned by the user
        total_quantity_owned = Transaction.objects.filter(user=request.user, stock=stock).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

        if total_quantity_owned >= quantity:
            # Add the sale price to user balance
            profile.balance += total_price
            profile.save()

            # Record the transaction
            total_buy_quantity = 0
            total_buy_cost = Decimal(0)
            transactions = Transaction.objects.filter(user=request.user, stock=stock, transaction_type='BUY')
            for transaction in transactions:
                total_buy_quantity += transaction.quantity
                total_buy_cost += transaction.quantity * transaction.purchase_price

            avg_purchase_price = total_buy_cost / total_buy_quantity if total_buy_quantity > 0 else Decimal(0)

            Transaction.objects.create(
                user=request.user,
                stock=stock,
                quantity=quantity,
                transaction_type='SELL',
                purchase_price=avg_purchase_price  # Record the average purchase price

            )

            # Update the stock price after sell
            update_stock_price_sell(stock)

            # Log transaction and update net worth
            log_transaction_and_update_net_worth(request, request.user)

            return redirect('stock_detail', stock_name=stock_name)
        else:
            return render(request, 'market/sell.html', {'stock': stock, 'error': 'Insufficient stocks'})

    return render(request, 'market/sell.html', {'stock': stock})

def update_stock_price_buy(stock):
    stock.price *= Decimal('1.01')  # Increase price if more buys than sells

    stock.save()
    PriceHistory.objects.create(stock=stock, price=stock.price)

def update_stock_price_sell(stock):
    stock.price *= Decimal('0.99')  # Decrease price if more sells than buys

    stock.save()
    PriceHistory.objects.create(stock=stock, price=stock.price)

def stocks(request):
    stocks = Stock.objects.all()
    transaction_count = Transaction.objects.count()
    good_articles = list(GoodArticle.objects.all())
    bad_articles = list(BadArticle.objects.all())

    articles = []

    if 'current_article_ids' in request.session and 'current_article_type' in request.session:
        article_ids = request.session['current_article_ids']
        article_type = request.session['current_article_type']

        if article_type == 'good':
            articles = GoodArticle.objects.filter(id__in=article_ids)
        elif article_type == 'bad':
            articles = BadArticle.objects.filter(id__in=article_ids)
    else:
        articles = sample(good_articles, 3)
        request.session['current_article_ids'] = [article.id for article in articles]
        request.session['current_article_type'] = 'good'

    # Update stock prices based on transaction count
    if transaction_count % 150 == 0:
        for stock in stocks:
            if sum(stock.price for stock in stocks) >= 0:
                stock.price *= Decimal('1.2')
            else:
                stock.price *= Decimal('0.8')
            stock.save()
    elif transaction_count % 75 == 0:
        for stock in stocks:
            stock.price *= Decimal('1.2')
            stock.save()
    elif transaction_count % 50 == 0:
        for stock in stocks:
            stock.price *= Decimal('0.8')
            stock.save()

    # Update articles based on transaction count
    if transaction_count >= 50:
        if transaction_count % 150 == 0:
            article_type = 'good' if sample([True, False]) else 'bad'
        elif transaction_count % 75 == 0:
            article_type = 'good'
        elif transaction_count % 50 == 0:
            article_type = 'bad'

        if article_type == 'good':
            articles = sample(good_articles, 3)
        else:
            articles = sample(bad_articles, 3)

        request.session['current_article_ids'] = [article.id for article in articles]
        request.session['current_article_type'] = article_type

    return render(request, 'market/stocks.html', {'stocks': stocks, 'news_data': articles})

@login_required
def stock_detail(request, stock_name):
    # Retrieve the stock object based on the provided stock_name
    stock = get_object_or_404(Stock, name=stock_name)

    # Get the total number of transactions
    transaction_count = Transaction.objects.count()

    # Check if it's the 7th transaction
    is_seventh_transaction = transaction_count % 7 == 0

    # Initialize news_data from session or None
    news_data = request.session.get('news_data', None)

    if is_seventh_transaction:
        # Randomly choose between 'good' and 'bad' news
        news_type = choice(['good', 'bad'])

        if news_type == 'good':
            # Increase stock price by 10% if news is 'good'
            stock.price *= Decimal('1.1')
            stock.save()
            # Select a random GoodMarketNews object
            selected_news = GoodMarketNews.objects.order_by('?').first()
        else:
            # Decrease stock price by 10% if news is 'bad'
            stock.price *= Decimal('0.9')
            stock.save()
            # Select a random BadMarketNews object
            selected_news = BadMarketNews.objects.order_by('?').first()

        # Store the selected news data in session
        news_data = {
            'news_type': news_type,
            'title': selected_news.title,
            'description': selected_news.description,
            'image_url': selected_news.image_url
        }
        request.session['news_data'] = news_data
    else:
        # Clear news_data from session if not the 7th transaction
        request.session.pop('news_data', None)
        news_data = None

    # Retrieve price history for the stock
    price_history_data = PriceHistory.objects.filter(stock=stock).order_by('timestamp')
    # Extract timestamps and prices for chart plotting
    labels = [entry.timestamp.strftime('%Y-%m-%d %H:%M:%S') for entry in price_history_data]
    prices = [entry.price for entry in price_history_data]

    # Render the template with necessary data
    return render(request, 'market/stock_detail.html', {
        'stock': stock,
        'data': json.dumps(prices, cls=DjangoJSONEncoder),
        'labels': json.dumps(labels, cls=DjangoJSONEncoder),
        'news_data': news_data,
    })

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org')
        if response.status_code == 200:
            return response.text
        else:
            return "Unable to retrieve public IP address"
    except Exception as e:
        return f"Error: {e}"

public_ip = get_public_ip()

def redirect_to_buy(request, stock_name):
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'buy':
        return redirect('buy', stock_name=stock_name)
    else:
        return redirect('stock_detail', stock_name=stock_name)

@login_required
def redirect_to_sell(request, stock_name):
    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'sell':
        return redirect('sell', stock_name=stock_name)
    else:
        return redirect('stock_detail', stock_name=stock_name)


@login_required
def portfolio(request):
    profile = Profile.objects.get(user=request.user)
    owned_stocks = profile.stocks.all()

    portfolio_data = []
    total_gain_loss = Decimal(0)
    total_stocks = 0

    stock_data = defaultdict(lambda: {'total_quantity': 0, 'total_cost': Decimal(0)})

    transactions = Transaction.objects.filter(user=request.user)
    for transaction in transactions:
        if transaction.transaction_type == 'BUY':
            stock_data[transaction.stock]['total_quantity'] += transaction.quantity
            stock_data[transaction.stock]['total_cost'] += transaction.quantity * transaction.purchase_price
        elif transaction.transaction_type == 'SELL':
            if stock_data[transaction.stock]['total_quantity'] > 0:
                avg_purchase_price = stock_data[transaction.stock]['total_cost'] / stock_data[transaction.stock]['total_quantity']
            else:
                avg_purchase_price = Decimal(0)
            stock_data[transaction.stock]['total_quantity'] -= transaction.quantity
            stock_data[transaction.stock]['total_cost'] -= transaction.quantity * avg_purchase_price

    for stock, data in stock_data.items():
        total_quantity = data['total_quantity']
        total_cost = data['total_cost']

        if total_quantity > 0:
            average_purchase_price = total_cost / total_quantity
            average_purchase_price = round(average_purchase_price, 2)
            current_value = stock.price * total_quantity
            gain_loss = round(current_value - total_cost, 2)
            total_gain_loss += gain_loss
            total_stocks += total_quantity

            portfolio_data.append({
                'stock': stock,
                'quantity': total_quantity,
                'purchase_price': average_purchase_price,
                'current_price': stock.price,
                'gain_loss': gain_loss,
            })

    user_balance = profile.balance
    net_worth = user_balance + sum(stock.price * data['total_quantity'] for stock, data in stock_data.items())

    net_worth_history = request.session.get('net_worth_history', [])

    # Prepare context data to pass to template
    context = {
        'profile': profile,
        'portfolio_data': portfolio_data,
        'total_stocks': total_stocks,
        'total_gain_loss': total_gain_loss,
        'user_balance': user_balance,
        'net_worth': net_worth,
        'net_worth_history': json.dumps(net_worth_history),
    }

    return render(request, 'market/portfolio.html', context)

MAX_NET_WORTH_HISTORY_LENGTH = 50

def log_transaction_and_update_net_worth(request, user):
    profile = Profile.objects.get(user=user)
    stock_data = defaultdict(lambda: {'total_quantity': 0, 'total_cost': Decimal(0)})

    transactions = Transaction.objects.filter(user=user)
    for transaction in transactions:
        if transaction.transaction_type == 'BUY':
            stock_data[transaction.stock]['total_quantity'] += transaction.quantity
            stock_data[transaction.stock]['total_cost'] += transaction.quantity * transaction.purchase_price
        elif transaction.transaction_type == 'SELL':
            if stock_data[transaction.stock]['total_quantity'] > 0:
                avg_purchase_price = stock_data[transaction.stock]['total_cost'] / stock_data[transaction.stock]['total_quantity']
            else:
                avg_purchase_price = Decimal(0)
            stock_data[transaction.stock]['total_quantity'] -= transaction.quantity
            stock_data[transaction.stock]['total_cost'] -= transaction.quantity * avg_purchase_price

    net_worth = profile.balance + sum(stock.price * data['total_quantity'] for stock, data in stock_data.items())

    # Retrieve net worth history from session or initialize as empty list
    net_worth_history = request.session.get('net_worth_history', [])

    # Append current net worth to history
    net_worth_history.append(float(net_worth))

    # Limit the length of net worth history (remove oldest elements if necessary)
    if len(net_worth_history) > MAX_NET_WORTH_HISTORY_LENGTH:
        net_worth_history = net_worth_history[-MAX_NET_WORTH_HISTORY_LENGTH:]

    # Store updated net worth history in session
    request.session['net_worth_history'] = net_worth_history

    # Ensure session is saved
    request.session.modified = True