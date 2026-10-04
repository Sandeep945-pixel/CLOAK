"""
Generate user-facing report from pipeline outputs.
Saves both JSON (for evaluation) and TXT (human readable).
"""

import json
import os


def generate_user_report(profile, draft_result, risk, phrases, edits, verification, draft_text, output_dir):
    """Generate the report a user would actually see."""

    # Extract key info
    new_attrs = draft_result.get("new_attributes", [])
    interactions = risk.get("dangerous_interactions", [])
    phrase_rankings = phrases.get("phrase_rankings", [])
    edit_list = edits.get("edits", [])
    
    candidate_before = risk.get("candidate_set_before", "unknown")
    candidate_after = risk.get("candidate_set_after", "unknown")
    candidate_after_edit = verification.get("candidate_set_after", "unknown")
    is_tipping = risk.get("is_tipping_point", False)

    # Determine risk level
    if len(interactions) >= 2 or is_tipping:
        risk_level = "HIGH"
        risk_color = "red"
        risk_message = "Cross-Post Interaction Detected"
    elif len(interactions) == 1:
        risk_level = "MODERATE"
        risk_color = "orange"
        risk_message = "Potential Cross-Post Interaction"
    elif len(new_attrs) > 0:
        risk_level = "LOW"
        risk_color = "yellow"
        risk_message = "New Attributes Detected (minimal interaction)"
    else:
        risk_level = "NO_NEW_RISK_DETECTED"
        risk_color = "green"
        risk_message = "No New Risk Detected"

    # Build user report JSON
    user_report = {
        "notice": "Experimental privacy-awareness output. Model estimates may be wrong; no anonymity or safety guarantee. Use only your own text, fictional examples, or text shared with informed consent.",
        "risk_level": risk_level,
        "risk_message": risk_message,

        "summary": f"This draft reveals {len(new_attrs)} new attribute(s) that interact with your posting history across {len(set(a.get('source_subreddit', a.get('subreddit', '?')) for a in profile.get('attributes', [])))} subreddits.",

        "new_attributes_from_draft": [
            {
                "attribute": a.get("attribute_type", a.get("type", "?")),
                "value": a.get("value", "?"),
                "category": a.get("category", "?"),
                "interacts_with": a.get("interacts_with", []),
                "interaction_reasoning": a.get("interaction_reasoning", "")
            }
            for a in new_attrs
        ],

        "cross_post_interactions": [
            {
                "draft_attribute": ix.get("draft_attribute", "?"),
                "history_attribute": ix.get("history_attribute", "?"),
                "history_post": ix.get("history_post", "?"),
                "combined_narrowing": ix.get("combined_narrowing", "?"),
                "reasoning": ix.get("reasoning", "")
            }
            for ix in interactions
        ],

        "risky_phrases": [
            {
                "rank": p.get("rank", i + 1),
                "phrase": p.get("exact_phrase", "?"),
                "risk_percentage": p.get("risk_contribution", "?"),
                "interacts_with_history": p.get("interacts_with_history", p.get("interacts_with", "?")),
                "suggested_edit": next(
                    (e.get("suggested_edit", "") for e in edit_list
                     if p.get("exact_phrase", "XXX") in e.get("original_phrase", "")),
                    "no edit suggested"
                )
            }
            for i, p in enumerate(phrase_rankings[:5])
        ],

        "suggested_edits": [
            {
                "priority": e.get("priority", i + 1),
                "original": e.get("original_phrase", "?"),
                "edited": e.get("suggested_edit", "?"),
                "edit_type": e.get("edit_type", "?"),
                "what_you_lose": e.get("what_user_loses", "?"),
                "what_you_keep": e.get("what_user_keeps", "?"),
                "breaks_link_with": e.get("breaks_interaction_with", "?")
            }
            for i, e in enumerate(edit_list)
        ],

        "before_after": {
            "risk_before_draft": risk.get("risk_before", "?"),
            "risk_after_draft": risk.get("risk_after", "?"),
            "risk_after_edits": verification.get("risk_after", "unknown"),
            "is_tipping_point": is_tipping,
            "edits_applied": len(edit_list),
            "story_preserved": edits.get("story_preserved", None),
        },

        "original_draft": draft_text,
        "edited_draft": edits.get("edited_post", ""),

        "profile_summary": {
            "total_attributes_in_history": profile.get("total_attributes_found", 0),
            "subreddits_covered": list(set(
                a.get("source_subreddit", "?") for a in profile.get("attributes", [])
                if a.get("source_subreddit")
            )),
            "attribute_categories": {
                "PII": sum(1 for a in profile.get("attributes", []) if a.get("category") == "PII"),
                "SPI": sum(1 for a in profile.get("attributes", []) if a.get("category") == "SPI"),
                "QI": sum(1 for a in profile.get("attributes", []) if a.get("category") == "QI"),
            }
        }
    }

    # Save JSON report
    with open(os.path.join(output_dir, "user_report.json"), "w") as f:
        json.dump(user_report, f, indent=2)

    # Generate human-readable text report
    txt = []
    txt.append("=" * 60)
    txt.append(f"  CLOAK — Pre-Publication Risk Report")
    txt.append("=" * 60)
    txt.append("")

    # Risk level
    txt.append("  " + user_report["notice"])
    txt.append("")
    txt.append(f"  RISK LEVEL: {risk_level}")
    txt.append(f"  {risk_message}")
    txt.append("")

    # Summary
    txt.append(f"  {user_report['summary']}")
    txt.append("")

    # New attributes
    txt.append("-" * 60)
    txt.append("  NEW ATTRIBUTES DETECTED IN YOUR DRAFT")
    txt.append("-" * 60)
    if new_attrs:
        for a in user_report["new_attributes_from_draft"]:
            txt.append(f"  [{a['category']}] {a['value']}")
            if a["interaction_reasoning"]:
                txt.append(f"        ↔ {a['interaction_reasoning'][:80]}")
            txt.append("")
    else:
        txt.append("  No new identifying information was detected by the model; this is not proof of safety.")
        txt.append("")

    # Cross-post interactions
    if interactions:
        txt.append("-" * 60)
        txt.append("  CROSS-POST INTERACTIONS")
        txt.append("-" * 60)
        for ix in user_report["cross_post_interactions"]:
            txt.append(f"  Draft: \"{ix['draft_attribute']}\"")
            txt.append(f"  + History: \"{ix['history_attribute']}\"")
            if ix.get("reasoning"):
                txt.append(f"  = {ix['reasoning'][:80]}")
            txt.append("")

    # Risky phrases
    txt.append("-" * 60)
    txt.append("  RISKY PHRASES IN YOUR DRAFT")
    txt.append("-" * 60)
    for p in user_report["risky_phrases"]:
        txt.append(f"  #{p['rank']}: \"{p['phrase']}\"")
        txt.append(f"        Risk: {p['risk_percentage']}")
        txt.append(f"        Interacts with: {p['interacts_with_history']}")
        txt.append(f"        Suggested edit: \"{p['suggested_edit']}\"")
        txt.append("")

    # Edits
    txt.append("-" * 60)
    txt.append("  SUGGESTED EDITS")
    txt.append("-" * 60)
    for e in user_report["suggested_edits"]:
        txt.append(f"  Edit #{e['priority']} ({e['edit_type']}):")
        txt.append(f"    Before: \"{e['original']}\"")
        txt.append(f"    After:  \"{e['edited']}\"")
        txt.append(f"    Keeps:  {e['what_you_keep']}")
        txt.append(f"    Loses:  {e['what_you_lose']}")
        txt.append("")

    # Before/after
    txt.append("-" * 60)
    txt.append("  BEFORE vs AFTER EDITS")
    txt.append("-" * 60)
    ba = user_report["before_after"]
    txt.append(f"  Risk before draft:   {ba['risk_before_draft']}")
    txt.append(f"  Risk after draft:    {ba['risk_after_draft']}")
    txt.append(f"  Risk after edits:    {ba['risk_after_edits']}")
    txt.append(f"  Is tipping point:    {ba['is_tipping_point']}")
    txt.append(f"  Story preserved:     {ba['story_preserved']}")
    txt.append("")

    # Original vs edited
    txt.append("-" * 60)
    txt.append("  YOUR ORIGINAL DRAFT")
    txt.append("-" * 60)
    txt.append(f"  {user_report['original_draft'][:500]}")
    txt.append("")
    txt.append("-" * 60)
    txt.append("  SUGGESTED VERSION (review before posting)")
    txt.append("-" * 60)
    txt.append(f"  {user_report['edited_draft'][:500]}")
    txt.append("")
    txt.append("=" * 60)
    txt.append("  [Post As-Is]  [Apply Edits]  [Edit Myself]")
    txt.append("=" * 60)

    # Save text report
    with open(os.path.join(output_dir, "user_report.txt"), "w") as f:
        f.write("\n".join(txt))

    return user_report
