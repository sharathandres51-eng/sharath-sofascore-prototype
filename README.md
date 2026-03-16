# AI Tactical Breakdown Prototype

Welcome to the AI Tactical Breakdown Prototype — a feature enhancement concept designed to sit on top of existing football data platforms like SofaScore.

While most platforms give you great raw numbers (65% possession, 15 shots), they don't always tell you *the story of the game*. This app takes raw, event-level match data, processes the statistics, and feeds it into a Large Language Model to let you interrogate matches like a tactical analyst.

---

## Enhancements implemented in Assignment 2

The second iteration of the prototype introduced a full conversational analyst layer on top of the original stats UI, along with a complete visual overhaul.

### Conversational Analyst (Ask the Analyst tab)

The single-click report generator from A1 has been replaced with a proper **chat interface** powered by `st.chat_input`. You can now hold a multi-turn conversation about any match.

Every question goes through a **two-stage LLM pipeline** before a response is generated:

1. **Scope classifier** — a cheap GPT-4o-mini call (5 tokens) decides whether the question is within scope (football tactics, match data, player performance). Out-of-scope questions (weather, coding, etc.) are politely declined without triggering the expensive retrieval path.
2. **Intent classifier** — classifies the question into one of five tactical categories and determines whether an inline chart should be rendered alongside the answer.

| Intent category | Inline chart triggered |
|---|---|
| `chance_quality` | xG Timeline |
| `match_dominance` | Shot Map |
| `turning_point` | Event Timeline |
| `player_impact` | Player Involvement |
| `tactical_pattern` | *(text answer only)* |

Chat history is persisted per match via `st.session_state`, and inline charts are re-rendered deterministically on every rerun.

### Retrieval-Augmented Generation (RAG)

Answers are grounded in a **tactical knowledge base** of 8 domain-specific documents covering:

- Positional play (Juego de Posición)
- Pressing & gegenpressing (with PPDA reference values)
- Transition play (positive and negative)
- Counter-attack patterns
- Overloads and numerical superiorities
- Half-space exploitation
- Low block and defensive structure
- Finishing quality vs xG

Each document was substantially expanded in A2 with richer tactical context, Barcelona-specific examples from the 2018/19 La Liga season, and StatsBomb data fingerprints that connect concepts to what is actually measurable in the event data.

Retrieval uses a **FAISS flat L2 index** with `text-embedding-3-small` embeddings. The top-3 retrieved chunks are injected into the GPT-4o-mini prompt as grounding context.

### Visual Insights tab

The Visual Insights tab now has **four on-demand charts**, each rendered only when the user clicks its button (or when the intent classifier determines the chart is relevant to a chat question):

| Chart | What it shows |
|---|---|
| **Shot Map** | Shot locations on a StatsBomb pitch; circle size = xG, gold stars = goals |
| **xG Timeline** | Cumulative xG step curves with area fill; goal moments annotated |
| **Event Timeline** | Goals and substitutions plotted across match minutes |
| **Player Involvement** | Stacked horizontal bars for top 7 players: passes, shots, pressures, tackles |

Charts previously auto-rendered on tab load. They now gate behind `st.session_state` flags (`viz_{match_id}_{chart}`) so they only appear when explicitly requested, and reset cleanly when switching matches.

### Unified colour palette

All charts, pitch maps, and UI stat bars now share a single SofaScore-inspired palette defined in `COLOURS` (in `visualizations.py`) and imported wherever needed:

| Role | Hex |
|---|---|
| Background | `#1a1c2e` deep navy |
| Home team | `#00b04a` SofaScore green |
| Away team | `#5263ff` SofaScore indigo |
| Goal markers | `#FFD700` gold |
| Card surfaces | `#222438` |

### Chart quality improvements

All chart functions were upgraded for a substantially more polished output:

- **xG Timeline:** area fill under curves, horizontal gridlines, rounded `bbox` annotations for goal markers, padded margins
- **Event Timeline:** team-zone colour tints, 15-minute gridlines, `bbox` pill labels for goals, team indicator dots
- **Shot Map:** xG total badge per panel, shot/goal counts in legend, improved scatter edge contrast
- **Player Involvement:** abbreviated player names, x-axis gridlines, total count labels at bar ends
- Global `figure.dpi: 130` and explicit `subplots_adjust` for consistent, crisp output across all figures

---

## Architecture

```
app.py                  ← Streamlit UI (tabs, chat loop, stat comparison)
llm.py                  ← GPT-4o-mini calls: scope classifier, intent classifier, RAG answer
retriever.py            ← FAISS index build + top-k retrieval (cached with @st.cache_resource)
data_processing.py      ← StatsBomb event parsing, match stats, average position pitch map
visualizations.py       ← All 4 chart functions + shared COLOURS palette
knowledge_base/*.txt    ← 8 tactical concept documents used for RAG
```

---

## How to Run Locally

### Prerequisites

- Python 3.10+
- An OpenAI API key (required for scope classification, intent classification, and RAG answers)

### 1. Clone & setup

```bash
git clone https://github.com/sharathandres51-eng/sharath-sofascore-prototype.git
cd sharath-sofascore-prototype
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your API key

```bash
mkdir -p .streamlit
touch .streamlit/secrets.toml
```

Open `secrets.toml` and add:

```toml
OPENAI_API_KEY = "sk-proj-your-api-key-here"
```

### 5. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8502`.

---

### A note on data constraints

This prototype runs on StatsBomb's Free Open Data. For the 2018/19 La Liga season, StatsBomb only publicly released matches featuring Lionel Messi — so the app displays Barcelona matches only for that dataset.
