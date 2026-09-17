# conversations/services/core/memory_manager.py

from conversations.models import ConversationLog


MEMORY_LIMIT = 6  # last N messages


def load_conversation_history(agent):
    """
    Load last N conversation messages for context.
    Returns formatted text block for LLM.
    """
    logs = (
        ConversationLog.objects
        .filter(agent=agent)
        .order_by("-created_at")[:MEMORY_LIMIT]
    )

    history = []

    for log in reversed(logs):
        history.append(f"User: {log.user_message}")
        history.append(f"Assistant: {log.agent_reply}")

    return "\n".join(history)


def save_conversation(agent, user_message, agent_reply):
    """
    Save conversation turn.
    """
    ConversationLog.objects.create(
        agent=agent,
        user_message=user_message,
        agent_reply=agent_reply
    )