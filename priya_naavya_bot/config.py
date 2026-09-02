# priya_naavya_bot/config.py

AGENT_NAME = "Priya"
COMPANY_NAME = "Naavya.ai (JMS Tech)"
MAX_MESSAGE_LENGTH = 1000
MAX_TURNS = 10

# Dialogue Stages
STAGE_GREET = 1         # Stage 1: Opening 3-Variant Greeting
STAGE_PAIN = 2          # Stage 2: Confirm the Pain (monthly leads & missed leads due to late reply)
STAGE_VALUE = 3         # Stage 3: Value Prop (24/7 calls & WhatsApp instant reply)
STAGE_META_PROOF = 4    # Stage 4: Meta-Proof (Live AI reveal)
STAGE_TRIAL = 5         # Stage 5: Soft CTA (3-day free trial on real leads)
STAGE_BOOK_DEMO = 6     # Stage 6: Book Demo (WhatsApp link + 11 AM Dhruv callback)
STAGE_CLOSING = 7       # Stage 7: Closing with [END_CALL]
