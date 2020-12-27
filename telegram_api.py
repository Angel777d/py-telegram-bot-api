import http.client
import json
from threading import Thread, currentThread
from time import sleep
from typing import List, Optional, Callable, Tuple, KeysView
from urllib.parse import urlencode


class DefaultFieldObject:
	def __init__(self, **kwargs):
		self.__data: dict = kwargs
		fill_object(self, kwargs)

	def __repr__(self):
		return f'[DefaultDataClass] data: {self.__data}'

	def get_fields(self) -> KeysView[str]:
		return self.__data.keys()

	def get_source(self) -> dict:
		return self.__data


class InlineQuery(DefaultFieldObject):
	pass


class ChosenInlineResult(DefaultFieldObject):
	pass


class CallbackQuery(DefaultFieldObject):
	pass


class ShippingQuery(DefaultFieldObject):
	pass


class PreCheckoutQuery(DefaultFieldObject):
	pass


class Poll(DefaultFieldObject):
	pass


class PollAnswer(DefaultFieldObject):
	pass


class Contact(DefaultFieldObject):
	pass


class Voice(DefaultFieldObject):
	pass


class VideoNote(DefaultFieldObject):
	pass


class Video(DefaultFieldObject):
	pass


class Sticker(DefaultFieldObject):
	pass


class PhotoSize(DefaultFieldObject):
	pass


class Document(DefaultFieldObject):
	pass


class Audio(DefaultFieldObject):
	pass


class Animation(DefaultFieldObject):
	pass


class PassportData(DefaultFieldObject):
	pass


class SuccessfulPayment(DefaultFieldObject):
	pass


class Invoice(DefaultFieldObject):
	pass


class Location(DefaultFieldObject):
	pass


class Venue(DefaultFieldObject):
	pass


class Game(DefaultFieldObject):
	pass


class Dice(DefaultFieldObject):
	pass


class ChatPermissions(DefaultFieldObject):
	pass


class ChatPhoto(DefaultFieldObject):
	pass


class InlineKeyboardMarkup(DefaultFieldObject):
	pass


# Type of the entity. Can be
class MessageEntityTypes:
	MENTION = "mention"  # “mention” (@username),
	HASHTAG = "hashtag"  # “hashtag” (#hashtag),
	CASHTAG = "cashtag"  # “cashtag” ($USD),
	BOT_COMMAND = "bot_command"  # “bot_command” (/start@jobs_bot),
	URL = "url"  # “url” (https://telegram.org),
	EMAIL = "email"  # “email” (do-not-reply@telegram.org),
	PHONE_NUMBER = "phone_number"  # “phone_number” (+1-212-555-0123),
	BOLD = "bold"  # “bold” (bold text),
	ITALIC = "italic"  # “italic” (italic text),
	UNDERLINE = "underline"  # “underline” (underlined text),
	STRIKETHROUGH = "strikethrough"  # “strikethrough” (strikethrough text),
	CODE = "code"  # “code” (monowidth string),
	PRE = "pre"  # “pre” (monowidth block),
	TEXT_LINK = "text_link"  # “text_link” (for clickable text URLs),
	TEXT_MENTION = "text_mention"  # “text_mention” (for users without usernames)


class MessageEntity(DefaultFieldObject):

	def __init__(self, **kwargs):
		self.type: str = ""
		self.offset: int = 0
		self.length: int = 0

		self.url: Optional[str] = None
		self.user: Optional[User] = None
		self.language: Optional[str] = None

		DefaultFieldObject.__init__(self, **kwargs)


class User(DefaultFieldObject):
	def __init__(self, **kwargs):
		self.id: int = 0
		self.is_bot: bool = False
		self.first_name: str = ""

		self.last_name: Optional[str] = None
		self.username: Optional[str] = None
		self.language_code: Optional[str] = None

		self.can_join_groups: Optional[bool] = None
		self.can_read_all_group_messages: Optional[bool] = None
		self.supports_inline_queries: Optional[bool] = None

		DefaultFieldObject.__init__(self, **kwargs)


class Chat(DefaultFieldObject):
	def __init__(self, **kwargs):
		self.id: int = 0
		self.type: str = ""
		self.title: Optional[str] = None
		self.username: Optional[str] = None
		self.first_name: Optional[str] = None
		self.last_name: Optional[str] = None
		self.photo: Optional[ChatPhoto] = None
		self.description: Optional[str] = None
		self.invite_link: Optional[str] = None
		self.pinned_message: Optional[Message] = None
		self.permissions: Optional[ChatPermissions] = None
		self.slow_mode_delay: Optional[int] = None
		self.sticker_set_name: Optional[str] = None
		self.can_set_sticker_set: Optional[bool] = None

		DefaultFieldObject.__init__(self, **kwargs)


class Message(DefaultFieldObject):
	def __init__(self, **kwargs):
		self.message_id: int = 0
		self.date: int = 0
		self.chat: Chat = Chat()
		self.forward_from: Optional[User] = None
		self.forward_from_chat: Optional[Chat] = None
		self.forward_from_message_id: Optional[int] = None
		self.forward_signature: Optional[str] = None
		self.forward_sender_name: Optional[str] = None
		self.forward_date: Optional[int] = None
		self.reply_to_message: Optional[Message] = None
		self.via_bot: Optional[User] = None
		self.edit_date: Optional[int] = None
		self.media_group_id: Optional[str] = None
		self.author_signature: Optional[str] = None
		self.text: Optional[str] = None
		self.entities: Optional[List[MessageEntity]] = None
		self.animation: Optional[Animation] = None
		self.audio: Optional[Audio] = None
		self.document: Optional[Document] = None
		self.photo: Optional[List[PhotoSize]] = None
		self.sticker: Optional[Sticker] = None
		self.video: Optional[Video] = None
		self.video_note: Optional[VideoNote] = None
		self.voice: Optional[Voice] = None
		self.caption: Optional[str] = None
		self.caption_entities: Optional[List[MessageEntity]] = None
		self.contact: Optional[Contact] = None
		self.dice: Optional[Dice] = None
		self.game: Optional[Game] = None
		self.poll: Optional[Poll] = None
		self.venue: Optional[Venue] = None
		self.location: Optional[Location] = None
		self.new_chat_members: Optional[List[User]] = None
		self.left_chat_member: Optional[User] = None
		self.new_chat_title: Optional[str] = None
		self.new_chat_photo: Optional[List[PhotoSize]] = None
		self.delete_chat_photo: Optional[bool] = None
		self.group_chat_created: Optional[bool] = None
		self.supergroup_chat_created: Optional[bool] = None
		self.channel_chat_created: Optional[bool] = None
		self.migrate_to_chat_id: Optional[int] = None
		self.migrate_from_chat_id: Optional[int] = None
		self.pinned_message: Optional[Message] = None
		self.invoice: Optional[Invoice] = None
		self.successful_payment: Optional[SuccessfulPayment] = None
		self.connected_website: Optional[str] = None
		self.passport_data: Optional[PassportData] = None
		self.reply_markup: Optional[InlineKeyboardMarkup] = None

		DefaultFieldObject.__init__(self, **kwargs)
		# we can't use "from" word in code
		self.from_user: Optional[User] = getattr(self, "from")

	def get_entities_by_type(self, entity_type) -> Tuple[str]:
		r = []
		if self.entities:
			for e in self.entities:
				if e.type == entity_type:
					s: str = self.text[e.offset:e.offset + e.length]
					r.append(s)
		return tuple(r)


class Update(DefaultFieldObject):
	def __init__(self, update_id: int, **kwargs):
		self.__data = kwargs

		self.update_id: int = update_id
		self.message: Optional[Message] = None
		self.edited_message: Optional[Message] = None
		self.channel_post: Optional[Message] = None
		self.edited_channel_post: Optional[Message] = None
		self.inline_query: Optional[InlineQuery] = None
		self.chosen_inline_result: Optional[ChosenInlineResult] = None
		self.callback_query: Optional[CallbackQuery] = None
		self.shipping_query: Optional[ShippingQuery] = None
		self.pre_checkout_query: Optional[PreCheckoutQuery] = None
		self.poll: Optional[Poll] = None
		self.poll_answer: Optional[PollAnswer] = None

		keys = tuple(k for k in kwargs.keys())
		self.update_types: Tuple[str] = keys

		DefaultFieldObject.__init__(self, **kwargs)

	def __repr__(self):
		return f'[Update] update_id: {self.update_id}, type: {self.update_types}, value: {self.__data.values()}'


FIELD_MAP = {
	"message": Message,
	"entities": MessageEntity,
	"reply_to_message": Message,
	"chat": Chat,
	"from": User,
}


def fill_object(target, data):
	for k, v in data.items():
		setattr(target, k, ch_list(k, v))


def ch_list(k, v):
	return [ch_obj(k, a) for a in v] if type(v) is list else ch_obj(k, v)


def ch_obj(k, v):
	return FIELD_MAP.get(k, DefaultFieldObject)(**v) if type(v) is dict else v


def make_optional(params: dict, exclude):
	return {k: v for k, v in params.items() if v is not None and v not in exclude}


class Pooling:
	def __init__(self, api, handler: Callable[[Update], None], update_time: float = 5):
		self.__api: API = api
		self.handler: Callable[[Update], None] = handler
		self.__update_time: float = update_time
		self.__pooling = None
		self.__lastUpdate: int = 0

	def start(self):
		if self.__pooling:
			return

		self.__pooling = Thread(target=self.__request_update)
		self.__pooling.start()
		return self

	def stop(self):
		if not self.__pooling:
			return

		self.__pooling.running = False
		self.__pooling = None

	def __request_update(self):
		while getattr(currentThread(), "running", True):
			# print("request")
			updates = self.__api.get_updates(offset=self.__lastUpdate)
			for update in updates:
				self.__lastUpdate = update.update_id + 1
				if self.handler:
					self.handler(update)
			sleep(self.__update_time)


class API:
	def __init__(self, token: str, host: str = "api.telegram.org"):
		self.__host = host
		self.__token = token

	def __get_url(self, api_method) -> str:
		return f'https://{self.__host}/bot{self.__token}/{api_method}'

	def __make_request(self, api_method, method="POST", **kwargs):
		url = self.__get_url(api_method)
		params = urlencode(kwargs)
		headers = {
			"Content-type": "application/x-www-form-urlencoded",
			"Accept": "application/json"
		}

		conn = http.client.HTTPSConnection(self.__host)
		conn.request(method, url, params, headers)

		resp = conn.getresponse()

		if resp.reason != "OK":
			raise ValueError("unexpected reason")

		if resp.getcode() != 200:
			raise ValueError("unexpected code")

		data = resp.read()
		parsed_data = json.loads(data)
		return parsed_data

	def get_updates(self, offset=None, limit=None, timeout=None, allowed_updates=None) -> List[Update]:
		params = make_optional(locals(), (self,))
		data = self.__make_request("getUpdates", **params)
		update_list = data.get("result", None)
		return [Update(**d) for d in update_list]

	# MarkdownV2, HTML, Markdown
	def send_message(
			self,
			chat_id: int,
			text: str,
			parse_mode: str = None,
			disable_web_page_preview: bool = None,
			disable_notification: bool = None,
			reply_to_message_id: int = None,
			reply_markup=None
	):
		params = {"chat_id": chat_id, "text": text}
		params.update(make_optional(locals(), (self, chat_id, text)))
		data = self.__make_request("sendMessage", **params)
		return data
