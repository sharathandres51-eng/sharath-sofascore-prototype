import requests
import pandas as pd
import streamlit as st

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

def get_team_logo_url(team_name):
    """Returns a logo URL for the given La Liga team. 
    Currently using UI Avatars as a fallback due to network DNS blocking external logo APIs.
    """
    return f"https://ui-avatars.com/api/?name={team_name.replace(' ', '+')}&background=random&size=128"

@st.cache_data
def load_competitions():
    """Fetch all available competitions from StatsBomb open data."""
    url = f"{BASE_URL}/competitions.json"
    response = requests.get(url)
    response.raise_for_status()
    return pd.DataFrame(response.json())

@st.cache_data
def get_laliga_1819_info():
    """Identify competition_id and season_id for La Liga 2018/19."""
    df_comps = load_competitions()
    
    # Filter for La Liga (Spain) and 2018/2019 season
    laliga = df_comps[
        (df_comps["competition_name"] == "La Liga") & 
        (df_comps["season_name"] == "2018/2019")
    ]
    
    if laliga.empty:
        raise ValueError("La Liga 2018/19 not found in StatsBomb open data.")
        
    comp_row = laliga.iloc[0]
    return comp_row["competition_id"], comp_row["season_id"]

@st.cache_data
def load_matches(comp_id, season_id):
    """Load matches for a specific competition and season."""
    url = f"{BASE_URL}/matches/{comp_id}/{season_id}.json"
    response = requests.get(url)
    if response.status_code != 200:
        return pd.DataFrame()
    return pd.DataFrame(response.json())

@st.cache_data
def load_events(match_id):
    """Load all events for a specific match."""
    url = f"{BASE_URL}/events/{match_id}.json"
    response = requests.get(url)
    if response.status_code != 200:
        return []
    return response.json()

def compute_match_stats(events, home_team, away_team):
    """
    Computes structured match statistics from raw StatsBomb event data.
    """
    stats = {
        home_team: {
            "shots": 0, "xg": 0.0, "passes": 0, "goals": [], 
            "subs": [], "pressures": 0, "tackles": 0, "player_events": {}
        },
        away_team: {
            "shots": 0, "xg": 0.0, "passes": 0, "goals": [], 
            "subs": [], "pressures": 0, "tackles": 0, "player_events": {}
        }
    }
    
    for ev in events:
        team = ev.get("team", {}).get("name")
        if team not in stats:
            continue
            
        ev_type = ev.get("type", {}).get("name")
        minute = ev.get("minute")
        player = ev.get("player", {}).get("name")
        
        # Track player involvement
        if player:
            stats[team]["player_events"][player] = stats[team]["player_events"].get(player, 0) + 1
            
        if ev_type == "Shot":
            stats[team]["shots"] += 1
            shot_info = ev.get("shot", {})
            xg = shot_info.get("statsbomb_xg", 0.0)
            stats[team]["xg"] += xg
            
            outcome = shot_info.get("outcome", {}).get("name")
            if outcome == "Goal":
                stats[team]["goals"].append({"minute": minute, "player": player})
                
        elif ev_type == "Pass":
            stats[team]["passes"] += 1
            
        elif ev_type == "Substitution":
            replacement = ev.get("substitution", {}).get("replacement", {}).get("name")
            stats[team]["subs"].append({
                "minute": minute, 
                "out": player, 
                "in": replacement
            })
            
        elif ev_type == "Pressure":
            stats[team]["pressures"] += 1
            
        elif ev_type == "Duel":
            duel_type = ev.get("duel", {}).get("type", {}).get("name")
            if duel_type == "Tackle":
                stats[team]["tackles"] += 1

    # Sort top players
    for t in [home_team, away_team]:
        sorted_players = sorted(stats[t]["player_events"].items(), key=lambda x: x[1], reverse=True)
        stats[t]["top_players"] = [p[0] for p in sorted_players[:3]] # Top 3 players
        del stats[t]["player_events"] # Clean up raw counts

    return stats


@st.cache_data
def load_lineups(match_id):
    """Load lineups for a specific match to get jersey numbers."""
    url = f"{BASE_URL}/lineups/{match_id}.json"
    response = requests.get(url)
    if response.status_code != 200:
        return []
    return response.json()


def plot_average_positions(events, lineups, target_team, color="#1D428A"):
    """
    Plots the average position of the starting XI for a target team.
    Returns a matplotlib figure.
    """
    from mplsoccer import Pitch
    import matplotlib.pyplot as plt
    import numpy as np

    # 1. Get Jersey Numbers
    jersey_nums = {}
    team_lineup = None
    for team in lineups:
        if team.get("team_name") == target_team:
            team_lineup = team.get("lineup", [])
            break
            
    if not team_lineup:
        return None
        
    for p in team_lineup:
        name = p.get("player_name")
        j_num = p.get("jersey_number")
        if name and j_num is not None:
            jersey_nums[name] = str(j_num)

    # 2. Extract Events for Starters
    # We'll use passes and ball receipts to determine "average involvement position"
    player_locs = {}
    for ev in events:
        if ev.get("team", {}).get("name") != target_team:
            continue
            
        # Only use events with locations
        if "location" not in ev:
            continue
            
        player = ev.get("player", {}).get("name")
        if not player or player not in jersey_nums:
            continue
            
        loc = ev["location"]
        if player not in player_locs:
            player_locs[player] = {"x": [], "y": []}
            
        player_locs[player]["x"].append(loc[0])
        player_locs[player]["y"].append(loc[1])

    # 3. Calculate Averages
    avg_locs = []
    for player, locs in player_locs.items():
        if len(locs["x"]) > 5: # Needs a minimum amount of touches to plot
            avg_x = np.mean(locs["x"])
            avg_y = np.mean(locs["y"])
            avg_locs.append({
                "player": player,
                "jersey": jersey_nums[player],
                "x": avg_x,
                "y": avg_y
            })

    # 4. Draw Pitch
    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1E1E1E', line_color='#c7d5cc')
    fig, ax = pitch.draw(figsize=(6, 4))
    fig.patch.set_facecolor('#1E1E1E')
    
    # 5. Plot Nodes
    for p in avg_locs:
        pitch.scatter(p["x"], p["y"], ax=ax, color=color, edgecolors='white', s=500, zorder=2)
        pitch.annotate(p["jersey"], xy=(p["x"], p["y"]), ax=ax, color='white', 
                       va='center', ha='center', fontsize=12, fontweight='bold', zorder=3)
        
    ax.set_title(f"{target_team}", color="white", fontsize=14, loc="center")
    
    return fig
