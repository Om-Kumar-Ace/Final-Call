import pandas as pd
import json, random ,requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import F 
from .models import Team, Player, AuctionState, TransactionLog, AuctionEvent
from django.contrib import messages
from django.utils import timezone


def normalize_columns(df):
    # 1. Clean existing columns (lowercase, strip spaces)
    df.columns = df.columns.astype(str).str.strip().str.lower()
    print(f"DEBUG: Detected Columns -> {list(df.columns)}") 

    # 2. Mapping Dictionary
    mapping = {
        'name': ['player', 'player name', 'fullname', 'name', 'full name'],
        'email': ['email', 'email address', 'contact', 'mail', 'id','Mobile No.','Email address'],
        'category': ['category', 'cat', 'group', 'tier', 'type','role','ROLE'],
        'position': ['position', 'speciality', 'playing role','playing position'],
        'department': ['department', 'dept', 'branch', 'section'],
        'year':['year','y','Year','YEAR'],
        'base_price': ['baseprice', 'base price', 'cost', 'starting bid', 'price', 'points', 'base'],
        'image': ['image', 'photo', 'pic', 'url', 'image link']
    }

    # 3. Rename columns
    new_cols = {}
    for db_field, aliases in mapping.items():
        for alias in aliases:
            if alias in df.columns:
                new_cols[alias] = db_field
                break 
    
    df = df.rename(columns=new_cols)
    print(f"DEBUG: Mapped Columns -> {list(df.columns)}")
    return df

# --- SETUP VIEW ---
def setup_view(request):
    if request.method == "POST":
        action = request.POST.get('action_type')

        if action == 'continue':
            return redirect('auction_dashboard')

        elif action == 'new':
            try:
                with transaction.atomic():
                    # 1. Deactivate Old Auctions
                    AuctionEvent.objects.update(is_active=False)
                    
                    # 2. Create New Event
                    event_name = request.POST.get('event_name', 'New Auction')
                    event_pin = request.POST.get('admin_pin', '1212')
                    event = AuctionEvent.objects.create(name=event_name, is_active=True)

                    # 3. Create Teams
                    count = int(request.POST.get('team_count', 4))
                    budget = int(request.POST.get('budget', 5000))
                    teams_to_create = [
                        Team(auction=event, name=f"Team {i+1}", budget=budget) 
                        for i in range(count)
                    ]
                    Team.objects.bulk_create(teams_to_create)

                    # 4. Process File
                    if 'file_upload' in request.FILES:
                        f = request.FILES['file_upload']
                        if f.name.endswith('.csv'):
                            df = pd.read_csv(f)
                        else:
                            df = pd.read_excel(f)
                        
                        # Apply Mapping
                        df = normalize_columns(df)
                        
                        # --- DATA CLEANING ---
                        if 'name' in df.columns:
                            # Drop empty names
                            df = df.dropna(subset=['name'])
                            
                            # Handle Email Duplicates
                            if 'email' in df.columns:
                                df['email'] = df['email'].astype(str).str.lower().str.strip()
                                df = df.drop_duplicates(subset=['email'], keep='first')
                            
                            # === FIX: HANDLE BASE PRICE SAFELY ===
                            if 'base_price' in df.columns:
                                # Convert to numeric, turn errors (text) into NaN
                                df['base_price'] = pd.to_numeric(df['base_price'], errors='coerce')
                                # Fill NaN with default value (e.g. 200)
                                df['base_price'] = df['base_price'].fillna(0)
                                # Convert float (200.0) to integer (200)
                                df['base_price'] = df['base_price'].astype(int)
                            else:
                                # If column missing, fill with 200
                                df['base_price'] = 0
                            # ======================================

                            # Create Players
                            players = []
                            for _, row in df.iterrows():
                                players.append(Player(
                                    auction=event, 
                                    name=str(row['name']).strip(),
                                    email=row.get('email', None),
                                    department=row.get('department', ''),
                                    year=row.get('year',''),
                                    category=row.get('category', 'General'),
                                    position=row.get('position', 'Player'),
                                    base_price=row['base_price'], # Now strictly an integer
                                    image_url=row.get('image', '')
                                ))
                            
                            Player.objects.bulk_create(players)
                            print(f"DEBUG: Imported {len(players)} Players")
                        else:
                            messages.error(request, "Error: CSV must have a 'Name' column.")

                    # 5. Create State
                    AuctionState.objects.create(auction=event)
                    
                return redirect('auction_dashboard')

            except Exception as e:
                print(f"CRITICAL ERROR: {e}")
                messages.error(request, f"Error: {e}")

    # Get active event for "Resume" button
    active_event = AuctionEvent.objects.filter(is_active=True).first()
    return render(request, 'setup.html', {'active_event': active_event})

# --- ARCHIVE VIEWS ---
def archive_list(request):
    events = AuctionEvent.objects.all().order_by('-date_created')
    return render(request, 'archive_list.html', {'events': events})

def archive_detail(request, event_id):
    event = get_object_or_404(AuctionEvent, id=event_id)
    teams = event.teams.all()
    sold_players = event.players.filter(is_sold=True)
    unsold_players = event.players.filter(is_unsold=True)
    return render(request, 'archive_detail.html', {
        'event': event, 'teams': teams, 'sold': sold_players, 'unsold': unsold_players
    })

# --- API (Filters by Active Event) ---
def get_state(request):
    event = AuctionEvent.objects.filter(is_active=True).first()
    if not event: return JsonResponse({'error': 'No active auction'})

    state, _ = AuctionState.objects.get_or_create(auction=event)
    teams = list(event.teams.values(
    'id', 'name', 'budget', 'spent', 'players_count', 
    'captain_name', 'vice_captain_name'
).order_by('id'))
    
    curr_p = None
    if state.current_player:
        p = state.current_player
        curr_p = {
            'id': p.id, 'name': p.name, 'department': p.department,
            'category': p.category, 'position': p.position, 
            'image': p.image_url, 'base_price': p.base_price, 'year': p.year,
        }

    history = list(TransactionLog.objects.filter(auction=event).values(
        'player_name', 'team_name', 'amount', 'timestamp'
    ).order_by('-id'))
    all_unsold_players = list(event.players.filter(
        is_sold=False, 
        is_unsold=False
    ).values('id', 'name', 'category', 'priority_score').order_by('name'))
    stats = {
        'remaining': event.players.filter(is_sold=False, is_unsold=False).count(),
        'unsold': event.players.filter(is_unsold=True).count(),
        'sold': event.players.filter(is_sold=True).count(),
    }
    categories = list(
    Player.objects
    .values_list("category", flat=True)
    .distinct()
)
    return JsonResponse({
        'auction_name': event.name,
        'current_player': curr_p,
        'current_bid': state.current_bid,
        'teams': teams,
        'history': history,
        'stats': stats,
        'all_unsold_players': all_unsold_players,
        'host_url': request.get_host(),
        'categories': categories
    })

@csrf_exempt
def api_action(request):
    if request.method != "POST":
        return JsonResponse({"status": "invalid_method"})

    try:
        data = json.loads(request.body)
    except:
        return JsonResponse({"status": "invalid_json"})

    action = data.get("action")
    category = data.get("category", "ALL")  # 👈 NEW
    categories = list(
    Player.objects
    .values_list("category", flat=True)
    .distinct()
    )

# optional: clean + sort
    categories = sorted([c for c in categories if c])
    event = AuctionEvent.objects.filter(is_active=True).first()
    if not event:
        return JsonResponse({"status": "no_active_event"})

    with transaction.atomic():
        state = AuctionState.objects.select_for_update().get(auction=event)

        # =========================================================
        # 🎯 SPIN (CATEGORY + PRIORITY BASED)
        # =========================================================
        if action == "SPIN":

            
            
            candidates = event.players.filter(is_sold=False, is_unsold=False)
            # apply category filter
            if category and category != "ALL":
                filtered = candidates.filter(category__iexact=category)

                # fallback if empty
                if filtered.exists():
                    candidates = filtered

            # priority players first
            priority_candidates = candidates.filter(priority_score__gt=0).order_by("-priority_score")

            if priority_candidates.exists():
                winner = priority_candidates.first()

                # reset priority after selection
                winner.priority_score = 0
                winner.save()

            elif candidates.exists():
                winner = random.choice(list(candidates))
            else:
                return JsonResponse({"status": "empty_pool"})

            state.current_player = winner
            state.current_bid = winner.base_price
            state.last_action_time = timezone.now()
            state.save()

            return JsonResponse({
                "status": "success",
                "player": winner.name,
                "is_unsold_round": state.is_unsold_round,
            })

        elif action == 'BID':
            state.current_bid = int(data.get('amount', 0))
            state.save()

        elif action == 'SELL':
            team = Team.objects.select_for_update().get(id=data.get('team_id'))
            player = state.current_player
            price = state.current_bid
            
            if player :
                team.budget -= price
                team.spent += price
                team.players_count += 1
                team.save()
                
                player.is_sold = True
                player.sold_to = team
                player.sold_price = price
                player.save()
                
                TransactionLog.objects.create(auction=event, player_name=player.name, team_name=team.name, amount=price)
                
                state.current_player = None
                state.current_bid = 0
                state.save()

        elif action == 'UNSOLD':
            if state.current_player:
                p = state.current_player
                p.is_unsold = True
                p.save()
                state.current_player = None
                state.save()
        
        elif action == "RESET_UNSOLD":
            players = event.players.filter(is_unsold=True)

            count = players.update(
            is_unsold=False,
            priority_score=0
            )

            return JsonResponse({
                "status": "success",
                "reset_players": count
            })

    return JsonResponse({'status': 'ok'})


def dashboard_view(request): return render(request, 'dashboard.html')


# --- EXPORT FUNCTION ---

def export_csv(request):
    # Get Active Event
    event = AuctionEvent.objects.filter(is_active=True).first()
    if not event: 
        return HttpResponse("No active auction found to export.")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{event.name}_Final_Report.csv"'

    # --- PART 1: SOLD PLAYERS (Grouped by Team) ---
    # We order by 'sold_to__name' so all players of "Team A" appear together
    sold_data = list(event.players.filter(is_sold=True).select_related('sold_to').order_by('sold_to__name', 'name').values(
        Team=F('sold_to__name'),
        Player=F('name'),
        Price=F('sold_price'),
        Position=F('position'),
        Category=F('category'),
        Department=F('department'),
        Year=F('year'),
        Base_Price=F('base_price'),
        Email=F('email')
    ))

    # --- PART 2: UNSOLD PLAYERS ---
    unsold_data = list(event.players.filter(is_unsold=True).order_by('name').values(
        Player=F('name'),
        Position=F('position'),
        Category=F('category'),
        Year=F('year'),
        Department=F('department'),
        Base_Price=F('base_price'),
        Email=F('email')
    ))

    # --- PART 3: REMAINING PLAYERS (Optional, usually good to know) ---
    remaining_data = list(event.players.filter(is_sold=False, is_unsold=False).order_by('name').values(
        Player=F('name'),
        Position=F('position'),
        Base_Price=F('base_price'),
        Category=F('category'),
        Year=F('year'),
        Department=F('department'),

    ))

    # --- BUILD DATAFRAMES ---
    df_sold = pd.DataFrame(sold_data)
    df_unsold = pd.DataFrame(unsold_data)
    df_remaining = pd.DataFrame(remaining_data)

    # Add Status Columns & Fill Missing Data for Alignment
    if not df_sold.empty:
        df_sold['Status'] = 'SOLD'
    
    if not df_unsold.empty:
        df_unsold['Team'] = 'UNSOLD POOL'
        df_unsold['Price'] = 0
        df_unsold['Status'] = 'UNSOLD'

    if not df_remaining.empty:
        df_remaining['Team'] = 'WAITING LIST'
        df_remaining['Price'] = 0
        df_remaining['Status'] = 'PENDING'

    # --- COMBINE IN SPECIFIC ORDER ---
    # 1. Sold (Team A, Team B...) -> 2. Unsold -> 3. Remaining
    final_df = pd.concat([df_sold, df_unsold, df_remaining], ignore_index=True)

    # --- FINAL FORMATTING ---
    if not final_df.empty:
        # Define the exact column order you want in the CSV
        columns_order = [
            'Team', 'Player', 'Price', 'Status', 'year',
            'Position', 'Category', 'Department', 'Base_Price', 'Email'
        ]
        
        # Ensure all columns exist (adds empty cols if missing)
        for col in columns_order:
            if col not in final_df.columns:
                final_df[col] = ''
                
        # Reorder and Fill NaNs (empty cells) with empty string
        final_df = final_df[columns_order].fillna('')

    # Write to Response
    final_df.to_csv(path_or_buf=response, index=False)
    return response

@csrf_exempt
def verify_pin(request):
    if request.method == "POST":
        data = json.loads(request.body)
        pin_attempt = data.get('pin', '')
        
        event = AuctionEvent.objects.filter(is_active=True).first()
        if not event:
            return JsonResponse({'success': False, 'msg': 'No Active Auction'})
            
        if pin_attempt == event.admin_pin:
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'msg': 'Incorrect PIN'})
    return JsonResponse({'success': False})
@csrf_exempt
def toggle_priority(request):
    if request.method == "POST":
        data = json.loads(request.body)
        player_id = data.get('player_id')
        player = get_object_or_404(Player, id=player_id)
        
        # If score is 0, make it 1 (Boosted). If 1, make it 0 (Normal).
        player.priority_score = 1 if player.priority_score == 0 else 0
        player.save()
        
        return JsonResponse({
            'success': True, 
            'is_prioritized': player.priority_score > 0,
            'player_name': player.name
        })
    return JsonResponse({'success': False}, status=400)


@csrf_exempt
def assign_team_roles(request):
    if request.method == "POST":
        data = json.loads(request.body)
        team = get_object_or_404(Team, id=data.get('team_id'))
        team.captain_name = data.get('captain', "")
        team.vice_captain_name = data.get('vice_captain', "")
        team.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)
# views.py


def proxy_image(request):
    url = request.GET.get("url")
    if not url:
        return HttpResponseBadRequest("Missing 'url' parameter")

    # Handle Google Drive links
    if "drive.google.com" in url:
        # Extract file ID from /file/d/<ID>/view
        import re
        match = re.search(r"/d/([^/]+)/", url)
        if match:
            file_id = match.group(1)
            url = f"https://drive.google.com/uc?export=view&id={file_id}"
        else:
            return HttpResponseBadRequest("Invalid Google Drive link")

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        return HttpResponseBadRequest(f"Error fetching image: {e}")

    # Detect content type from response headers
    content_type = resp.headers.get("Content-Type", "image/jpeg")
    response = HttpResponse(resp.content, content_type=content_type)
    response["Access-Control-Allow-Origin"] = "*"   # allow all origins
    return response