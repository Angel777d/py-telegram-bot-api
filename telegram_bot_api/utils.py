from io import StringIO
from typing import Tuple, Optional, List

from telegram_bot_api import MessageEntityType, Message, MessageEntity, User


def get_value(entity: MessageEntity, text: str) -> str:
	return text[entity.offset:entity.offset + entity.length]


def get_entities(text: str, entities: List[MessageEntity], entity_type: MessageEntityType) -> Tuple[str]:
	return tuple(get_value(e, text) for e in entities if e.type == entity_type) if entities else tuple()


def get_entities_by_type(message: Message, entity_type: MessageEntityType) -> Tuple[str]:
	if not message:
		return tuple()
	return get_entities(message.text, message.entities, entity_type)


class MessageBuilder:
	def __init__(self):
		self.__text: StringIO = StringIO()
		self.__entities: List[MessageEntity] = []

	def append(
			self,
			text: str,
			entity_type: MessageEntityType = MessageEntityType.WRONG,
			url: Optional[str] = None,
			user: Optional[User] = None,
			language: Optional[str] = None
	):
		if entity_type == MessageEntityType.WRONG:
			self.__text.write(text)
			return self
		offset = self.__text.tell()
		entity_text = f'{self.get_prefix(entity_type)}{text}'
		entity = MessageEntity(type=entity_type, offset=offset, length=len(entity_text))
		if url:
			assert entity_type == MessageEntityType.TEXT_LINK, "url allowed for 'text_link' only"
			entity.url = url
		if user:
			assert entity_type == MessageEntityType.TEXT_MENTION, "User allowed for 'mention' only"
			entity.user = user
		if language:
			assert entity_type == MessageEntityType.PRE, "language allowed for 'pre' only"
			entity.language = language
		self.__text.write(entity_text)
		self.__entities.append(entity)
		return self

	@staticmethod
	def get_prefix(entity_type: MessageEntityType):
		if entity_type == MessageEntityType.BOT_COMMAND:
			return "/"
		if entity_type == MessageEntityType.CASHTAG:
			return "$"
		if entity_type == MessageEntityType.HASHTAG:
			return "#"
		if entity_type == MessageEntityType.MENTION:
			return "@"
		if entity_type == MessageEntityType.TEXT_MENTION:
			return "@"
		return ""

	def get(self) -> Tuple[str, List[MessageEntity]]:
		return self.__text.getvalue(), self.__entities
