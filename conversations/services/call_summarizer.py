"""
Post-Call AI Conversation Summarizer and Intent Tag Classifier Service.
Analyzes full voice call transcripts (supporting Hindi, Gujarati, English, Hinglish, Marathi, etc.)
and generates:
1. Concise 1-2 sentence human-readable call summary.
2. Accurate lead outcome status (INTERESTED, NOT_INTERESTED, CALLBACK, MISMATCH, GENERAL_INQUIRY, NO_ANSWER).
3. Contextual tags (e.g. ['Not Interested', 'Already Bought'], ['Interested', 'Test Drive Scheduled'], ['Callback', 'WhatsApp Details']).
4. Sentiment analysis and extracted entities (product, budget, location, appointment/callback date).
"""

import json
import logging
import re
import threading
from django.db import close_old_connections

logger = logging.getLogger(__name__)

CALL_SUMMARY_PROMPT = """You are an expert sales analyst for an Indian Voice AI system. Analyze the following conversation transcript between a Voice AI Assistant and a Customer.

TRANSCRIPT:
{transcript}

CALL METRICS:
- Customer Name: {customer_name}
- Agent / Business: {agent_name}
- Call Duration: {duration_seconds} seconds
- Additional Context: {extra_context}

YOUR TASK:
Carefully assess what the customer ACTUALLY said in English, Hindi, Gujarati, Hinglish, or Marathi.
Determine whether the customer was genuinely interested, requested a callback, declined/rejected the pitch, or had a neutral inquiry.

CLASSIFICATION CRITERIA FOR "final_status":
- "INTERESTED": The customer explicitly expressed interest to buy/visit/apply, asked about pricing/features/models with buying intent, or agreed to a store visit/test drive/counseling session.
- "NOT_INTERESTED": The customer said no, not interested, already bought another car/phone/service, doesn't need it, hung up after saying no, told bot not to call, or said wrong number.
- "CALLBACK": The customer was busy (e.g. driving, working, in meeting), asked to call back later/tomorrow, or asked to send details/brochures on WhatsApp/SMS.
- "MISMATCH": Customer is looking for a completely different product/job/service that is not offered.
- "GENERAL_INQUIRY": Customer engaged in neutral conversation without expressing clear purchase intent or explicit refusal.
- "NO_ANSWER": No meaningful dialogue occurred (instant hang up, silence, or voicemail).

OUTPUT JSON SCHEMA:
{{
    "call_summary": "1-2 concise, clear sentences summarizing what the customer discussed, their reaction, and the outcome.",
    "final_status": "INTERESTED" | "NOT_INTERESTED" | "CALLBACK" | "MISMATCH" | "GENERAL_INQUIRY" | "NO_ANSWER",
    "tags": ["1 to 3 short contextual tags, e.g. 'Not Interested', 'Already Purchased', 'Test Drive Request', 'WhatsApp Details', 'Price Inquiry', 'Wrong Number'"],
    "sentiment": "POSITIVE" | "NEUTRAL" | "NEGATIVE",
    "product_interest": "Product or vehicle model discussed or empty string",
    "appointment_date": "Any scheduled visit date, interview date, or callback time or empty string",
    "customer_area": "Customer location/city if mentioned or empty string",
    "key_concerns": "Any specific objection or question raised or empty string"
}}

RESPOND ONLY WITH THE RAW VALID JSON OBJECT. Do not include markdown code blocks or additional text.
"""


def _rule_based_fallback_analysis(transcript_text, customer_name="Customer", duration_seconds=0, extra_vars=None):
    """
    Robust multilingual rule-based NLP fallback when Azure OpenAI is unavailable or fails.
    Accurately recognizes Hindi, Gujarati, English, Hinglish, and Marathi phrases.
    """
    text = (transcript_text or "").lower().strip()
    dur = float(duration_seconds or 0)

    # 1. Very short calls or empty transcripts
    if not text or len(text) < 15:
        if dur < 5:
            return {
                "call_summary": "Call disconnected within a few seconds before conversation started.",
                "final_status": "NO_ANSWER",
                "tags": ["Missed / No Answer"],
                "sentiment": "NEUTRAL",
                "product_interest": "",
                "appointment_date": "",
                "customer_area": "",
                "key_concerns": ""
            }
        return {
            "call_summary": f"Call lasted {int(dur)}s with no customer speech or minimal response.",
            "final_status": "NOT_INTERESTED",
            "tags": ["No Customer Speech"],
            "sentiment": "NEUTRAL",
            "product_interest": "",
            "appointment_date": "",
            "customer_area": "",
            "key_concerns": ""
        }

    # 2. Explicit Not Interested / Rejection / Wrong Number / Already Bought
    not_interested_patterns = [
        "not interested", "not_interested", "don't want", "dont want", "no need", "no thanks",
        "wrong number", "stop calling", "do not call", "cut the call", "disconnect", "hung up",
        "nahi chahiye", "nahi lena", "interest nahi hai", "interested nahi", "phone rakho",
        "dusri le li", "dusra le liya", "already bought", "already purchased", "nahi karna",
        "bekaar", "faltu", "time nahi hai mere paas", "kyun phone kiya", "nahi chahiye bhai",
        "koi lena dena nahi", "nathi joiye", "nathi levu", "ras nathi", "jarur nathi",
        "wrong number chhe", "phone muko", "nathi karvu", "leli chhe", "kharidi lidhi",
        "नको आहे", "रुचि नहीं है", "नहीं चाहिए", "નથી જોઈતું", "જરૂર નથી", "રસ નથી"
    ]
    if any(p in text for p in not_interested_patterns):
        tags = ["Not Interested"]
        if any(w in text for w in ["wrong number", "wrong no", "રોંગ નંબર", "गलत नंबर"]):
            tags.append("Wrong Number")
        elif any(w in text for w in ["already bought", "dusri le li", "kharidi lidhi", "already purchased"]):
            tags.append("Already Bought")
        return {
            "call_summary": "Customer answered the call and explicitly stated they are not interested.",
            "final_status": "NOT_INTERESTED",
            "tags": tags,
            "sentiment": "NEGATIVE",
            "product_interest": "",
            "appointment_date": "",
            "customer_area": "",
            "key_concerns": "Customer declined the offer"
        }

    # 3. Callback / Busy / Driving / WhatsApp Request
    callback_patterns = [
        "call back", "callback", "call later", "call me later", "call after", "talk later",
        "call tomorrow", "call in the evening", "busy right now", "driving", "in a meeting",
        "send on whatsapp", "whatsapp pe bhejo", "whatsapp details", "send brochure", "send details",
        "baad me phone", "baad me baat", "kal phone karna", "kal call karo", "sham ko phone",
        "pachi phone karjo", "kale phone", "hamna busy chhu", "driving karu chhu",
        "whatsapp karo", "whatsapp par moklo", "brochure moklo", "details moklo",
        "बाद में बात", "कल फोन करना", "व्हाट्सएप पर भेजें", "પછી ફોન કરજો", "કાલે વાત"
    ]
    if any(p in text for p in callback_patterns):
        tags = ["Callback Requested"]
        if any(w in text for w in ["whatsapp", "brochure", "details", "વોટ્સએપ", "व्हाट्सएप"]):
            tags.append("WhatsApp Details")
        return {
            "call_summary": "Customer was busy or requested a callback / details via WhatsApp.",
            "final_status": "CALLBACK",
            "tags": tags,
            "sentiment": "NEUTRAL",
            "product_interest": "",
            "appointment_date": "Callback requested",
            "customer_area": "",
            "key_concerns": "Requested later follow-up"
        }

    # 4. Clear Interest / High Intent / Store Visit / Test Drive / Booking
    interested_patterns = [
        "interested", "kitna price", "kitne ki hai", "price kya hai", "features kya hai",
        "test drive", "showroom", "store visit", "visit karna hai", "kab aa sakte hai",
        "booking", "book karna hai", "discount milega", "loan ho jayega", "down payment",
        "bhav su chhe", "ketla ma aavshe", "store par aavish", "test drive levi chhe",
        "khareedvu chhe", "booking karvu chhe", "admission levi chhe",
        "टेस्ट ड्राइव", "शोरूम", "खरीदना है", "સ્ટોર વિઝિટ", "ટેસ્ટ ડ્રાઇવ", "ખરીદવું છે"
    ]
    if any(p in text for p in interested_patterns):
        tags = ["Interested"]
        if "test drive" in text or "ટેસ્ટ ડ્રાઇવ" in text:
            tags.append("Test Drive")
        elif "showroom" in text or "store" in text or "સ્ટોર" in text:
            tags.append("Store Visit")
        return {
            "call_summary": "Customer showed positive interest in the product and discussed features/visit.",
            "final_status": "INTERESTED",
            "tags": tags,
            "sentiment": "POSITIVE",
            "product_interest": "",
            "appointment_date": "",
            "customer_area": "",
            "key_concerns": ""
        }

    # 5. Default / Neutral conversation
    return {
        "call_summary": f"Customer answered and engaged in a {int(dur)}s conversation.",
        "final_status": "GENERAL_INQUIRY" if dur >= 15 else "NOT_INTERESTED",
        "tags": ["General Inquiry" if dur >= 15 else "Short Disconnect"],
        "sentiment": "NEUTRAL",
        "product_interest": "",
        "appointment_date": "",
        "customer_area": "",
        "key_concerns": ""
    }


def analyze_call_transcript(transcript, candidate_name="Customer", duration_seconds=0, agent_name="", extra_vars=None):
    """
    Analyzes conversation transcript using Azure OpenAI LLM, with automatic fallback
    to intelligent rule-based NLP if LLM is unavailable.
    """
    clean_tx = (transcript or "").strip()
    dur = float(duration_seconds or 0)
    extra_context_str = json.dumps(extra_vars) if isinstance(extra_vars, dict) else str(extra_vars or "")

    # Quick bypass for 0-duration or empty calls without burning LLM tokens
    if not clean_tx or len(clean_tx) < 15:
        return _rule_based_fallback_analysis(clean_tx, candidate_name, dur, extra_vars)

    try:
        from conversations.services.azure_openai_service import generate_response

        prompt = CALL_SUMMARY_PROMPT.format(
            transcript=clean_tx,
            customer_name=candidate_name or "Customer",
            agent_name=agent_name or "Voice AI Agent",
            duration_seconds=round(dur, 1),
            extra_context=extra_context_str
        )

        raw_llm_out = generate_response(
            system_prompt="You are a precise JSON-only Voice AI sales conversation analyzer.",
            user_message=prompt
        )

        if raw_llm_out:
            cleaned = raw_llm_out.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
                cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)

            valid_statuses = {"INTERESTED", "NOT_INTERESTED", "CALLBACK", "MISMATCH", "GENERAL_INQUIRY", "NO_ANSWER"}
            status = str(parsed.get("final_status") or "").upper().strip()
            if status not in valid_statuses:
                status = "NOT_INTERESTED" if "NOT" in status else ("INTERESTED" if "INT" in status else "GENERAL_INQUIRY")

            tags = parsed.get("tags") or []
            if not isinstance(tags, list):
                tags = [str(tags)] if tags else []

            summary = str(parsed.get("call_summary") or "").strip()
            if not summary:
                summary = f"Call completed ({int(dur)}s) with status {status}."

            return {
                "call_summary": summary,
                "final_status": status,
                "tags": tags[:4],
                "sentiment": str(parsed.get("sentiment") or "NEUTRAL").upper(),
                "product_interest": str(parsed.get("product_interest") or "").strip(),
                "appointment_date": str(parsed.get("appointment_date") or "").strip(),
                "customer_area": str(parsed.get("customer_area") or "").strip(),
                "key_concerns": str(parsed.get("key_concerns") or "").strip(),
            }

    except Exception as err:
        logger.warning(f"⚠️ [CALL SUMMARIZER LLM WARNING]: {err} — falling back to rule-based NLP.")

    return _rule_based_fallback_analysis(clean_tx, candidate_name, dur, extra_vars)


def process_and_save_call_record_summary(call_record_id, async_mode=True):
    """
    Enriches a SarvamCallRecord with AI Call Summary, classified status, and tags.
    Safe for async/background execution without blocking webhook responses.
    """
    def _worker(rec_id):
        close_old_connections()
        try:
            from conversations.models import SarvamCallRecord
            rec = SarvamCallRecord.objects.filter(id=rec_id).first()
            if not rec:
                return

            agent_name = rec.sarvam_agent.name if rec.sarvam_agent else "Sarvam Voice Agent"
            extra_vars = rec.summary if isinstance(rec.summary, dict) else {}

            analysis = analyze_call_transcript(
                transcript=rec.transcript or "",
                candidate_name=rec.candidate_name,
                duration_seconds=rec.duration_seconds,
                agent_name=agent_name,
                extra_vars=extra_vars
            )

            # Preserve existing summary keys and enrich with AI output
            summary_dict = rec.summary if isinstance(rec.summary, dict) else {}
            summary_dict.update({
                "call_summary": analysis["call_summary"],
                "final_status": analysis["final_status"],
                "tags": analysis["tags"],
                "sentiment": analysis["sentiment"],
            })

            if analysis.get("product_interest") and not summary_dict.get("product_interest") and not summary_dict.get("car_model"):
                summary_dict["product_interest"] = analysis["product_interest"]
            if analysis.get("appointment_date"):
                summary_dict["appointment_date"] = analysis["appointment_date"]
            if analysis.get("customer_area") and not summary_dict.get("customer_area"):
                summary_dict["customer_area"] = analysis["customer_area"]
            if analysis.get("key_concerns"):
                summary_dict["key_concerns"] = analysis["key_concerns"]

            rec.summary = summary_dict
            rec.status = analysis["final_status"]
            rec.save(update_fields=["summary", "status", "updated_at", "billed_seconds"])

            logger.info(
                f"🧠 [CALL AI SUMMARY APPLIED]: Record #{rec.id} ({rec.phone_number}) "
                f"-> Status: {rec.status} | Tags: {analysis['tags']} | Summary: {analysis['call_summary'][:60]}..."
            )

        except Exception as e:
            logger.error(f"❌ [CALL AI SUMMARY ERROR]: Record #{rec_id} - {e}", exc_info=True)
        finally:
            close_old_connections()

    if async_mode:
        t = threading.Thread(target=_worker, args=(call_record_id,), daemon=True)
        t.start()
    else:
        _worker(call_record_id)
