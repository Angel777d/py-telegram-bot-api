from typing import Tuple

from telegram_bot_api import MessageEntityType, Message, MessageEntity


def get_value(entity: MessageEntity, text: str) -> str:
	return text[entity.offset:entity.offset + entity.length]


def get_entities_by_type(message: Message, entity_type: MessageEntityType) -> Tuple[str]:
	return tuple(get_value(e, message.text) for e in message.entities if e.type == entity_type)
