import sys, json, time, os
sys.path.append(".")
from datetime import datetime

from agents.agent1_extractor import extract_profile, extract_draft
from agents.agent2_population import estimate_before_after
from agents.agent3_risk import score_risk
from agents.agent4_editor import suggest_edits
from report_generator import generate_user_report


def run_pipeline(history_path, draft_path, output_dir="outputs"):
    os.makedirs(output_dir, exist_ok=True)

    with open(history_path, "r") as f:
        history = f.read()
    with open(draft_path, "r") as f:
        draft = f.read()

    master_log = open(os.path.join(output_dir, "pipeline_log.txt"), "w")

    def log(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        print(line)
        master_log.write(line + "\n")
        master_log.flush()

    log("=" * 60)
    log("CLOAK — EXPERIMENTAL PRIVACY-AWARENESS ASSISTANT")
    log("Use only your own text, fictional examples, or text shared with informed consent.")
    log("No stalking, identity tracing, surveillance, or mass deanonymization. Estimates are not safety guarantees.")
    log(f"History: {history_path}")
    log(f"Draft:   {draft_path}")
    log(f"Time:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)

    total_start = time.time()

    # ─── STEP 1: Build profile from history ───
    cached_profile = os.path.join(output_dir, "step1_profile.json")
    if os.path.exists(cached_profile):
        log("\n[1/6] PROFILE BUILD — USING CACHED PROFILE (skipping)")
        log("-" * 40)
        with open(cached_profile) as f:
            profile = json.load(f)
        log(f"  Loaded {profile.get('total_attributes_found',0)} cached attributes")
    else:
        log("\n[1/6] PROFILE BUILD — Agent 1 on history (Gemini Flash)")
        log("-" * 40)
        with open(os.path.join(output_dir, "step1_log.txt"), "w") as lf:
            profile = extract_profile(history, lf)
        with open(os.path.join(output_dir, "step1_profile.json"), "w") as f:
            json.dump(profile, f, indent=2)
        log(f"  Found {profile.get('total_attributes_found',0)} attributes from history")
        log(f"  Risk from history alone: {profile.get('overall_risk','unknown')}")

    # ─── STEP 2: Extract NEW attributes from draft ───
    log("\n[2/6] DRAFT EXTRACTION — Agent 1 on draft (Gemini Flash)")
    log("-" * 40)
    with open(os.path.join(output_dir, "step2_log.txt"), "w") as lf:
        draft_result = extract_draft(draft, profile, lf)
    with open(os.path.join(output_dir, "step2_draft.json"), "w") as f:
        json.dump(draft_result, f, indent=2)
    new_count = len(draft_result.get("new_attributes", []))
    log(f"  New attributes from draft: {new_count}")
    if new_count > 0:
        for attr in draft_result["new_attributes"][:5]:
            log(f"    → {attr['attribute_type']}: {attr['value'][:60]}")

    # ─── STEP 3: Risk analysis — before vs after draft ───
    log("\n[3/6] RISK ANALYSIS — Agent 2 before/after (Gemini Pro)")
    log("-" * 40)
    with open(os.path.join(output_dir, "step3_log.txt"), "w") as lf:
        risk = estimate_before_after(profile, draft_result, lf)
    with open(os.path.join(output_dir, "step3_risk.json"), "w") as f:
        json.dump(risk, f, indent=2)
    log(f"  Candidate set BEFORE draft: {risk['candidate_set_before']}")
    log(f"  Candidate set AFTER draft:  {risk['candidate_set_after']}")
    log(f"  Is tipping point: {risk.get('is_tipping_point', 'N/A')}")
    for ix in risk.get("dangerous_interactions", [])[:3]:
        log(f"  Interaction: {ix.get('draft_attribute', '?')} + {ix.get('history_attribute', '?')}")

    # ─── STEP 4: Phrase ranking on draft ───
    log("\n[4/6] PHRASE RANKING — Agent 3 on draft (Gemini Flash)")
    log("-" * 40)
    with open(os.path.join(output_dir, "step4_log.txt"), "w") as lf:
        phrases = score_risk(draft, profile, risk, lf)
    with open(os.path.join(output_dir, "step4_phrases.json"), "w") as f:
        json.dump(phrases, f, indent=2)
    if phrases.get("phrase_rankings"):
        top = phrases["phrase_rankings"][0]
        log(f"  Top threat: \"{top['exact_phrase'][:60]}\"")
        log(f"  Risk contribution: {top['risk_contribution']}")

    # ─── STEP 5: Edit suggestions for draft ───
    log("\n[5/6] EDIT SUGGESTIONS — Agent 4 on draft (Gemini Pro)")
    log("-" * 40)
    with open(os.path.join(output_dir, "step5_log.txt"), "w") as lf:
        edits = suggest_edits(draft, profile, risk, phrases, lf)
    with open(os.path.join(output_dir, "step5_edits.json"), "w") as f:
        json.dump(edits, f, indent=2)
    with open(os.path.join(output_dir, "edited_draft.txt"), "w") as f:
        f.write(edits.get("edited_post", ""))
    log(f"  {edits.get('edits_count', 0)} edits suggested")
    log(f"  Identifiability: {edits.get('original_score', '?')} → {edits.get('edited_score', '?')}")

    # ─── STEP 6: Verify edits ───
    log("\n[6/6] VERIFICATION — re-run Agent 1+2 on edited draft")
    log("-" * 40)
    edited_draft = edits.get("edited_post", draft)
    with open(os.path.join(output_dir, "step6_log.txt"), "w") as lf:
        edited_attrs = extract_draft(edited_draft, profile, lf)
        verify = estimate_before_after(profile, edited_attrs, lf)
    with open(os.path.join(output_dir, "step6_verify.json"), "w") as f:
        json.dump({
            "edited_draft_attributes": edited_attrs,
            "verification": verify
        }, f, indent=2)
    log(f"  After edits — candidate set: {verify['candidate_set_after']}")
    log(f"  Risk reduced: {verify['candidate_set_after'] > risk['candidate_set_after']}")

    # ─── Generate user-facing report ───
    log("\n  Generating user report...")
    user_report = generate_user_report(
        profile, draft_result, risk, phrases, edits, verify, draft, output_dir
    )
    log(f"  User report saved: {output_dir}/user_report.json")
    log(f"  User report saved: {output_dir}/user_report.txt")

    total_time = time.time() - total_start

    # ─── FINAL REPORT ───
    log("\n" + "=" * 60)
    log("FINAL REPORT")
    log("=" * 60)
    log(f"\nPipeline time: {total_time:.1f}s")
    log(f"\nProfile attributes (from history): {profile['total_attributes_found']}")
    log(f"New attributes (from draft): {new_count}")
    log(f"\nCandidate set BEFORE draft:  {risk['candidate_set_before']}")
    log(f"Candidate set AFTER draft:   {risk['candidate_set_after']}")
    log(f"Candidate set AFTER edits:   {verify['candidate_set_after']}")
    log(f"\nIs draft the tipping point?  {risk.get('is_tipping_point', 'N/A')}")
    log(f"Edits suggested: {edits.get('edits_count', 0)}")
    log(f"Risk reduced by edits: {verify['candidate_set_after'] > risk['candidate_set_after']}")

    log(f"\nOUTPUT FILES:")
    log(f"  {output_dir}/user_report.txt         — WHAT THE USER SEES")
    log(f"  {output_dir}/user_report.json        — user report (for evaluation)")
    log(f"  {output_dir}/step1_profile.json      — history attribute profile")
    log(f"  {output_dir}/step2_draft.json        — draft new attributes")
    log(f"  {output_dir}/step3_risk.json         — before/after risk analysis")
    log(f"  {output_dir}/step4_phrases.json      — phrase risk ranking")
    log(f"  {output_dir}/step5_edits.json        — edit suggestions")
    log(f"  {output_dir}/step6_verify.json       — verification of edits")
    log(f"  {output_dir}/edited_draft.txt        — suggested version of draft")
    log(f"  {output_dir}/pipeline_log.txt        — this log")

    master_log.close()

    return {
        "profile": profile,
        "draft_attrs": draft_result,
        "risk": risk,
        "phrases": phrases,
        "edits": edits,
        "verification": verify,
        "user_report": user_report,
        "time": total_time
    }


if __name__ == "__main__":
    # Usage: python pipeline.py data/R00/history.txt data/R00/draft.txt
    # Or:    python pipeline.py data/R00/history.txt data/R00/draft.txt outputs/R00

    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    if len(args) < 2:
        print("Usage: python pipeline.py <history.txt> <draft.txt> [output_dir]")
        print("Example: python pipeline.py data/R00/history.txt data/R00/draft.txt outputs/R00")
        sys.exit(1)

    history_path = args[0]
    draft_path = args[1]
    output_dir = args[2] if len(args) > 2 else "outputs"

    run_pipeline(history_path, draft_path, output_dir)
