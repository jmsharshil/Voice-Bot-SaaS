# from typing import Optional


# class ResponseFormatter:
#     """
#     Humanized response formatter.
#     Keeps replies natural, warm, and professional.
#     """

#     GENERIC_FALLBACK = "I’m here to help. Let me know what you’d like to know."

#     @staticmethod
#     def format(
#         raw_response: str,
#         *,
#         strategy_type: str,
#         intent: Optional[str] = None,
#         agent_name: Optional[str] = None
#     ) -> str:

#         if not raw_response:
#             return ResponseFormatter.GENERIC_FALLBACK

#         text = raw_response.strip()

#         if strategy_type == "information":
#             return ResponseFormatter._information_style(text)

#         if strategy_type == "transaction":
#             return ResponseFormatter._transaction_style(text)

#         if strategy_type == "qualification":
#             return ResponseFormatter._qualification_style(text)

#         return text

#     # --------------------
#     # HUMANIZED STYLES
#     # --------------------

#     @staticmethod
#     def _information_style(text: str) -> str:
#         opening = "Sure — here’s what I found:"
#         closing = "If you’d like more details or help with the next step, just let me know."

#         return ResponseFormatter._compose(text, opening, closing)

#     @staticmethod
#     def _transaction_style(text: str) -> str:
#         opening = "Sure, I can help with that."
#         closing = "Just tell me how you’d like to continue."

#         return ResponseFormatter._compose(text, opening, closing)

#     @staticmethod
#     def _qualification_style(text: str) -> str:
#         opening = "Got it, thanks for sharing."
#         closing = "I can suggest the best option once I know a bit more."

#         return ResponseFormatter._compose(text, opening, closing)

#     # --------------------
#     # COMPOSER
#     # --------------------

#     @staticmethod
#     def _compose(body: str, opening: str, closing: str) -> str:
#         parts = []

#         # Avoid robotic repetition
#         if not body.lower().startswith(opening.lower()):
#             parts.append(opening)

#         parts.append(body.rstrip())

#         # Gentle punctuation fix
#         if not parts[-1].endswith((".", "!", "?")):
#             parts[-1] += "."

#         # Avoid forcing closing if body already ends naturally
#         if closing.lower() not in body.lower():
#             parts.append(closing)

#         return "\n\n".join(parts)