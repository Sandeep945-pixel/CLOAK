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
    """Parse JSON from LLM response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text)


def extract_profile(history_text, log_file):
    """Step 1: Extract attributes from all history posts. Builds the user profile."""
    system = load_prompt("system_agent1.txt")
    task = load_prompt("agent1_profile.txt")

    full_prompt = f"{system}\n\n{task}\n\nPost history to analyze:\n\"\"\"\n{history_text}\n\"\"\""

    log("Agent 1 [Profile Build]: Extracting attributes from history...", log_file)
    log(f"Agent 1: Using model {GEMINI_FLASH}", log_file)
    log(f"Agent 1: History length: {len(history_text)} chars", log_file)

    start = time.time()
    response = client.models.generate_content(model=GEMINI_FLASH, contents=full_prompt)
    elapsed = time.time() - start

    log(f"Agent 1: Response in {elapsed:.1f}s ({len(response.text)} chars)", log_file)

    with open(Path(log_file.name).parent / (Path(log_file.name).stem + "_step1_raw.txt"), "w", encoding="utf-8") as f:
        f.write(response.text)

    result = parse_json_response(response.text)

    log(f"\nAgent 1 PROFILE:", log_file)
    log(f"  Total attributes: {result['total_attributes_found']}", log_file)
    log(f"  Overall risk: {result['overall_risk']}", log_file)
    for attr in result.get("attributes", [])[:10]:
        log(f"  [{attr.get('source_post','?'):>6}] {attr['attribute_type']}: {attr['value'][:60]}", log_file)
    if len(result.get("attributes", [])) > 10:
        log(f"  ... and {len(result['attributes']) - 10} more", log_file)

    return result


def extract_draft(draft_text, profile, log_file):
    """Step 2: Extract NEW attributes from draft, given existing profile."""
    system = load_prompt("system_agent1.txt")
    task = load_prompt("agent1_draft.txt")

    # Summarize profile for context
    profile_summary = json.dumps([
        {"type": a["attribute_type"], "value": a["value"], "post": a.get("source_post", "?")}
        for a in profile.get("attributes", [])
    ], indent=2)

    full_prompt = (
        f"{system}\n\n{task}\n\n"
        f"USER'S EXISTING PROFILE (from history posts):\n{profile_summary}\n\n"
        f"NEW DRAFT POST to analyze:\n\"\"\"\n{draft_text}\n\"\"\""
    )

    log("Agent 1 [Draft Extraction]: Finding NEW attributes in draft...", log_file)
    log(f"Agent 1: Profile has {len(profile.get('attributes', []))} existing attributes", log_file)

    start = time.time()
    response = client.models.generate_content(model=GEMINI_FLASH, contents=full_prompt)
    elapsed = time.time() - start

    log(f"Agent 1: Response in {elapsed:.1f}s ({len(response.text)} chars)", log_file)

    with open(Path(log_file.name).parent / (Path(log_file.name).stem + "_step2_raw.txt"), "w", encoding="utf-8") as f:
        f.write(response.text)

    result = parse_json_response(response.text)

    log(f"\nAgent 1 DRAFT ANALYSIS:", log_file)
    new_attrs = result.get("new_attributes", [])
    log(f"  New attributes found: {len(new_attrs)}", log_file)
    for attr in new_attrs:
        log(f"    NEW: {attr['attribute_type']}: {attr['value'][:60]}", log_file)
        interactions = attr.get("interacts_with", [])
        if interactions:
            log(f"         Interacts with: {interactions}", log_file)

    return result
