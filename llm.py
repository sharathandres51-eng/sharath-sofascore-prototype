import json
import os
from openai import OpenAI
import streamlit as st


client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY")))

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
        response = client.chat.completions.create(
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
