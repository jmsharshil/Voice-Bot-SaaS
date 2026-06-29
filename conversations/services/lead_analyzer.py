"""
Post-call LLM Lead Analysis Service.
Analyzes the full conversation transcript after a call ends
and produces a structured lead assessment.
"""
import json
import traceback
from conversations.models import Conversation, Message, LeadAnalysis
from conversations.services.azure_openai_service import generate_response


LEAD_ANALYSIS_PROMPT = """You are an expert sales lead analyst. Analyze the following phone call conversation 
between a voice AI bot and a customer. Provide a structured JSON assessment.

REFERENCE CALL DATE: {call_date}

CONVERSATION TRANSCRIPT:
{transcript}

RULES:
1. Analyze the FULL conversation — every user message matters.
2. Determine the lead level based on user behavior:
   - "hot" → User is clearly interested, asked detailed questions, provided personal details, or agreed to buy/visit.
   - "warm" → User showed moderate interest, asked some questions, but didn't commit or provide details.
   - "cold" → User had minimal interest, gave short replies, or was mostly indifferent.
   - "not_interested" → User explicitly said they don't want the product/service.
3. Extract any user details mentioned in the conversation (name, email, phone, etc.).
4. Identify what product/service the user was interested in.
5. Write a brief 1-2 line summary of the conversation outcome.
6. Extract any appointment date, visit date, or day/time of availability/visit mentioned by the user. If the user mentions relative time expressions (such as "tomorrow", "kal", "parso", "2 din baad", "3 days later", "next week", "Monday", etc.), calculate the exact absolute calendar date and day of the week based on the REFERENCE CALL DATE provided above, and return it in a clear human-readable format (e.g., "Saturday, 27 Jun 2026" or "Monday, 29 Jun 2026 at 4:00 PM").

RESPOND WITH ONLY THIS JSON FORMAT — no extra text, no markdown:
{{
    "lead_level": "hot" | "warm" | "cold" | "not_interested",
    "user_name": "extracted name or empty string",
    "user_email": "extracted email or empty string",
    "user_phone": "extracted phone or empty string",
    "interest_topic": "what product/service they were interested in",
    "summary": "1-2 line summary of the conversation and lead quality",
    "appointment_date": "calculated absolute calendar date and day or empty string"
}}
"""


def analyze_lead(conversation_id):
    """
    Analyze a completed conversation and save lead analysis.
    Called as a background task after call disconnect.
    """
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        messages = Message.objects.filter(conversation=conversation).order_by("created_at")

        if messages.count() < 2:
            print(f"📊 LEAD ANALYSIS: Very short call ({messages.count()} msgs) — updating lead status.")
            LeadAnalysis.objects.update_or_create(
                conversation=conversation,
                defaults={
                    "agent": conversation.agent,
                    "lead_level": "cold",
                    "summary": "Very short call — user hung up during greeting or short exchange.",
                }
            )
            return None

        # Build transcript
        transcript_lines = []
        for msg in messages:
            role = "Customer" if msg.role == "user" else "Bot"
            transcript_lines.append(f"{role}: {msg.text}")
        transcript = "\n".join(transcript_lines)

        # Get call date info as anchor for relative date calculations
        call_date = conversation.started_at.strftime("%A, %d %b %Y") if conversation.started_at else "today"
 
        # Send to LLM
        prompt = LEAD_ANALYSIS_PROMPT.format(transcript=transcript, call_date=call_date)

        raw_response = generate_response(prompt, "Analyze this conversation and return JSON.")

        # Parse JSON from response
        # Clean up response — LLM might wrap in ```json blocks
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()

        analysis = json.loads(cleaned)

        # Validate lead_level
        valid_levels = ["hot", "warm", "cold", "not_interested"]
        lead_level = analysis.get("lead_level", "cold").lower()
        if lead_level not in valid_levels:
            lead_level = "cold"

        # Save to database
        lead, created = LeadAnalysis.objects.update_or_create(
            conversation=conversation,
            defaults={
                "agent": conversation.agent,
                "lead_level": lead_level,
                "user_name": analysis.get("user_name", "")[:255],
                "user_email": analysis.get("user_email", "")[:255],
                "user_phone": analysis.get("user_phone", "")[:50],
                "interest_topic": analysis.get("interest_topic", "")[:255],
                "summary": analysis.get("summary", ""),
                "appointment_date": analysis.get("appointment_date", "")[:255],
                "raw_analysis": analysis,
            }
        )

        status = "created" if created else "updated"
        print(
            f"📊 LEAD ANALYSIS COMPLETE ({status}):\n"
            f"   Level: {lead_level.upper()}\n"
            f"   Name: {lead.user_name or '—'}\n"
            f"   Email: {lead.user_email or '—'}\n"
            f"   Phone: {lead.user_phone or '—'}\n"
            f"   Topic: {lead.interest_topic or '—'}\n"
            f"   Summary: {lead.summary}"
        )
        return lead

    except Conversation.DoesNotExist:
        print(f"❌ LEAD ANALYSIS: Conversation {conversation_id} not found")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ LEAD ANALYSIS: Failed to parse LLM response as JSON: {e}")
        print(f"   Raw response: {raw_response[:300]}")
        return None
    except Exception as e:
        print(f"❌ LEAD ANALYSIS ERROR: {e}")
        traceback.print_exc()
        return None
