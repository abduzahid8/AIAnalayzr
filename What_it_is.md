The Core Architecture {1}: of the Vigil platform is defined by its Multi-Agent Relay, a design pattern where specialized AI agents operate in a high-speed, synchronized sequence to transform raw data into executive strategy. Unlike a single-model chatbot, Vigil uses a "divide and conquer" approach to risk assessment.

Here is the detailed breakdown of how the architecture is structured and how the relay functions:
1. The Orchestration Layer (The "Brain")

The architecture starts with the Orchestrator, which acts as the system's "Lead Project Manager."

    Intent-Based Routing: When a user provides a company profile (e.g., "A Series B fintech startup in Southeast Asia"), the Orchestrator classifies the intent and determines the specific "risk vectors" required.

    Task Decomposition: It breaks the high-level request into sub-tasks for the specialized agents.

    Model Selection: It dynamically chooses between Claude 4.6 Opus (for high-reasoning synthesis) and Claude 4.6 Sonnet (for rapid data extraction) via the AIML API.

2. The Specialized Agent Relay (The "Workers")

The 8 agents work in a specific sequence, where each agent's output enriches the "Global State" (Blackboard) for the next.
Agent	Function	Relay Role
1. Orchestrator	Dispatcher	Initializes the session and routes the first tasks.
2. Signal Harvester	Data Ingestion	Ingests live numeric data (VIX, S&P 500, sector ETFs).
3. Narrative Intel	Sentiment Analysis	Scans news headlines/FUD to detect qualitative shifts.
4. Macro Watchdog	Economic Context	Layers in interest rates, CPI, and geopolitical triggers.
5. Competitive Intel	Peer Benchmarking	Analyzes competitor volatility and market position.
6. Market Oracle	Predictive Modeling	Compares current signals against historical crash signatures.
7. Risk Synthesizer	Logic Gate	Correlates all data to calculate the 0-100 Risk Score.
8. Strategy Commander	Action Generator	Transforms the risk score into the 30-day playbook.
3. Shared State & Persistent Memory

The "Multi-Agent Relay" is made possible by the complete.dev environment, which solves the problem of "context loss."

    Persistent Workspace: Instead of passing massive text blocks back and forth (which would hit token limits), the agents work in a Shared Workspace.

    Global Blackboard: When the Signal Harvester finds a spike in the VIX, it writes that value to a shared state file. The Market Oracle later reads that specific file to inform its prediction.

    State Recovery: Because the backend is built on FastAPI with session persistence, if the "Strategy Commander" fails at the final step, the system doesn't restart; it resumes exactly where it left off using the saved state.

4. Data Flow: From Raw Signal to Strategy

    Ingestion: Agents 2, 3, and 4 pull raw data from external APIs (Alpha Vantage, FRED, NewsAPI).

    Analysis: Agents 5 and 6 process the raw data into "Insights."

    Synthesis: Agent 7 (The Risk Synthesizer) acts as a Bayesian Logic Gate, ensuring that a "High VIX" signal is only flagged as a "Red Tier" risk if it correlates with "Negative Narrative Sentiment."

    Executive Output: Agent 8 takes the synthesized risk and uses Claude Opus 4.6’s high-order reasoning to write a human-readable 30-day playbook.

Technical Summary

    Total Generation Time: ~90 Seconds.

    Communication Protocol: JSON-based state exchange.

    Safety Logic: The Orchestrator includes "Circuit Breakers" that stop the relay if any agent detects critical misinformation or data gaps.





// 2 Logic Breakdown

The Logic Breakdown of Vigil is designed as a sequential intelligence relay. Instead of one AI trying to do everything, the system breaks "Risk" into eight distinct logical dimensions.

Here is how the system processes a company profile from raw data to a 30-day strategic playbook:
1. The Orchestration Logic (The "Brain")

The Orchestrator is the "Agent 0." Its primary logic is Intent-Based Routing.

    Context Injection: It takes your specific company profile (e.g., "SaaS startup, $2M ARR, focused on the EU market") and "tags" the message with relevant metadata.

    Routing Decision: If the market is experiencing a sudden crash (high VIX), the Orchestrator prioritizes the Market Oracle and Signal Harvester. if the risk is regulatory, it shifts weight to Macro Watchdog.

    Session Persistence: Using the complete.dev environment, the Orchestrator maintains a "Global State" so that Agent 8 knows exactly what Agent 1 discovered without re-reading the entire transcript.

2. The Analytical Agents (The "Silos")

Each agent has a specific Logic Gate it must clear:

    Signal Harvester (Quantitative Logic): Ingests numeric data (VIX, S&P 500, Sector ETFs). Its logic is purely mathematical: Is current volatility exceeding the 30-day moving average?

    Narrative Intel (Qualitative Logic): Scans news headlines and social sentiment. Its logic is semantic: Are people talking about "recession" or "innovation"? It assigns a sentiment polarity score from -1 to +1.

    Macro Watchdog (Contextual Logic): Looks at interest rates, inflation data, and geopolitical triggers. Its logic is global: How do external economic shifts impact this specific company's burn rate or runway?

    Competitive Intel (Relational Logic): Benchmarks the company against its sector. Its logic is comparative: Is the competitor’s volatility lower than ours? Why?

3. The Synthesis Engine (The "Decision Logic")

This is where the platform moves from "data" to "intelligence."

    Market Oracle (Predictive Logic): It takes the outputs of the first four agents and runs a "Probability Tree." It asks: "Given the current VIX (Signal) and the negative sentiment (Narrative), what is the 10-day likelihood of a sector-wide correction?"

    Risk Synthesizer (Mathematical Logic): This agent calculates the 0-100 Risk Score. It uses a weighted formula:
    RiskScore=(Market×0.3)+(Narrative×0.2)+(Macro×0.25)+(Comp×0.25)

    It then assigns the Tier Color:

        GREEN (0-25): Operational as usual.

        YELLOW (26-50): Increased noise; monitor daily.

        ORANGE (51-75): Structural risk identified; hedge positions.

        RED (76-100): Critical threat; immediate defensive action required.

4. The Executive Output (The "Action Logic")

The Strategy Commander is the final logic gate. It converts abstract risks into concrete tasks.

    Task Prioritization: It filters all identified risks to find the "Top 3" based on the highest probability of impact.

    Deadline Logic: It assigns deadlines based on the "Risk Velocity." A "Red" risk might have a 24-hour deadline, while a "Yellow" risk has a 14-day deadline.

    The 30-Day Playbook: This is a chronological roadmap. It breaks the strategy into:

        Days 1-7: Mitigation & Defense.

        Days 8-21: Stabilization & Monitoring.

        Days 22-30: Long-term Strategic Realignment.

Technical Logic (FastAPI + Claude)

    Asynchronous Relay: While the agents work "in sequence," the system uses FastAPI to pre-fetch market data via the Signal Harvester while the Orchestrator is still processing the user's intent, achieving the 90-second report time.

    Claude Opus 4.6 Reasoning: The system uses Opus for the Synthesizer and Commander because those steps require "high-order logic"—the ability to understand that a high VIX might actually be an opportunity for certain types of companies, rather than just a risk.

// 3 The Scoring & Tier Logic 


The Scoring & Tier Logic of Vigil is what transforms raw, fragmented data into a single, high-conviction decision metric. It does not rely on simple averages; instead, it uses a Weighted Synthesis Model that prioritizes hard market data while using qualitative sentiment as a "multiplier."

Here is the detailed breakdown of how Vigil calculates its 0–100 score and assigns the risk tiers.
1. The Scoring Formula: Weighted Bayesian Synthesis

The Risk Synthesizer Agent uses a mathematical framework to aggregate inputs from the upstream agents. The logic is grounded in a weighted formula where different "risk vectors" have different levels of influence:
TotalRiskScore=(M⋅0.35)+(Mc⋅0.25)+(N⋅0.20)+(C⋅0.20)

    M (Market Signal): Numeric volatility (VIX, S&P 500, Sector ETFs).

    Mc (Macro Watchdog): High-level economic indicators (Fed rates, CPI, geopolitical triggers).

    N (Narrative Intel): Sentiment polarity from news and earnings calls (-1 to +1).

    C (Competitive Intel): Benchmark variance against industry rivals.

The "Confidence Multiplier" (Cm​)

A unique feature of Vigil’s logic is that it adjusts the final score based on Agent Consensus. If the Signal Harvester shows high volatility but Narrative Intel shows positive news, the system calculates an Entropy Factor. High entropy (disagreement) reduces the confidence of the score, which can shift the Tier to a "Cautionary" state regardless of the raw number.
2. The Risk Tiers (Color Logic)

The final 0–100 score is mapped to a four-tier visual system. Each tier triggers a different "operational mode" for the Strategy Commander agent.
Tier	Score Range	Logic Criteria	Operational State
GREEN	0 – 25	All signals within standard deviations. Positive sentiment.	Growth & Expansion: Strategy focuses on aggressive scaling.
YELLOW	26 – 50	Market noise detected or minor sectoral shifts.	Watchful Waiting: Strategy focuses on localized monitoring.
ORANGE	51 – 75	Correlation between Market and Macro risks. Sectoral contagion.	Defensive Hedging: Strategy focuses on liquidity preservation.
RED	76 – 100	Market, Macro, and Narrative risks all align (High Convergence).	Crisis Management: Strategy focuses on "Survival & Pivot."
3. Threshold Triggers: How a Score "Jumps"

The logic is not linear. Certain "Critical Triggers" can cause a score to jump tiers instantly:

    The VIX Spike: If the VIX exceeds 30, the system automatically adds a +20 point "Volatility Premium" to the score.

    Sentiment Flip: If the Narrative Intel agent detects a "Sudden Negative Shift" (e.g., a massive geopolitical event), it acts as a 1.5× Multiplier on the existing score.

    Macro Divergence: If the Macro Watchdog detects an interest rate hike that conflicts with the company's current burn rate (from the Profile Data), the risk score is elevated to ORANGE regardless of market stability.



// 4
igil was specifically engineered to address the critical friction points found in institutional and startup-level risk management. While traditional risk assessments are often slow, subjective, and backward-looking, Vigil targets four distinct "pains" that prevent leaders from making fast, data-backed decisions.
1. The "Data Fatigue" Pain (Information Overload)

Financial analysts are currently drowning in "High-Velocity Noise." Between live tickers (VIX, S&P 500), sector-specific ETFs, and a 24/7 news cycle, the human brain cannot correlate these signals in real-time.

    The Problem: Analysts spend 80% of their time gathering data and only 20% analyzing it. By the time the data is "cleaned," the market has already moved.

    The Vigil Solution: The Signal Harvester and Narrative Intel agents automate the "grunt work." They ingest thousands of data points and news headlines per minute, filtering out the noise to present only the correlations that actually impact the company's specific profile.

2. The "Latency" Pain (The Reaction Gap)

In high-volatility environments, a risk report that is 24 hours old is functionally useless.

    The Problem: Traditional "Quarterly Risk Assessments" are static snapshots. They fail to account for "Flash Crashes" or sudden geopolitical shifts (e.g., a sudden interest rate announcement or a viral news story).

    The Vigil Solution: By using Live Market Data synthesized through an 8-agent chain, Vigil provides a dynamic "Risk Score (0-100)" that updates as market conditions change. It shifts the company from a reactive stance (fixing damage) to a proactive stance (hedging before the hit).

3. The "Siloed Intelligence" Pain (Contextual Blindness)

Usually, a company has a "Macro" expert, a "Market" analyst, and a "Competitive" researcher. These three people rarely synthesize their findings into a single coherent truth.

    The Problem: A "Macro" risk (like rising inflation) might be mitigated by a "Competitive" advantage, but if the data is siloed, the executive sees two separate problems instead of one integrated solution.

    The Vigil Solution: The Risk Synthesizer agent acts as a "logic bridge." It forces data from the Macro Watchdog, Market Oracle, and Competitive Intel into a single weighted score. This creates a Unified Truth that accounts for how different risks amplify or cancel each other out.

4. The "Execution Gap" Pain (Analysis Paralysis)

The most common pain for CEOs is receiving a 50-page risk report and asking, "So, what do I actually do on Monday morning?"

    The Problem: Most risk tools provide "Insights" (data descriptions) but fail to provide "Intelligence" (decision support). This leads to Decision Paralysis.

    The Vigil Solution: Vigil is built to be "Action-First." It doesn't just describe a risk; the Strategy Commander agent generates:

        Top 3 Risks ranked by mathematical probability.

        Top 3 Actions with hard deadlines.

        A 30-Day Strategic Playbook that maps out operational survival and growth.

Summary of Value Proposition
Pain Point	Vigil Solution	Outcome
Too much noise	Signal Harvester filters relevant tickers.	Clarity & Focus
Slow reporting	FastAPI + 8-Agent 90-second processing.	Real-time Agility
Siloed data	Risk Synthesizer cross-correlates vectors.	Holistic Vision
Indecision	Strategy Commander gives a 30-day playbook.	Immediate Action