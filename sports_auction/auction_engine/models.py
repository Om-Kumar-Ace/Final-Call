from django.db import models
import uuid

class AuctionEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    date_created = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    # NEW FIELD: Admin PIN
    admin_pin = models.CharField(max_length=10, default="1234") 

    def __str__(self): return self.name

# ... (Keep Team, Player, AuctionState, TransactionLog exactly as they were) ...
class Team(models.Model):
    auction = models.ForeignKey(AuctionEvent, on_delete=models.CASCADE, related_name="teams")
    name = models.CharField(max_length=100)
    budget = models.IntegerField(default=10000)
    spent = models.IntegerField(default=0)
    players_count = models.IntegerField(default=0)
    captain_name = models.CharField(max_length=100, blank=True, default="")
    vice_captain_name = models.CharField(max_length=100, blank=True, default="")
    def __str__(self): return self.name

class Player(models.Model):
    auction = models.ForeignKey(AuctionEvent, on_delete=models.CASCADE, related_name="players")
    email = models.EmailField(null=True, blank=True)
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True, default="")
    category = models.CharField(max_length=50, default="General")
    position = models.CharField(max_length=50, default="Player")
    base_price = models.IntegerField(default=200)
    image_url = models.TextField(blank=True, null=True)
    is_sold = models.BooleanField(default=False)
    is_unsold = models.BooleanField(default=False)
    sold_to = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    sold_price = models.IntegerField(default=0)
    priority_score = models.IntegerField(default=0)
    def __str__(self): return self.name

class AuctionState(models.Model):
    auction = models.ForeignKey(AuctionEvent, on_delete=models.CASCADE)
    current_player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True)
    current_bid = models.IntegerField(default=0)

class TransactionLog(models.Model):
    auction = models.ForeignKey(AuctionEvent, on_delete=models.CASCADE)
    player_name = models.CharField(max_length=100)
    team_name = models.CharField(max_length=100)
    amount = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

