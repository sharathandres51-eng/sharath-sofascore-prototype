"""
visualizations.py
-----------------
Four chart types for the Visual Insights tab and inline chat rendering:
  1. plot_shot_map          – shot locations for both teams on a pitch
  2. plot_xg_timeline       – cumulative xG curves over match minutes
  3. plot_event_timeline    – goal / substitution markers on a horizontal timeline
  4. plot_player_involvement – stacked bar chart of top player involvement counts
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# ---------------------------------------------------------------------------
# Shared colour palette — SofaScore-inspired dark-navy / green / indigo
# All chart functions reference this dict; import it from other modules too.
# ---------------------------------------------------------------------------
COLOURS = {
    "bg":          "#1a1c2e",   # deep navy (figures, axes, pitch fill)
    "bg_card":     "#222438",   # slightly lighter navy (legends, cards)
    "bg_band":     "#1e2035",   # subtle alternate band for timelines
    "spine":       "#3a3f62",   # axis spines and grid lines
    "pitch_line":  "#3d5065",   # pitch markings
    "home":        "#00b04a",   # SofaScore signature green
    "away":        "#5263ff",   # SofaScore indigo blue
    "goal":        "#FFD700",   # gold goal markers
    "text":        "#ffffff",   # primary labels and titles
    "text_muted":  "#8a9bb5",   # secondary / placeholder text
    "passes":      "#5263ff",   # player chart: passes segment
    "shots":       "#ffa040",   # player chart: shots segment (warm amber)
    "pressures":   "#ff4e8c",   # player chart: pressures segment (coral pink)
    "tackles":     "#00b04a",   # player chart: tackles segment
    "halftime":    "#4a5080",   # half-time divider line
}

# ---------------------------------------------------------------------------
# Global style defaults applied to every figure
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "font.family":        "DejaVu Sans",
    "axes.titleweight":   "bold",
    "axes.labelweight":   "semibold",
    "figure.dpi":         130,
})


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _empty_figure(message: str) -> plt.Figure:
    """
    Returns a styled placeholder figure with a centred italic message.
    Used when a chart cannot be rendered due to insufficient data.
    """
    fig, ax = plt.subplots(figsize=(10, 3))
    fig.patch.set_facecolor(COLOURS["bg"])
    ax.set_facecolor(COLOURS["bg"])
    ax.text(
        0.5, 0.5, message,
        transform=ax.transAxes,
        color=COLOURS["text_muted"], fontsize=13,
        ha="center", va="center", style="italic",
    )
    ax.set_axis_off()
    return fig


def _style_axes(ax, grid: bool = True, grid_axis: str = "y"):
    """Apply consistent spine + grid styling to an axes."""
    ax.set_facecolor(COLOURS["bg"])
    for side, spine in ax.spines.items():
        spine.set_color(COLOURS["spine"])
        spine.set_linewidth(1.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if grid:
        ax.grid(
            axis=grid_axis,
            color=COLOURS["spine"],
            linewidth=0.5,
            linestyle="--",
            alpha=0.4,
        )
        ax.set_axisbelow(True)
    ax.tick_params(colors=COLOURS["text_muted"], labelsize=9.5)


def _legend(ax, **kwargs):
    """Return a consistently styled legend."""
    defaults = dict(
        facecolor=COLOURS["bg_card"],
        edgecolor=COLOURS["spine"],
        labelcolor=COLOURS["text"],
        fontsize=9.5,
        framealpha=0.92,
        borderpad=0.7,
    )
    defaults.update(kwargs)
    return ax.legend(**defaults)


# ---------------------------------------------------------------------------
# 1. Shot Map
# ---------------------------------------------------------------------------
def plot_shot_map(events_data: list, home_team: str, away_team: str):
    """
    Renders shot locations for both teams side-by-side on StatsBomb pitches.
    Circle size scales with xG value; goals are highlighted with a gold star.

    Returns a matplotlib Figure.
    """
    all_shots = [e for e in events_data if e.get("type", {}).get("name") == "Shot"]
    if not all_shots:
        return _empty_figure("No shot data available for this match.")

    from mplsoccer import Pitch

    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5))
    fig.patch.set_facecolor(COLOURS["bg"])
    fig.subplots_adjust(left=0.04, right=0.96, top=0.88, bottom=0.06, wspace=0.08)

    team_cfg = [
        (axes[0], home_team, COLOURS["home"]),
        (axes[1], away_team, COLOURS["away"]),
    ]

    for ax, team, base_color in team_cfg:
        pitch = Pitch(
            pitch_type="statsbomb",
            pitch_color=COLOURS["bg"],
            line_color=COLOURS["pitch_line"],
            line_zorder=2,
            linewidth=1.2,
        )
        pitch.draw(ax=ax)

        shots = [
            e for e in events_data
            if e.get("type", {}).get("name") == "Shot"
            and e.get("team", {}).get("name") == team
        ]
        goals = [s for s in shots if s.get("shot", {}).get("outcome", {}).get("name") == "Goal"]

        for shot in shots:
            loc = shot.get("location", [0, 0])
            xg = shot.get("shot", {}).get("statsbomb_xg", 0.05)
            is_goal = shot.get("shot", {}).get("outcome", {}).get("name") == "Goal"

            pitch.scatter(
                loc[0], loc[1],
                ax=ax,
                color=COLOURS["goal"] if is_goal else base_color,
                edgecolors="#ffffff" if is_goal else COLOURS["bg_card"],
                s=xg * 1400 + 55,
                marker="*" if is_goal else "o",
                alpha=0.9 if is_goal else 0.75,
                zorder=4 if is_goal else 3,
                linewidths=1.0 if is_goal else 0.6,
            )

        from matplotlib.lines import Line2D
        shot_count = len(shots)
        goal_count = len(goals)
        total_xg = sum(s.get("shot", {}).get("statsbomb_xg", 0) for s in shots)

        legend_elements = [
            Line2D([0], [0], marker="o", color="w", markerfacecolor=base_color,
                   markersize=9, label=f"Shot  ({shot_count})", linestyle="None",
                   markeredgecolor=COLOURS["bg_card"], markeredgewidth=0.5),
            Line2D([0], [0], marker="*", color="w", markerfacecolor=COLOURS["goal"],
                   markersize=13, label=f"Goal  ({goal_count})", linestyle="None",
                   markeredgecolor="white", markeredgewidth=0.5),
        ]
        leg = ax.legend(
            handles=legend_elements,
            loc="upper left",
            facecolor=COLOURS["bg_card"],
            edgecolor=COLOURS["spine"],
            labelcolor=COLOURS["text"],
            framealpha=0.92,
            fontsize=9,
            borderpad=0.7,
        )

        ax.set_title(
            f"{team}",
            color=COLOURS["text"], fontsize=13, fontweight="bold", pad=10,
        )
        # xG badge beneath title
        ax.text(
            0.5, 1.02, f"xG: {total_xg:.2f}",
            transform=ax.transAxes,
            color=base_color, fontsize=10, fontweight="semibold",
            ha="center", va="bottom",
        )

    fig.suptitle(
        "Shot Map",
        color=COLOURS["text"], fontsize=15, fontweight="bold", y=0.97,
    )
    return fig


# ---------------------------------------------------------------------------
# 2. Cumulative xG Timeline
# ---------------------------------------------------------------------------
def plot_xg_timeline(events_data: list, home_team: str, away_team: str,
                     match_stats: dict):
    """
    Plots cumulative xG as a step function over match minutes (0–95).
    Fills the area under each curve and annotates goal moments.

    Returns a matplotlib Figure.
    """
    shot_events = [e for e in events_data if e.get("type", {}).get("name") == "Shot"]
    if not shot_events:
        return _empty_figure("No shot data available — xG timeline cannot be rendered.")

    fig, ax = plt.subplots(figsize=(13, 5))
    fig.patch.set_facecolor(COLOURS["bg"])
    fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.13)
    _style_axes(ax, grid=True, grid_axis="y")

    home_xg_by_min: dict[int, float] = {}
    away_xg_by_min: dict[int, float] = {}

    for ev in events_data:
        if ev.get("type", {}).get("name") != "Shot":
            continue
        team = ev.get("team", {}).get("name")
        minute = ev.get("minute", 0)
        xg = ev.get("shot", {}).get("statsbomb_xg", 0.0)

        if team == home_team:
            home_xg_by_min[minute] = home_xg_by_min.get(minute, 0.0) + xg
        elif team == away_team:
            away_xg_by_min[minute] = away_xg_by_min.get(minute, 0.0) + xg

    all_minutes = list(range(0, 96))
    home_cum, away_cum = [], []
    hc, ac = 0.0, 0.0
    for m in all_minutes:
        hc += home_xg_by_min.get(m, 0.0)
        ac += away_xg_by_min.get(m, 0.0)
        home_cum.append(hc)
        away_cum.append(ac)

    # Lines + area fills
    ax.step(all_minutes, home_cum, color=COLOURS["home"], linewidth=2.5,
            label=home_team, where="post", zorder=3)
    ax.fill_between(all_minutes, home_cum, step="post",
                    color=COLOURS["home"], alpha=0.12, zorder=2)

    ax.step(all_minutes, away_cum, color=COLOURS["away"], linewidth=2.5,
            label=away_team, where="post", zorder=3)
    ax.fill_between(all_minutes, away_cum, step="post",
                    color=COLOURS["away"], alpha=0.12, zorder=2)

    y_max = max(ax.get_ylim()[1], 0.1)

    # Half-time divider
    ax.axvline(x=45, color=COLOURS["halftime"], linewidth=1.2,
               linestyle=":", alpha=0.8, zorder=1)
    ax.text(45.6, y_max * 0.04, "HT",
            color=COLOURS["text_muted"], fontsize=8.5, fontstyle="italic")

    # Goal annotations with bbox
    _goal_annotation_y = {home_team: y_max * 0.88, away_team: y_max * 0.70}
    for team, clr, ypos in [
        (home_team, COLOURS["home"], _goal_annotation_y[home_team]),
        (away_team, COLOURS["away"], _goal_annotation_y[away_team]),
    ]:
        for goal in match_stats.get(team, {}).get("goals", []):
            m = goal.get("minute", 0)
            ax.axvline(x=m, color=clr, linewidth=1.0, linestyle="--", alpha=0.55, zorder=1)
            ax.text(
                m + 0.6, ypos, f"⚽ {m}'",
                color=clr, fontsize=8.5, fontweight="semibold",
                bbox=dict(
                    boxstyle="round,pad=0.3", facecolor=COLOURS["bg_card"],
                    edgecolor=clr, linewidth=0.8, alpha=0.85,
                ),
            )

    ax.set_xlabel("Minute", color=COLOURS["text"], fontsize=11, labelpad=6)
    ax.set_ylabel("Cumulative xG", color=COLOURS["text"], fontsize=11, labelpad=6)
    ax.set_title("Cumulative xG Timeline", color=COLOURS["text"],
                 fontsize=14, fontweight="bold", pad=12)
    ax.set_xlim(0, 95)
    ax.tick_params(colors=COLOURS["text_muted"], labelsize=9.5)

    _legend(ax, loc="upper left")
    return fig


# ---------------------------------------------------------------------------
# 3. Event Timeline (goals + substitutions)
# ---------------------------------------------------------------------------
def plot_event_timeline(match_stats: dict, home_team: str, away_team: str):
    """
    Horizontal timeline showing goals (⚽) and substitutions for both teams.
    Home events sit above the axis; away events below.

    Returns a matplotlib Figure.
    """
    fig, ax = plt.subplots(figsize=(14, 4.5))
    fig.patch.set_facecolor(COLOURS["bg"])
    fig.subplots_adjust(left=0.13, right=0.97, top=0.84, bottom=0.16)
    ax.set_facecolor(COLOURS["bg"])

    # Subtle team-zone fills
    ax.axhspan(0, 1.8, color=COLOURS["home"], alpha=0.04, zorder=0)
    ax.axhspan(-1.8, 0, color=COLOURS["away"], alpha=0.04, zorder=0)

    # Minute tick grid
    for m in range(0, 96, 15):
        ax.axvline(x=m, color=COLOURS["spine"], linewidth=0.7,
                   linestyle="--", alpha=0.35, zorder=1)

    # Central timeline bar
    ax.axhline(y=0, color=COLOURS["spine"], linewidth=1.8, zorder=2)

    # Half-time
    ax.axvline(x=45, color=COLOURS["halftime"], linewidth=1.4,
               linestyle=":", alpha=0.85, zorder=2)
    ax.text(45.6, 1.55, "HT",
            color=COLOURS["text_muted"], fontsize=8.5, fontstyle="italic")

    home_color = COLOURS["home"]
    away_color = COLOURS["away"]

    def short_name(full_name):
        parts = full_name.split() if full_name else ["?"]
        return parts[-1]

    # --- Goals ---
    for goal in match_stats.get(home_team, {}).get("goals", []):
        m = goal.get("minute", 0)
        p = short_name(goal.get("player", ""))
        ax.scatter(m, 0.7, color=home_color, s=300, marker="*",
                   edgecolors="white", linewidths=0.6, zorder=5)
        ax.annotate(
            f"⚽  {p}  {m}'", xy=(m, 0.7),
            xytext=(0, 11), textcoords="offset points",
            color=home_color, fontsize=8.5, fontweight="semibold",
            ha="center",
            bbox=dict(boxstyle="round,pad=0.28", facecolor=COLOURS["bg_card"],
                      edgecolor=home_color, linewidth=0.7, alpha=0.88),
        )

    for goal in match_stats.get(away_team, {}).get("goals", []):
        m = goal.get("minute", 0)
        p = short_name(goal.get("player", ""))
        ax.scatter(m, -0.7, color=away_color, s=300, marker="*",
                   edgecolors="white", linewidths=0.6, zorder=5)
        ax.annotate(
            f"⚽  {p}  {m}'", xy=(m, -0.7),
            xytext=(0, -16), textcoords="offset points",
            color=away_color, fontsize=8.5, fontweight="semibold",
            ha="center",
            bbox=dict(boxstyle="round,pad=0.28", facecolor=COLOURS["bg_card"],
                      edgecolor=away_color, linewidth=0.7, alpha=0.88),
        )

    # --- Substitutions ---
    for sub in match_stats.get(home_team, {}).get("subs", []):
        m = sub.get("minute", 0)
        ax.scatter(m, 0.28, color=home_color, s=70, marker="^",
                   alpha=0.72, zorder=4)
        ax.annotate(f"↕ {m}'", xy=(m, 0.28),
                    xytext=(0, 7), textcoords="offset points",
                    color=home_color, fontsize=7.5, ha="center", alpha=0.85)

    for sub in match_stats.get(away_team, {}).get("subs", []):
        m = sub.get("minute", 0)
        ax.scatter(m, -0.28, color=away_color, s=70, marker="v",
                   alpha=0.72, zorder=4)
        ax.annotate(f"↕ {m}'", xy=(m, -0.28),
                    xytext=(0, -13), textcoords="offset points",
                    color=away_color, fontsize=7.5, ha="center", alpha=0.85)

    # Team labels
    ax.text(-2.5, 0.85, home_team,
            color=home_color, fontsize=10, fontweight="bold",
            ha="right", va="center")
    ax.text(-2.5, -0.85, away_team,
            color=away_color, fontsize=10, fontweight="bold",
            ha="right", va="center")

    # Home / Away side indicators (small coloured dots on the far left)
    ax.scatter(-4.5, 0.7, color=home_color, s=60, marker="o", zorder=5)
    ax.scatter(-4.5, -0.7, color=away_color, s=60, marker="o", zorder=5)

    ax.set_xlim(-6, 97)
    ax.set_ylim(-1.85, 1.85)
    ax.set_xlabel("Minute", color=COLOURS["text"], fontsize=11, labelpad=6)
    ax.set_yticks([])
    ax.tick_params(colors=COLOURS["text_muted"], labelsize=9.5)
    ax.set_title("Match Event Timeline", color=COLOURS["text"],
                 fontsize=14, fontweight="bold", pad=10)

    # Styled bottom spine only
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_color(COLOURS["spine"])
    ax.spines["bottom"].set_linewidth(1.2)

    return fig


# ---------------------------------------------------------------------------
# 4. Player Involvement Chart
# ---------------------------------------------------------------------------
def plot_player_involvement(events_data: list, home_team: str, away_team: str) -> plt.Figure:
    """
    Stacked horizontal bar chart showing the top 7 players per team ranked
    by total involvement, broken down by passes, shots, pressures, and tackles.
    Computed fresh from events_data — no dependency on compute_match_stats.

    Returns a matplotlib Figure.
    """
    from collections import defaultdict

    if not events_data:
        return _empty_figure("No event data available for player involvement chart.")

    _TYPE_MAP = {"Pass": "passes", "Shot": "shots", "Pressure": "pressures"}

    def _build_player_stats(team_name: str) -> dict:
        stats = defaultdict(lambda: {"passes": 0, "shots": 0, "pressures": 0, "tackles": 0})
        for ev in events_data:
            if ev.get("team", {}).get("name") != team_name:
                continue
            player = ev.get("player", {}).get("name")
            if not player:
                continue
            ev_type = ev.get("type", {}).get("name", "")
            if ev_type in _TYPE_MAP:
                stats[player][_TYPE_MAP[ev_type]] += 1
            elif ev_type == "Duel":
                if ev.get("duel", {}).get("type", {}).get("name") == "Tackle":
                    stats[player]["tackles"] += 1
        return stats

    def _abbrev(name: str) -> str:
        """'Lionel Messi' → 'L. Messi'"""
        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}. {' '.join(parts[1:])}"
        return name

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    fig.patch.set_facecolor(COLOURS["bg"])
    fig.subplots_adjust(left=0.12, right=0.97, top=0.88, bottom=0.12, wspace=0.35)

    _SEGMENT_COLORS = {
        "passes":    COLOURS["passes"],
        "shots":     COLOURS["shots"],
        "pressures": COLOURS["pressures"],
        "tackles":   COLOURS["tackles"],
    }
    team_cfg = [(axes[0], home_team), (axes[1], away_team)]

    for ax, team in team_cfg:
        _style_axes(ax, grid=True, grid_axis="x")
        stats = _build_player_stats(team)

        if not stats:
            ax.text(0.5, 0.5, "No player data", transform=ax.transAxes,
                    color=COLOURS["text_muted"], ha="center", va="center", style="italic")
            ax.set_axis_off()
            continue

        # Top 7 players by total event count
        sorted_players = sorted(
            stats.items(),
            key=lambda x: sum(x[1].values()),
            reverse=True,
        )[:7]
        players = [_abbrev(p) for p, _ in sorted_players]
        raw_players = [p for p, _ in sorted_players]

        # Stacked horizontal bars
        lefts = [0] * len(players)
        for key, color in _SEGMENT_COLORS.items():
            values = [stats[rp][key] for rp in raw_players]
            bars = ax.barh(players, values, left=lefts, color=color,
                           label=key.capitalize(), height=0.58,
                           edgecolor=COLOURS["bg"], linewidth=0.4)
            lefts = [l + v for l, v in zip(lefts, values)]

        # Total count label at end of bar
        for i, (rp, total_left) in enumerate(zip(raw_players, lefts)):
            if total_left > 0:
                ax.text(total_left + 1, i, str(total_left),
                        color=COLOURS["text_muted"], fontsize=8, va="center")

        ax.set_title(f"{team}", color=COLOURS["text"],
                     fontsize=12, fontweight="bold", pad=8)
        ax.tick_params(colors=COLOURS["text_muted"], labelsize=9)
        ax.set_xlabel("Event count", color=COLOURS["text"], fontsize=10, labelpad=5)
        _legend(ax, loc="lower right", fontsize=8)

    fig.suptitle("Player Involvement", color=COLOURS["text"],
                 fontsize=14, fontweight="bold", y=0.98)
    return fig
