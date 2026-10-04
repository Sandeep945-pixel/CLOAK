from agents.utils import parse_json_response
import sys, json, time, os
sys.path.append(".")
from config import client, GEMINI_PRO
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


def suggest_edits(draft_text, profile, risk_analysis, phrase_rankings, log_file):
    """Step 5: Suggest minimal edits to the draft to break cross-post identification."""
    system = load_prompt("system_agent4.txt")
    task = load_prompt("agent4_edit.txt")

    context = json.dumps({
        "phrase_rankings": phrase_rankings.get("phrase_rankings", []),
        "dangerous_interactions": risk_analysis.get("dangerous_interactions", []),
        "candidate_set_before": risk_analysis.get("candidate_set_before", "?"),
        "candidate_set_after": risk_analysis.get("candidate_set_after", "?"),
        "profile_attributes_count": len(profile.get("attributes", []))
    }, indent=2)

    full_prompt = (
        f"{system}\n\n{task}\n\n"
        f"DRAFT POST (edit ONLY this text):\n\"\"\"\n{draft_text}\n\"\"\"\n\n"
        f"RISK ANALYSIS:\n{context}"
    )

    log("Agent 4 [Editor]: Suggesting privacy-preserving edits for draft...", log_file)
    log(f"Agent 4: Using model {GEMINI_PRO}", log_file)

    start = time.time()
    response = client.models.generate_content(model=GEMINI_PRO, contents=full_prompt)
    elapsed = time.time() - start

    log(f"Agent 4: Response in {elapsed:.1f}s ({len(response.text)} chars)", log_file)

    with open(Path(log_file.name).parent / (Path(log_file.name).stem + "_step5_raw.txt"), "w", encoding="utf-8") as f:
        f.write(response.text)

    result = parse_json_response(response.text)

    log(f"\nAgent 4 EDITS:", log_file)
    log(f"  {result.get('edits_count', 0)} edits suggested", log_file)
    for e in result.get("edits", []):
        log(f"  Edit #{e.get('priority', '?')} [{e.get('edit_type', '?')}]:", log_file)
        log(f"    Before: \"{e.get('original_phrase', '')[:60]}\"", log_file)
        log(f"    After:  \"{e.get('suggested_edit', '')[:60]}\"", log_file)

    log(f"\n  Score: {result.get('original_score', '?')} → {result.get('edited_score', '?')}", log_file)
    log(f"  Story preserved: {result.get('story_preserved', '?')}", log_file)

    return result
