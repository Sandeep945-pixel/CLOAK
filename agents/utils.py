import json
import re


def parse_json_response(text):
    """Parse JSON from LLM response, handling markdown fences and malformed JSON."""
    text = text.strip()
    
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
    
    cleaned = text[start:end] if start >= 0 else text
    cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    print(f"  WARNING: Could not parse JSON ({len(text)} chars)")
    return {
        "attributes": [], "new_attributes": [], "all_attributes": [],
        "dangerous_combinations": [], "immediate_recognizers": [],
        "sensitive_exposure": [], "cross_post_interactions": [],
        "total_attributes_found": 0, "overall_risk": "parse_error",
        "summary": "JSON parsing failed",
        "phrase_rankings": [],
        "technical_attack_surface": {"search_queries": [], "estimated_time": "N/A"},
        "cross_platform_risk": "unknown", "cross_platform_reasoning": "",
        "edits": [], "edited_post": "", "edits_count": 0, "words_changed": 0,
        "original_score": "unknown", "edited_score": "unknown",
        "story_preserved": True, "emotional_tone_preserved": True,
        "core_question_preserved": True,
        "narrowing_chain_before": [], "narrowing_chain_after": [],
        "candidate_set_before": "unknown", "candidate_set_after": "unknown",
        "is_tipping_point": False, "dangerous_interactions": [],
        "risk_before": "unknown", "risk_after": "unknown",
        "recommendation": "JSON parsing failed",
        "draft_risk_alone": "unknown", "draft_risk_with_history": "unknown",
        "already_known": [], "_parse_error": True
    }