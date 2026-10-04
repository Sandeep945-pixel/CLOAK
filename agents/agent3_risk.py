from agents.utils import parse_json_response
import sys, json, time, os
sys.path.append(".")
from config import client, GEMINI_FLASH
from datetime import datetime
from pathlib import Path


def load_prompt(name):
    with open(Path(__file__).resolve().parents[1] / "prompts" / name, "r", encoding="utf-8") as f:
        return f.read()


def log(msg, log_file):
    timestamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    log_file.write(line + "\n")


def parse_json_response(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)


def score_risk(draft_text, profile, risk_analysis, log_file):
    """Step 4: Rank phrases in the DRAFT by risk contribution."""
    system = load_prompt("system_agent3.txt")
    task = load_prompt("agent3_risk.txt")

    context = json.dumps({
        "profile_attributes": [
            {"type": a["attribute_type"], "value": a["value"], "post": a.get("source_post", "?")}
            for a in profile.get("attributes", [])
        ],
        "new_draft_attributes": risk_analysis.get("new_attributes",
            [{"draft_attribute": ix.get("draft_attribute", "")}
             for ix in risk_analysis.get("dangerous_interactions", [])]),
        "dangerous_interactions": risk_analysis.get("dangerous_interactions", []),
        "candidate_set_before": risk_analysis.get("candidate_set_before", "?"),
        "candidate_set_after": risk_analysis.get("candidate_set_after", "?"),
        "is_tipping_point": risk_analysis.get("is_tipping_point", False)
    }, indent=2)

    full_prompt = (
        f"{system}\n\n{task}\n\n"
        f"DRAFT POST (the post the user is about to publish):\n\"\"\"\n{draft_text}\n\"\"\"\n\n"
        f"RISK CONTEXT (from prior analysis):\n{context}"
    )

    log("Agent 3 [Phrase Ranker]: Ranking draft phrases by risk...", log_file)
    log(f"Agent 3: Using model {GEMINI_FLASH}", log_file)

    start = time.time()
    response = client.models.generate_content(model=GEMINI_FLASH, contents=full_prompt)
    elapsed = time.time() - start

    log(f"Agent 3: Response in {elapsed:.1f}s ({len(response.text)} chars)", log_file)

    with open(Path(log_file.name).parent / (Path(log_file.name).stem + "_step4_raw.txt"), "w", encoding="utf-8") as f:
        f.write(response.text)

    result = parse_json_response(response.text)

    log(f"\nAgent 3 PHRASE RANKINGS:", log_file)
    for p in result.get("phrase_rankings", [])[:5]:
        log(f"  #{p['rank']}: \"{p['exact_phrase'][:60]}\"", log_file)
        log(f"    Risk: {p['risk_contribution']} | Interacts with: {p.get('interacts_with_history', 'N/A')}", log_file)

    return result
