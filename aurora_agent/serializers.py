from .models import AgentConversation, AgentMessage


def message_to_dict(message: AgentMessage):
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "metadata": message.metadata or {},
        "created_at": message.created_at.isoformat(),
    }


def conversation_to_dict(conversation: AgentConversation, include_messages=False):
    data = {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }
    if include_messages:
        data["messages"] = [message_to_dict(message) for message in conversation.messages.all()]
    return data
