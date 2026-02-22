import streamlit as st
import pandas as pd
from data_processing import get_laliga_1819_info, load_matches, load_events, get_team_logo_url

st.set_page_config(page_title="AI Tactical Breakdown", layout="wide")

header_html = """
<div style="display: flex; align-items: center; gap: 15px; margin-bottom: 5px;">
    <img src="https://upload.wikimedia.org/wikipedia/en/0/0d/Sofascorelogo.png" height="28" style="object-fit: contain;">
    <span style="font-size: 28px; font-weight: 300; color: #666;">x</span>
    <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/0/0f/LaLiga_logo_2023.svg/1024px-LaLiga_logo_2023.svg.png" height="32" style="object-fit: contain;">
    <h1 style="margin: 0; padding: 0; font-size: 2.2em; margin-left: 10px;">AI Tactical Breakdown &bull; 2018/19</h1>
</div>
"""
st.markdown(header_html, unsafe_allow_html=True)
st.markdown("A feature enhancement to the existing SofaScore setup, providing structured post-match tactical analysis using open event-level football data.")

@st.cache_data
def get_flag_emoji(country_name):
    if not country_name: return "🏳️"
    
    overrides = {
        "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", 
        "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", 
        "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
        "Northern Ireland": "🇬🇧",
        "Korea Republic": "KR",
        "Côte d'Ivoire": "CI",
        "Bosnia and Herzegovina": "BA",
        "Republic of Ireland": "IE",
        "USA": "US",
        "Russia": "RU",
        "Turkey": "TR",
        "Iran, Islamic Republic of": "IR",
        "Venezuela": "VE",
        "Syria": "SY",
        "Democratic Republic of the Congo": "CD",
        "Serbia": "RS",
        "Croatia": "HR"
    }
    
    val = overrides.get(country_name)
    if not val:
        import pycountry
        try:
            c = pycountry.countries.get(name=country_name)
            if c:
                val = c.alpha_2
            else:
                c = pycountry.countries.search_fuzzy(country_name)[0]
                val = c.alpha_2
        except:
            return "🏳️"
            
    if len(val) == 2:
        return chr(ord(val[0]) + 127397) + chr(ord(val[1]) + 127397)
    return val

# --- Sidebar: Team & Match Selector ---
st.sidebar.header("Configuration")

try:
    with st.spinner("Loading competition data..."):
        comp_id, season_id = get_laliga_1819_info()
    
    with st.spinner("Loading matches..."):
        df_matches = load_matches(comp_id, season_id)
    
    if df_matches.empty:
        st.error("Failed to load matches.")
        st.stop()

    # Create a mapping for easier extraction
    def extract_home_team(row): return row.get("home_team", {}).get("home_team_name", "Unknown")
    def extract_away_team(row): return row.get("away_team", {}).get("away_team_name", "Unknown")
    
    df_matches["home_team_name"] = df_matches.apply(extract_home_team, axis=1)
    df_matches["away_team_name"] = df_matches.apply(extract_away_team, axis=1)

    # 1. Team Selection
    all_teams = sorted(list(set(df_matches["home_team_name"].tolist() + df_matches["away_team_name"].tolist())))
    
    try:
        default_idx = all_teams.index("Barcelona")
    except ValueError:
        default_idx = 0
        
    selected_team = st.sidebar.selectbox("Select Team", all_teams, index=default_idx)

    # 2. Match Selection (Filtered by selected team)
    team_matches = df_matches[
        (df_matches["home_team_name"] == selected_team) | 
        (df_matches["away_team_name"] == selected_team)
    ].copy()

    # Sort matches reverse chronologically (latest to earliest)
    if "match_date" in team_matches.columns:
        team_matches = team_matches.sort_values(by="match_date", ascending=False)

except Exception as e:
    st.sidebar.error(f"Error loading initial data: {e}")
    st.stop()


# --- Session State Management ---
if "selected_match_id" not in st.session_state:
    st.session_state["selected_match_id"] = None
if "selected_team" not in st.session_state:
    st.session_state["selected_team"] = selected_team

# Reset match selection if team changes
if st.session_state["selected_team"] != selected_team:
    st.session_state["selected_match_id"] = None
    st.session_state["selected_team"] = selected_team

def select_match(match_id):
    st.session_state["selected_match_id"] = match_id

def go_back():
    st.session_state["selected_match_id"] = None

# --- Main Area Display Logic ---
if st.session_state["selected_match_id"] is None:
    # State 1: Show Vertical List of Matches for the Selected Team
    st.header(f"Matches for {selected_team}")
    st.markdown("Select a match to view tactical breakdown and advanced stats.")
    
    for i, match in team_matches.iterrows():
        home = match.get("home_team_name", "Unknown")
        away = match.get("away_team_name", "Unknown")
        h_score = match.get("home_score", "-")
        a_score = match.get("away_score", "-")
        date = match.get("match_date", "Unknown Date")
        m_id = match["match_id"]
        
        # Determine W/L/D for the selected team
        result_char = "D"
        result_color = "#6c757d" # grey
        
        if h_score != "-" and a_score != "-":
            h_s = int(h_score)
            a_s = int(a_score)
            if home == selected_team:
                if h_s > a_s:
                    result_char, result_color = "W", "#1ea64b" # green
                elif h_s < a_s:
                    result_char, result_color = "L", "#e62e2e" # red
            else:
                if a_s > h_s:
                    result_char, result_color = "W", "#1ea64b"
                elif a_s < h_s:
                    result_char, result_color = "L", "#e62e2e"
                    
        badge_html = f'<span style="background-color: {result_color}; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; margin-right: 12px; font-size: 0.9em;">{result_char}</span>'
        
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 5, 2], vertical_alignment="center")
            
            with col1:
                st.markdown(f"**{date}**")
            with col2:
                # Safely render HTML explicitly
                st.markdown(f"{badge_html} <span style='font-size: 1.2Mrem; font-weight: 600;'>{home} {h_score} - {a_score} {away}</span>", unsafe_allow_html=True)
            with col3:
                if st.button("View Details", key=f"btn_{m_id}", use_container_width=True):
                    select_match(m_id)
                    st.rerun()

else:
    # State 2: Show Specific Match Details
    st.button("⬅️ Back to Matches", on_click=go_back)
    
    selected_match_row = df_matches[df_matches["match_id"] == st.session_state["selected_match_id"]].iloc[0]
    match_id = selected_match_row["match_id"]
    
    st.header("Match Overview")

    # Extract basic info
    home_team = selected_match_row.get("home_team_name", "N/A")
    away_team = selected_match_row.get("away_team_name", "N/A")
    home_score = selected_match_row.get("home_score", 0)
    away_score = selected_match_row.get("away_score", 0)
    match_date = selected_match_row.get("match_date", "N/A")

    # ---------------------------------------------------
    # MATCH SCOREBOARD
    # ---------------------------------------------------
    st.markdown(f"<p style='text-align: center; color: #888; margin-bottom: 0px;'>La Liga 2018/19 &bull; {match_date}</p>", unsafe_allow_html=True)
    
    scoreboard_html = f"""
    <div style="display: flex; justify-content: center; align-items: center; gap: 2vw; margin-top: 10px; margin-bottom: 20px;">
        <div style="font-size: 2.2em; font-weight: bold; text-align: right; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            {home_team}
        </div>
        <div style="font-size: 3.5em; font-weight: 900; background-color: #1e1e1e; color: #fff; padding: 5px 30px; border-radius: 12px; border: 2px solid #333; line-height: 1.2;">
            {home_score} - {away_score}
        </div>
        <div style="font-size: 2.2em; font-weight: bold; text-align: left; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            {away_team}
        </div>
    </div>
    """
    st.markdown(scoreboard_html, unsafe_allow_html=True)

    st.divider()

    st.subheader("Match Events Data")
    # Load events and lineups for this match
    with st.spinner(f"Loading event data and lineups for match {match_id}..."):
        events_data = load_events(match_id)
        from data_processing import load_lineups, plot_average_positions
        lineups = load_lineups(match_id)

    if not events_data:
        st.warning("No event data found for this match.")
    else:
        st.success(f"Successfully loaded {len(events_data)} events!")
        
        # Build Player-to-Flag dictionary
        player_flags = {}
        if lineups:
            for team in lineups:
                for p in team.get("lineup", []):
                    c_name = p.get("country", {}).get("name", "")
                    player_flags[p.get("player_name")] = get_flag_emoji(c_name)
        
        with st.spinner("Computing match statistics..."):
            from data_processing import compute_match_stats
            match_stats = compute_match_stats(events_data, home_team, away_team)
            
        st.subheader("Team Comparison")
        
        # Helper function for SofaScore style stat bars
        def render_stat_comparison(stat_name, val1, val2, color1="#1D428A", color2="#C8102E"):
            try:
                v1, v2 = float(val1), float(val2)
            except:
                v1, v2 = 0, 0
                
            total = v1 + v2
            if total == 0:
                p1, p2 = 0, 0
            else:
                p1 = (v1 / total) * 100
                p2 = (v2 / total) * 100
                
            html = f"""
            <div style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                    <span style="font-weight: bold; font-size: 1.1em; width: 15%; text-align: left;">
                        {val1 if isinstance(val1, int) else f"{val1:.2f}"}
                    </span>
                    <span style="text-align: center; flex-grow: 1; font-weight: 500; font-size: 1em;">
                        {stat_name}
                    </span>
                    <span style="font-weight: bold; font-size: 1.1em; width: 15%; text-align: right;">
                        {val2 if isinstance(val2, int) else f"{val2:.2f}"}
                    </span>
                </div>
                <div style="display: flex; justify-content: space-between; gap: 10px; align-items: center;">
                    <div style="flex: 1; display: flex; justify-content: flex-end; background-color: #2b2b2b; height: 8px; border-radius: 4px; overflow: hidden;">
                        <div style="width: {p1}%; background-color: {color1}; height: 100%; border-radius: 4px;"></div>
                    </div>
                    <div style="flex: 1; display: flex; justify-content: flex-start; background-color: #2b2b2b; height: 8px; border-radius: 4px; overflow: hidden;">
                        <div style="width: {p2}%; background-color: {color2}; height: 100%; border-radius: 4px;"></div>
                    </div>
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)
            
        render_stat_comparison("Shots", match_stats[home_team]["shots"], match_stats[away_team]["shots"], "#1ea64b", "#4c4cf8")
        render_stat_comparison("Expected Goals (xG)", match_stats[home_team]["xg"], match_stats[away_team]["xg"], "#1ea64b", "#4c4cf8")
        render_stat_comparison("Passes", match_stats[home_team]["passes"], match_stats[away_team]["passes"], "#1ea64b", "#4c4cf8")
        render_stat_comparison("Pressures", match_stats[home_team]["pressures"], match_stats[away_team]["pressures"], "#1ea64b", "#4c4cf8")
        render_stat_comparison("Tackles", match_stats[home_team]["tackles"], match_stats[away_team]["tackles"], "#1ea64b", "#4c4cf8")
        
        st.subheader("Top Involved Players")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown(f"**{home_team}**")
            for player in match_stats[home_team]["top_players"]:
                flag = player_flags.get(player, "🏳️")
                st.markdown(f"- {flag} {player}")
        with col_p2:
            st.markdown(f"**{away_team}**")
            for player in match_stats[away_team]["top_players"]:
                flag = player_flags.get(player, "🏳️")
                st.markdown(f"- {flag} {player}")

        st.divider()
        st.subheader("Average Player Positions")
        
        with st.spinner("Generating pitch maps and lineups..."):
            if lineups:
                # 1. Extract Lineups DataFrames
                home_lineup_df = None
                away_lineup_df = None
                for team in lineups:
                    team_name = team.get("team_name")
                    # Extract players, ensuring jersey number exists
                    players = [{"Number": p.get("jersey_number"), "Player": f"{player_flags.get(p.get('player_name'), '🏳️')} {p.get('player_name')}"} 
                               for p in team.get("lineup", []) if p.get("jersey_number") is not None]
                    
                    df_players = pd.DataFrame(players).sort_values("Number")
                    df_players["Number"] = df_players["Number"].astype(int)
                    
                    if team_name == home_team:
                        home_lineup_df = df_players
                    elif team_name == away_team:
                        away_lineup_df = df_players
                
                # 2. Display Lineups Table
                st.markdown("##### Starting Lineups")
                lu_col1, lu_col2 = st.columns(2)
                with lu_col1:
                    if home_lineup_df is not None:
                        st.dataframe(home_lineup_df, hide_index=True, use_container_width=True)
                with lu_col2:
                    if away_lineup_df is not None:
                        st.dataframe(away_lineup_df, hide_index=True, use_container_width=True)
                        
                st.markdown("---")
                
                # 3. Generate Pitch Maps
                fig_home = plot_average_positions(events_data, lineups, home_team, color="#1D428A")
                fig_away = plot_average_positions(events_data, lineups, away_team, color="#C8102E")
                
                pitch_col1, pitch_col2 = st.columns(2)
                with pitch_col1:
                    if fig_home:
                        st.pyplot(fig_home, use_container_width=True)
                with pitch_col2:
                    if fig_away:
                        st.pyplot(fig_away, use_container_width=True)
            else:
                st.info("Lineup data unavailable for position maps.")

    st.divider()

    if st.button("Generate AI Tactical Breakdown", type="primary", use_container_width=True):
        with st.spinner(f"Analyzing tactics for {home_team} vs {away_team}..."):
            from llm import generate_tactical_breakdown
            import json
            
            # We send the computed stats, converted to a JSON string for the prompt
            match_stats_json = json.dumps(match_stats, indent=2)
            
            breakdown_markdown = generate_tactical_breakdown(
                match_stats_json, home_team, away_team, home_score, away_score
            )
            
            st.markdown("---")
            st.markdown("## 🤖 AI Tactical Breakdown")
            st.markdown(breakdown_markdown)
