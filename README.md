# AI Tactical Breakdown Prototype

Welcome to the AI Tactical Breakdown Prototype! 

This project is a feature enhancement concept designed to sit neatly on top of existing football data platforms (like SofaScore). While most platforms give you great raw numbers—like saying a team had 65% possession or 15 shots—they don't always tell you *the story of the game*. 

That's what this app does. It takes raw, event-level match data, processes the statistics, and then feeds it all into a Large Language Model (OpenAI's GPT-4o-mini) to automatically generate a structured, human-readable tactical breakdown of exactly what happened on the pitch.

## Features

- **Interactive UI:** A clean, modern Streamlit interface styled specifically to mimic the feel of premium football apps like SofaScore.
- **Advanced Match Stats:** Go beyond the basics with Expected Goals (xG), passing networks, pressure maps, and defensive duel metrics.
- **Starting Lineups & Visual Pitch Maps:** Get real passing nodes mapped dynamically onto a football pitch to see exactly where players were positioned on average during the game. Uses automated country flags for a polished look!
- **AI-Generated Match Reports:** Just click a button, and the app reads the stats to write a full match flow summary, pinpoint tactical shifts, and explain exactly *why* a team won or lost.

---

## How to Run Locally

Want to fire this up on your own machine? It's super simple. 

### Prerequisites

Make sure you have **Python 3.10+** installed. You will also need an **OpenAI API Key** if you actually want to generate the AI tactical breakdowns at the end of the matches.

### 1. Clone & Setup

First, clone the repository and navigate into the folder:

```bash
git clone https://github.com/sharathandres51-eng/sharath-duolingo-prototype.git
cd sharath-duolingo-prototype
```

### 2. Create a Virtual Environment

It's always best practice to keep your dependencies isolated. Let's create a `.venv` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

With your virtual environment active, install all the required Python packages (like `streamlit`, `pandas`, `mplsoccer`, `openai`, etc.):

```bash
pip install -r requirements.txt
```

### 4. Add Your API Key

To use the AI generation feature, the app needs your OpenAI key. Streamlit manages secrets securely inside a special folder.
Create a `.streamlit` folder and add a `secrets.toml` file:

```bash
mkdir -p .streamlit
touch .streamlit/secrets.toml
```

Open that `secrets.toml` file in your favorite text editor and paste your key in like this:
```toml
OPENAI_API_KEY = "sk-proj-your-api-key-here"
```

### 5. Run the App!

You're all set. Launch the Streamlit server:

```bash
streamlit run app.py
```

The app will pop open automatically in your browser at `http://localhost:8502`. Have fun exploring the matches!

---

### *A Note on Data Constraints*
*This prototype runs strictly on StatsBomb's Free Open Data repository. For the 2018/19 La Liga season, StatsBomb only publicly released matches featuring Lionel Messi. Therefore, the app currently defaults to Barcelona and only displays matches against them for that specific dataset.*
