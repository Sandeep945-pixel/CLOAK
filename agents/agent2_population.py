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


def estimate_before_after(profile, draft_result, log_file):
    """Step 3: Compute candidate set BEFORE and AFTER the draft post."""
    system = load_prompt("system_agent2.txt")
    task = load_prompt("agent2_before_after.txt")

    profile_attrs = json.dumps(profile.get("attributes", []), indent=2)
    new_attrs = json.dumps(draft_result.get("new_attributes", []), indent=2)
    combos = json.dumps(profile.get("dangerous_combinations", []), indent=2)

    full_prompt = (
        f"{system}\n\n{task}\n\n"
        f"EXISTING PROFILE ATTRIBUTES (from history):\n{profile_attrs}\n\n"
        f"NEW ATTRIBUTES FROM DRAFT POST:\n{new_attrs}\n\n"
        f"KNOWN DANGEROUS COMBINATIONS (from history):\n{combos}"
    )

    log("Agent 2 [Risk Analyst]: Computing before/after candidate sets...", log_file)
    log(f"Agent 2: Using model {GEMINI_PRO}", log_file)
    log(f"Agent 2: {len(profile.get('attributes', []))} profile attrs + {len(draft_result.get('new_attributes', []))} new attrs", log_file)

    start = time.time()
    response = client.models.generate_content(model=GEMINI_PRO, contents=full_prompt)
    elapsed = time.time() - start

    log(f"Agent 2: Response in {elapsed:.1f}s ({len(response.text)} chars)", log_file)

    with open(Path(log_file.name).parent / (Path(log_file.name).stem + "_step3_raw.txt"), "w", encoding="utf-8") as f:
        f.write(response.text)

    result = parse_json_response(response.text)

    log(f"\nAgent 2 RISK ANALYSIS:", log_file)
    log(f"  Candidate set BEFORE draft: {result.get('candidate_set_before', '?')}", log_file)
    log(f"  Candidate set AFTER draft:  {result.get('candidate_set_after', '?')}", log_file)
    log(f"  Is tipping point: {result.get('is_tipping_point', '?')}", log_file)

    for ix in result.get("dangerous_interactions", []):
        log(f"  INTERACTION: \"{ix.get('draft_attribute', '?')}\" + \"{ix.get('history_attribute', '?')}\"", log_file)
        log(f"    Narrowing: {ix.get('combined_narrowing', '?')}", log_file)

    return result
