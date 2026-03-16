import json
import os
from openai import OpenAI
import streamlit as st

# ---------------------------------------------------------------------------
# Scope definition — shared by the classifier prompt and the UI info box
# ---------------------------------------------------------------------------
SCOPE_DESCRIPTION = (
    "The assistant is a football tactical analyst for a specific La Liga 2018/19 match. "
    "It can ONLY answer questions about: match tactics and formations, player and team "
    "performance within this specific match, statistics (shots, xG, passes, pressures, "
    "tackles, goals, substitutions), and tactical concepts (pressing, transitions, "
    "low block, overloads, half-spaces, positional play). "
    "It CANNOT answer questions about politics, news, general world knowledge, coding, "
    "technology, other sports, player transfers, personal matters, or anything unrelated "
    "to the football match being analysed."
)


def _get_client():
    try:
        api_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    except Exception:
        api_key = os.environ.get("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)

def classify_question_scope(question: str) -> tuple[bool, str]:
    """
    Lightweight scope gate — runs before the main LLM call.

    Returns (True, '') if the question is on-topic football match analysis,
    or (False, polite_refusal_message) if it falls outside the defined scope.
    Fails open (returns True) if the classifier call itself errors, so a
    network blip never silently swallows a valid question.
    """
    prompt = f"""\
You are a strict scope classifier for a football tactical analysis assistant.

{SCOPE_DESCRIPTION}

User question: "{question}"

Is this question within the assistant's scope?
Reply with exactly one word: YES or NO."""

    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=5,
        )
        verdict = response.choices[0].message.content.strip().upper()
    except Exception:
        return True, ""  # fail open — let the main LLM handle edge cases

    if verdict.startswith("Y"):
        return True, ""

    return False, (
        "I'm a **football tactical analyst** focused solely on this match. ⚽\n\n"
        "I can help with questions about tactics, formations, player performance, xG, "
        "pressing, goals, substitutions, and other match-specific insights — but that "
        "question falls outside my scope. Feel free to ask me something about the game!"
    )


# ---------------------------------------------------------------------------
# Intent classification — maps in-scope questions to visualisation types
# ---------------------------------------------------------------------------
INTENT_CATEGORIES = [
    "chance_quality",   # xG, shot quality, whether the result was fair
    "match_dominance",  # possession, shot volume, who controlled the game
    "turning_point",    # goal/sub timing, when the match shifted
    "player_impact",    # specific player performance or influence
    "tactical_pattern", # formations, pressing, build-up style (text only)
]

VISUAL_MAP = {
    "chance_quality":   "xg_chart",
    "match_dominance":  "shot_map",
    "turning_point":    "event_timeline",
    "player_impact":    "player_chart",
    "tactical_pattern": None,
}


def classify_question_intent(question: str) -> str:
    """
    Classifies an already in-scope question into one of five intent categories.
    Used to decide which (if any) visualisation to render inline in the chat.
    Falls back to 'tactical_pattern' (text-only) on any error.
    """
    prompt = f"""\
Classify the following football match analysis question into exactly one category.

Categories:
- chance_quality   : questions about xG, shot quality, whether the result was fair, goal probability
- match_dominance  : questions about possession, shot volume, which team controlled the game
- turning_point    : questions about when the match shifted, goal timing, substitution impact
- player_impact    : questions about a specific player's performance or influence on the match
- tactical_pattern : questions about formations, pressing systems, build-up style, defensive shape

User question: "{question}"

Return only the category name, nothing else."""

    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10,
        )
        category = response.choices[0].message.content.strip().lower()
        if category in INTENT_CATEGORIES:
            return category
    except Exception:
        pass
    return "tactical_pattern"  # safe fallback — always produces a text answer


def generate_tactical_breakdown(match_stats_json, home_team, away_team, home_score, away_score):
    """
    Takes the structured match stats and asks the LLM to write a tactical breakdown.
    Returns the generated breakdown as a formatted Markdown string.
    """
    
    prompt = f"""
    You are an expert football analyst. I need a clear, professional, post-match tactical breakdown 
    based *only* on the provided event-level match statistics. Do not invent any events that are not supported by the stats.
    
    Match Information:
    {home_team} {home_score} - {away_score} {away_team}
    
    Structured Match Stats Data (JSON):
    {match_stats_json}
    
    Please provide the output formatted cleanly in Markdown, adhering rigidly to the following sections:
    
    ## 1. Match Summary
    A concise 2-3 sentence overview of the match flow, dominant team (if any), and the final result based on the xG and goals.
    
    ## 2. Tactical Structure
    Analyze the attacking and defensive numbers (e.g. shot volume, possession indicators like passes, and defensive actions like pressures/tackles) for both teams. Who controlled the tempo?
    
    ## 3. Turning Point
    Look at the timing of the goals or major flurries of statistical activity (if apparent) to identify when the match shifted. 
    
    ## 4. Substitution Impact
    Examine the substitutions made and infer if they correspond with any shifts in the game's momentum or late goals.
    
    ## 5. Why the Result Happened
    A concluding bulleted list (3 bullet points max) of the decisive factors according to the data (e.g., Clinical finishing despite low xG, high defensive pressure success, reliance on specific key players). Give a nod to the 'Top Involved Players' if relevant.
    """

    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",  # Keeping it on mini for speed and cost efficiency
            messages=[
                {"role": "system", "content": "You are an elite football tactical analyst covering La Liga."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3, # We want the analysis to be factual and consistent, so lower temp is better
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating tactical breakdown: {e}"


def answer_match_question(
    question: str,
    match_stats_json: str,
    retrieved_docs: list[str],
    home_team: str,
    away_team: str,
    home_score: int,
    away_score: int,
) -> str:
    """
    Answers a user's natural language question about a specific match.

    This is the core of the RAG pipeline:
      1. The caller (app.py) retrieves relevant tactical concepts from the
         knowledge base via retriever.py and passes them here as retrieved_docs.
      2. Those concepts are combined with the structured match stats and the
         user's question into a single prompt.
      3. The LLM reasons over all three sources to produce a grounded answer.

    The complexity here is intentional — a simple "ask the LLM about football"
    call would not need the retrieval step. The value is that the answer is
    anchored both in real match data AND in a curated tactical knowledge base,
    making it far more accurate and specific than a generic LLM response.

    Args:
        question         – the user's natural language question
        match_stats_json – JSON string of compute_match_stats() output
        retrieved_docs   – list of relevant knowledge base doc strings (from retriever.py)
        home_team        – home team name
        away_team        – away team name
        home_score       – final home score
        away_score       – final away score

    Returns:
        A concise, data-grounded tactical answer as a string.
    """

    # Format the retrieved tactical concepts cleanly for injection into the prompt
    if retrieved_docs:
        retrieved_text = "\n\n---\n\n".join(retrieved_docs)
    else:
        retrieved_text = "No specific tactical concepts retrieved for this question."

    prompt = f"""
You are a professional football tactical analyst with deep knowledge of La Liga.

Match: {home_team} {home_score} – {away_score} {away_team}

Structured Match Statistics (JSON):
{match_stats_json}

Relevant Football Tactical Concepts (retrieved from knowledge base):
{retrieved_text}

User Question:
{question}

Instructions:
- Ground your answer firmly in the match statistics provided. Reference specific numbers (shots, xG, passes, pressures) where relevant.
- Use the tactical concepts above to frame your explanation — do not ignore them.
- Keep your answer focused and analytical: 3–5 sentences maximum.
- Do not speculate about events not supported by the data.
- Write in a clear, professional tone suitable for a football analytics platform.
"""

    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an elite football tactical analyst. "
                        "Always ground your answers in the match data and tactical concepts provided. "
                        "Never fabricate statistics or events."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,  # Low temp keeps the analysis factual and consistent
            max_tokens=400,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating answer: {e}"
