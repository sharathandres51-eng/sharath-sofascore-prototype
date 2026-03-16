import streamlit as st
import pandas as pd
from data_processing import get_laliga_1819_info, load_matches, load_events, get_team_logo_url

st.set_page_config(page_title="AI Tactical Breakdown", layout="wide")

header_html = """
<div style="display: flex; align-items: center; gap: 15px; margin-bottom: 5px;">
    <span style="font-size: 1.25em; font-weight: 900; color: #00A3E0; letter-spacing: 0.5px;">SofaScore</span>
    <span style="font-size: 24px; font-weight: 300; color: #666;">×</span>
    <span style="font-size: 1.1em; font-weight: 900; color: #FF4B00; letter-spacing: 1.5px;
                 border: 2.5px solid #FF4B00; padding: 3px 10px; border-radius: 6px; line-height: 1;">
        LaLiga
    </span>
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

# ---------------------------------------------------------
# Sidebar Setup: Pick the team and see their matches
# ---------------------------------------------------------
st.sidebar.header("Configuration")

try:
    with st.spinner("Loading competition data..."):
        comp_id, season_id = get_laliga_1819_info()
    
    with st.spinner("Loading matches..."):
        df_matches = load_matches(comp_id, season_id)
    
    if df_matches.empty:
        st.error("Failed to load matches.")
        st.stop()

    # Quick helper to safely grab the names out of the nested dict
    def extract_home_team(row): return row.get("home_team", {}).get("home_team_name", "Unknown")
    def extract_away_team(row): return row.get("away_team", {}).get("away_team_name", "Unknown")
    
    df_matches["home_team_name"] = df_matches.apply(extract_home_team, axis=1)
    df_matches["away_team_name"] = df_matches.apply(extract_away_team, axis=1)

    # Let the user pick a team from the dropdown. We default to Barcelona since 
    # the free StatsBomb La Liga dataset revolves around Messi's matches.
    all_teams = sorted(list(set(df_matches["home_team_name"].tolist() + df_matches["away_team_name"].tolist())))
    
    try:
        default_idx = all_teams.index("Barcelona")
    except ValueError:
        default_idx = 0
        
    selected_team = st.sidebar.selectbox("Select Team", all_teams, index=default_idx)

    # Filter down to just the matches involving the team they picked
    team_matches = df_matches[
        (df_matches["home_team_name"] == selected_team) | 
        (df_matches["away_team_name"] == selected_team)
    ].copy()

    # Show the newest matches at the top of the list
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
    # State 2: Deep dive into a single match
    st.button("Back to Matches", on_click=go_back)

    # Pulse the chat input bar to draw the user's eye on first load
    st.markdown("""
    <style>
    @keyframes chat-input-pulse {
        0%   { box-shadow: 0 0 0  0px rgba(0, 176, 74, 0.00); }
        50%  { box-shadow: 0 0 0 14px rgba(0, 176, 74, 0.45); }
        100% { box-shadow: 0 0 0 28px rgba(0, 176, 74, 0.00); }
    }
    section[data-testid="stBottom"] > div {
        animation: chat-input-pulse 1.4s ease-out 4;
        border-radius: 14px;
    }
    </style>
    """, unsafe_allow_html=True)

    selected_match_row = df_matches[df_matches["match_id"] == st.session_state["selected_match_id"]].iloc[0]
    match_id = selected_match_row["match_id"]
    
    st.header("Match Overview")

    # Pull out the high-level match info
    home_team = selected_match_row.get("home_team_name", "N/A")
    away_team = selected_match_row.get("away_team_name", "N/A")
    home_score = selected_match_row.get("home_score", 0)
    away_score = selected_match_row.get("away_score", 0)
    match_date = selected_match_row.get("match_date", "N/A")

    # ---------------------------------------------------
    # Huge visual scoreboard at the top
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
    # Grab all the raw event actions and starting lineups for this specific game
    with st.spinner(f"Loading event data and lineups for match {match_id}..."):
        events_data = load_events(match_id)
        from data_processing import load_lineups, plot_average_positions
        lineups = load_lineups(match_id)

    if not events_data:
        st.warning("No event data found for this match.")
    else:
        st.success(f"Successfully loaded {len(events_data)} events!")
        
        # Build a quick dictionary mapping player names to their country flag emojis
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
        
        # We use a custom HTML block here instead of st.bar_chart to replicate 
        # the look of SofaScore's center-originating progress bars
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
                    <div style="flex: 1; display: flex; justify-content: flex-end; background-color: #222438; height: 8px; border-radius: 4px; overflow: hidden;">
                        <div style="width: {p1}%; background-color: {color1}; height: 100%; border-radius: 4px;"></div>
                    </div>
                    <div style="flex: 1; display: flex; justify-content: flex-start; background-color: #222438; height: 8px; border-radius: 4px; overflow: hidden;">
                        <div style="width: {p2}%; background-color: {color2}; height: 100%; border-radius: 4px;"></div>
                    </div>
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)
            
        render_stat_comparison("Shots", match_stats[home_team]["shots"], match_stats[away_team]["shots"], "#00b04a", "#5263ff")
        render_stat_comparison("Expected Goals (xG)", match_stats[home_team]["xg"], match_stats[away_team]["xg"], "#00b04a", "#5263ff")
        render_stat_comparison("Passes", match_stats[home_team]["passes"], match_stats[away_team]["passes"], "#00b04a", "#5263ff")
        render_stat_comparison("Pressures", match_stats[home_team]["pressures"], match_stats[away_team]["pressures"], "#00b04a", "#5263ff")
        render_stat_comparison("Tackles", match_stats[home_team]["tackles"], match_stats[away_team]["tackles"], "#00b04a", "#5263ff")
        
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
                home_lineup_df, away_lineup_df = None, None
                
                # Parse through the nested JSON to pull out the starting 11 for both teams
                for team in lineups:
                    team_name = team.get("team_name")
                    # Grab players who actually have a jersey number to filter out the bench/manager
                    players = [{"Number": p.get("jersey_number"), "Player": f"{player_flags.get(p.get('player_name'), '🏳️')} {p.get('player_name')}"} 
                               for p in team.get("lineup", []) if p.get("jersey_number") is not None]
                    
                    df_players = pd.DataFrame(players).sort_values("Number")
                    df_players["Number"] = df_players["Number"].astype(int)
                    
                    if team_name == home_team:
                        home_lineup_df = df_players
                    elif team_name == away_team:
                        away_lineup_df = df_players
                
                st.markdown("##### Starting Lineups")
                lu_col1, lu_col2 = st.columns(2)
                with lu_col1:
                    if home_lineup_df is not None:
                        st.dataframe(home_lineup_df, hide_index=True, use_container_width=True)
                with lu_col2:
                    if away_lineup_df is not None:
                        st.dataframe(away_lineup_df, hide_index=True, use_container_width=True)
                        
                st.markdown("---")
                
                # Plot the touch maps using mplsoccer
                from visualizations import COLOURS
                fig_home = plot_average_positions(events_data, lineups, home_team, color=COLOURS["home"])
                fig_away = plot_average_positions(events_data, lineups, away_team, color=COLOURS["away"])
                
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

    # ------------------------------------------------------------------
    # AI INSIGHTS — setup shared state and imports before tabs
    # ------------------------------------------------------------------
    import json
    match_stats_json = json.dumps(match_stats, indent=2)

    # Per-match chat history — resets automatically when switching matches
    chat_key = f"chat_history_{match_id}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    from llm import classify_question_scope, classify_question_intent, answer_match_question, VISUAL_MAP
    from visualizations import plot_shot_map, plot_xg_timeline, plot_event_timeline, plot_player_involvement
    from retriever import retrieve

    def _render_intent_chart(visual_type: str):
        """Renders the chart that corresponds to a classified intent."""
        if visual_type == "xg_chart":
            fig = plot_xg_timeline(events_data, home_team, away_team, match_stats)
        elif visual_type == "shot_map":
            fig = plot_shot_map(events_data, home_team, away_team)
        elif visual_type == "event_timeline":
            fig = plot_event_timeline(match_stats, home_team, away_team)
        elif visual_type == "player_chart":
            fig = plot_player_involvement(events_data, home_team, away_team)
        else:
            return
        st.pyplot(fig, use_container_width=True)

    # Chat input lives OUTSIDE the tabs so Streamlit pins it to the
    # viewport bottom rather than rendering it inline within the tab.
    question = st.chat_input("e.g. Was the scoreline a fair reflection of the match?")

    st.markdown("## 🤖 AI Insights")
    tab1, tab2 = st.tabs(["💬 Ask the Analyst", "📊 Visual Insights"])

    # ------------------------------------------------------------------
    # TAB 1 – Ask the Analyst (RAG-powered + scope-classified Q&A)
    # ------------------------------------------------------------------
    with tab1:
        # Scope info box — shows users what's fair game before they type
        with st.expander("ℹ️ What can I ask?", expanded=False):
            st.markdown("""
**In scope ✅**
- Match tactics, formations, and strategy
- Player and team performance in this match
- Statistics: shots, xG, passes, pressures, tackles
- Goals, substitutions, and key match events
- Tactical concepts: pressing, transitions, low block, overloads, half-spaces

**Out of scope ❌**
- Politics, news, or general world knowledge
- Coding, technology, or non-football topics
- Player transfers, personal matters, or off-pitch affairs
- Anything unrelated to this specific match
            """)

        st.markdown(
            "**Example questions:** Was the result fair based on xG? &nbsp;·&nbsp; "
            "Which team dominated tactically? &nbsp;·&nbsp; "
            "Why did the winning team win? &nbsp;·&nbsp; "
            "Which substitution changed the match?"
        )

        st.caption("Use the chat bar at the bottom of the page to ask your question.")

        # Render existing conversation (with chart replay)
        for msg in st.session_state[chat_key]:
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant":
                    visual_type = VISUAL_MAP.get(msg.get("intent") or "")
                    if visual_type:
                        _render_intent_chart(visual_type)
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("sources"):
                    with st.expander("📚 Tactical concepts used in this answer"):
                        for doc in msg["sources"]:
                            st.markdown(f"> {doc[:300]}…")

        # Process a new question submitted via the sticky bottom input
        if question:
            with st.chat_message("user"):
                st.markdown(question)
            st.session_state[chat_key].append({"role": "user", "content": question})

            with st.chat_message("assistant"):
                in_scope, refusal = classify_question_scope(question)

                if not in_scope:
                    answer = refusal
                    retrieved_docs = []
                    intent = None
                    st.markdown(answer)
                else:
                    intent = classify_question_intent(question)
                    visual_type = VISUAL_MAP.get(intent)

                    # Chart first — contextualises the text answer below it
                    if visual_type:
                        with st.spinner("Generating visualisation..."):
                            _render_intent_chart(visual_type)

                    with st.spinner("Retrieving tactical context and generating answer..."):
                        retrieved_docs = retrieve(question, top_k=2)
                        answer = answer_match_question(
                            question=question,
                            match_stats_json=match_stats_json,
                            retrieved_docs=retrieved_docs,
                            home_team=home_team,
                            away_team=away_team,
                            home_score=home_score,
                            away_score=away_score,
                        )
                    st.markdown(answer)
                    if retrieved_docs:
                        with st.expander("📚 Tactical concepts used in this answer"):
                            for doc in retrieved_docs:
                                st.markdown(f"> {doc[:300]}…")

            st.session_state[chat_key].append({
                "role": "assistant",
                "content": answer,
                "sources": retrieved_docs,
                "intent": intent,
            })

    # ------------------------------------------------------------------
    # TAB 2 – Visual Insights
    # ------------------------------------------------------------------
    with tab2:
        st.markdown("Select a chart to generate. Each is computed directly from the match event data.")

        from visualizations import plot_shot_map, plot_xg_timeline, plot_event_timeline

        # --- Shot Map ---
        st.markdown("#### Shot Map")
        st.markdown(
            "Shot locations for both teams. Circle size = xG value; gold stars = goals."
        )
        if st.button("Generate Shot Map", key=f"btn_shot_{match_id}", use_container_width=True):
            st.session_state[f"viz_{match_id}_shot"] = True
        if st.session_state.get(f"viz_{match_id}_shot"):
            with st.spinner("Rendering..."):
                st.pyplot(plot_shot_map(events_data, home_team, away_team), use_container_width=True)

        st.markdown("---")

        # --- xG Timeline ---
        st.markdown("#### Cumulative xG Timeline")
        st.markdown(
            "How xG built up across the 90 minutes. Steep steps = flurries of chances."
        )
        if st.button("Generate xG Timeline", key=f"btn_xg_{match_id}", use_container_width=True):
            st.session_state[f"viz_{match_id}_xg"] = True
        if st.session_state.get(f"viz_{match_id}_xg"):
            with st.spinner("Rendering..."):
                st.pyplot(plot_xg_timeline(events_data, home_team, away_team, match_stats), use_container_width=True)

        st.markdown("---")

        # --- Event Timeline ---
        st.markdown("#### Match Event Timeline")
        st.markdown(
            "Goals and substitutions plotted across match minutes."
        )
        if st.button("Generate Event Timeline", key=f"btn_events_{match_id}", use_container_width=True):
            st.session_state[f"viz_{match_id}_events"] = True
        if st.session_state.get(f"viz_{match_id}_events"):
            with st.spinner("Rendering..."):
                st.pyplot(plot_event_timeline(match_stats, home_team, away_team), use_container_width=True)
