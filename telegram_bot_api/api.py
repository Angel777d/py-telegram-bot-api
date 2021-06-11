import binascii
import http.client
import json
import mimetypes
import os
import stat
from enum import Enum
from io import BytesIO
from typing import List, Optional, Tuple, Any, Union
from urllib.parse import urlencode


def _make_optional(params: dict, *exclude):
	return {k: v for k, v in params.items() if v is not None and v not in exclude}


def _get_public(obj: Any):
	return _make_optional({name: getattr(obj, name) for name in vars(obj) if not name.startswith('_')})


def _fill_object(target, data):
	for k, v in data.items():
		setattr(target, k, __ch_list(target, k, v))


def __ch_list(target, k, v):
	return [__ch_list(target, k, a) for a in v] if isinstance(v, list) else __ch_obj(target, k, v)


def __ch_obj(target, k, v):
	return target.get_class(k)(**v) if isinstance(v, dict) else target.parse_field(k, v)


def __ser(obj):
	if isinstance(obj, str):
		return obj
	if isinstance(obj, list):
		return [__ser(o) for o in obj]
	if hasattr(obj, "serialize"):
		r = obj.serialize()
		return r
	return obj


def _dumps(obj):
	o = __ser(obj)
	if isinstance(o, list):
		return json.dumps(o)
	if isinstance(o, dict):
		return json.dumps(o)
	return obj


class MessageEntityType(Enum):
	"""https://core.telegram.org/bots/api#messageentity"""
	MENTION = "mention"
	HASHTAG = "hashtag"
	CASHTAG = "cashtag"
	BOT_COMMAND = "bot_command"
	URL = "url"
	EMAIL = "email"
	PHONE_NUMBER = "phone_number"
	BOLD = "bold"
	ITALIC = "italic"
	UNDERLINE = "underline"
	STRIKETHROUGH = "strikethrough"
	CODE = "code"
	PRE = "pre"
	TEXT_LINK = "text_link"
	TEXT_MENTION = "text_mention"

	WRONG = "wrong"


class ChatType(Enum):
	"""https://core.telegram.org/bots/api#chat"""
	PRIVATE = "private"
	GROUP = "group"
	SUPERGROUP = "supergroup"
	CHANNEL = "channel"

	WRONG = "wrong"


class PollType(Enum):
	"""https://core.telegram.org/bots/api#sendpoll"""
	REGULAR = "regular"
	QUIZ = "quiz"


# service class
class _Serializable:
	def serialize(self):
		return _get_public(self)


# service class
class _DefaultFieldObject:
	def __init__(self, **kwargs):
		self.__data: dict = kwargs
		_fill_object(self, kwargs)

	def __repr__(self):
		return f'[{self.__class__.__name__}]: {_get_public(self)}'

	@staticmethod
	def parse_field(name, value):
		return value

	def get_class(self, field_name: str):
		return _FIELDS.get(field_name, _DefaultFieldObject)


# part class
class _Caption:
	def __init__(self):
		self.caption: Optional[str] = None
		self.parse_mode: Optional[str] = None
		self.caption_entities: Optional[List[MessageEntity]] = None


# part class
class _Location:
	def __init__(self, latitude: float, longitude: float):
		self.latitude: float = latitude
		self.longitude: float = longitude
		self.horizontal_accuracy: Optional[float] = None
		self.live_period: Optional[int] = None
		self.heading: Optional[int] = None
		self.proximity_alert_radius: Optional[int] = None


# part class
class _Venue:
	def __init__(self, title: str, address: str):
		self.title: str = title
		self.address: str = address

		self.foursquare_id: Optional[str] = None
		self.foursquare_type: Optional[str] = None
		self.google_place_id: Optional[str] = None
		self.google_place_type: Optional[str] = None


# part class
class _Contact:
	def __init__(self, phone_number: str, first_name: str):
		self.phone_number: str = phone_number
		self.first_name: str = first_name

		self.last_name: Optional[str] = None
		self.vcard: Optional[str] = None


# part class
class _FileBase:
	def __init__(self):
		self.file_id: str = ""
		self.file_unique_id: str = ""
		self.file_size: int = 0  # Optional. File size


# part class
class _Bounds:
	def __init__(self):
		self.width: int = 0  # Photo width
		self.height: int = 0  # Photo height


# part class
class _FileDescription:
	def __init__(self):
		self.file_name: str = ""
		self.mime_type: str = ""
		self.thumb: Optional[PhotoSize] = None


class InputFile:
	"""https://core.telegram.org/bots/api#inputfile"""

	def __init__(self, path: str):
		self.value: str = path

	@property
	def file_name(self) -> str:
		return self.value.split('/')[-1]


class InputMedia(_Serializable, _Caption):
	"""https://core.telegram.org/bots/api#inputmedia"""

	def __init__(self, type_: str, media: Union[InputFile, str]):
		_Caption.__init__(self)
		self.type: str = type_
		self.media: Union[InputFile, str] = media

	def serialize(self) -> dict:
		result = _make_optional(_get_public(self), self.media)
		if isinstance(self.media, str):
			result["media"] = self.media
		else:
			result["media"] = f'attach://{self.media.file_name}'
		if self.caption_entities:
			result["caption_entities"] = [c.serialize() for c in self.caption_entities]
		return result


class InputMediaPhoto(InputMedia):
	"""https://core.telegram.org/bots/api#inputmediaphoto"""

	def __init__(self, media: [str, InputFile]):
		InputMedia.__init__(self, "photo", media)


class InputMediaVideo(InputMedia):
	"""https://core.telegram.org/bots/api#inputmediavideo"""

	def __init__(self, media: [str, InputFile]):
		InputMedia.__init__(self, "video", media)
		self.thumb: Optional[Union[InputFile, str]] = None
		self.width: Optional[int] = None
		self.height: Optional[int] = None
		self.duration: Optional[int] = None
		self.supports_streaming: Optional[bool] = None


class InputMediaAnimation(InputMedia):
	"""https://core.telegram.org/bots/api#inputmediaanimation"""

	def __init__(self, media: [str, InputFile]):
		InputMedia.__init__(self, "animation", media)
		self.thumb: Optional[Union[InputFile, str]] = None
		self.width: Optional[int] = None
		self.height: Optional[int] = None
		self.duration: Optional[int] = None


class InputMediaAudio(InputMedia):
	"""https://core.telegram.org/bots/api#inputmediaaudio"""

	def __init__(self, media: [str, InputFile]):
		InputMedia.__init__(self, "audio", media)
		self.thumb: Optional[Union[InputFile, str]] = None
		self.duration: Optional[int] = None
		self.performer: Optional[str] = None
		self.title: Optional[str] = None


class InputMediaDocument(InputMedia):
	"""https://core.telegram.org/bots/api#inputmediadocument"""

	def __init__(self, media: [str, InputFile]):
		InputMedia.__init__(self, "document", media)
		self.thumb: Optional[Union[InputFile, str]] = None
		self.disable_content_type_detection: Optional[bool] = None


class BotCommand(_Serializable):
	"""https://core.telegram.org/bots/api#botcommand"""

	def __init__(self, command: str, description: str):
		self.command: str = command
		self.description: str = description


class MessageId(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#messageid"""

	def __init__(self, **kwargs):
		self.message_id: int = 0
		_DefaultFieldObject.__init__(self, **kwargs)


class UserProfilePhotos(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#userprofilephotos"""

	def __init__(self, **kwargs):
		self.total_count: int = 0
		self.photos: List[List[PhotoSize]]
		_DefaultFieldObject.__init__(self, **kwargs)


class File(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#userprofilephotos"""

	def __init__(self, **kwargs):
		self.file_id: str = ""
		self.file_unique_id: str = ""
		self.file_size: Optional[int] = None
		self.file_path: Optional[str] = None
		_DefaultFieldObject.__init__(self, **kwargs)


class WebhookInfo(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#webhookinfo"""

	def __init__(self, **kwargs):
		self.url: str = ""
		self.has_custom_certificate: bool = False
		self.pending_update_count: int = 0
		self.ip_address: Optional[str] = None
		self.last_error_date: Optional[int] = None
		self.last_error_message: Optional[str] = None
		self.max_connections: Optional[int] = None
		self.allowed_updates: Optional[List[str]] = None
		_DefaultFieldObject.__init__(self, **kwargs)


class InlineQuery(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#inlinequery"""

	def __init__(self, **kwargs):
		self.id: str = ""  # Unique identifier for this query
		self.location: Optional[Location] = None
		self.query: str = ""  # Text of the query (up to 256 characters)
		self.offset: str = ""  # Offset of the results to be returned, can be controlled by the bot
		_DefaultFieldObject.__init__(self, **kwargs)
		# we can't use "from" word in code
		self.from_user: User = getattr(self, "from", None)


class CallbackQuery(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#callbackquery"""

	def __init__(self, **kwargs):
		self.id: str = ""
		self.message: Optional[Message] = None
		self.inline_message_id: Optional[str] = None
		self.chat_instance: Optional[str] = None
		self.data: Optional[str] = None
		self.game_short_name: Optional[str] = None
		_DefaultFieldObject.__init__(self, **kwargs)
		# we can't use "from" word in code
		self.from_user: User = getattr(self, "from", None)


class PollOption(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#polloption"""

	def __init__(self, **kwargs):
		self.text: str = ""
		self.voter_count: int = 0
		_DefaultFieldObject.__init__(self, **kwargs)


class Poll(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#poll"""

	def __init__(self, **kwargs):
		self.id: str = ""
		self.question: str = ""
		self.options: List[PollOption] = []
		self.total_voter_count: int = 0
		self.is_closed: bool = False
		self.is_anonymous: bool = False
		self.type: str = ""
		self.allows_multiple_answers: bool = False

		self.correct_option_id: Optional[int] = None
		self.explanation: Optional[str] = None
		self.explanation_entities: Optional[List[MessageEntity]] = None
		self.open_period: Optional[int] = None
		self.close_date: Optional[int] = None
		_DefaultFieldObject.__init__(self, **kwargs)


class PollAnswer(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#pollanswer"""

	def __init__(self, **kwargs):
		self.poll_id: str = ""
		self.user: User = User()
		self.option_ids: List[int] = []
		_DefaultFieldObject.__init__(self, **kwargs)


class Contact(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#contact"""

	def __init__(self, **kwargs):
		self.phone_number: str = ""
		self.first_name: str = ""
		self.last_name: Optional[str] = None
		self.user_id: Optional[int] = None
		self.vcard: Optional[str] = None
		_DefaultFieldObject.__init__(self, **kwargs)


class Location(_Location, _DefaultFieldObject):
	"""https://core.telegram.org/bots/api#location"""

	def __init__(self, **kwargs):
		_Location.__init__(self, 0, 0)
		_DefaultFieldObject.__init__(self, **kwargs)


class Venue(_Venue, _DefaultFieldObject):
	"""https://core.telegram.org/bots/api#venue"""

	def __init__(self, **kwargs):
		_Venue.__init__(self, "", "")
		self.location: Location = Location()
		_DefaultFieldObject.__init__(self, **kwargs)


class Game(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#game"""

	def __init__(self, **kwargs):
		self.title: str = ""
		self.description: str = ""
		self.photo: List[PhotoSize] = []
		self.text: Optional[str] = None
		self.text_entities: Optional[List[MessageEntity]] = None
		self.animation: Optional[Animation] = None
		_DefaultFieldObject.__init__(self, **kwargs)


class GameHighScore(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#gamehighscore"""

	def __init__(self, **kwargs):
		self.position: int = 0
		self.user: User = User()
		self.score: int = 0
		_DefaultFieldObject.__init__(self, **kwargs)


class Dice(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#dice"""

	def __init__(self, **kwargs):
		self.emoji: str = ""
		self.value: int = 0
		_DefaultFieldObject.__init__(self, **kwargs)


class ChatPermissions(_DefaultFieldObject, _Serializable):
	"""https://core.telegram.org/bots/api#chatpermissions"""

	def __init__(self, **kwargs):
		self.can_send_messages: Optional[bool] = None
		self.can_send_media_messages: Optional[bool] = None
		self.can_send_polls: Optional[bool] = None
		self.can_send_other_messages: Optional[bool] = None
		self.can_add_web_page_previews: Optional[bool] = None
		self.can_change_info: Optional[bool] = None
		self.can_invite_users: Optional[bool] = None
		self.can_pin_messages: Optional[bool] = None
		_DefaultFieldObject.__init__(self, **kwargs)


class ChatPhoto(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#chatphotos"""

	def __init__(self, **kwargs):
		self.small_file_id: str = ""
		self.small_file_unique_id: str = ""
		self.big_file_id: str = ""
		self.big_file_unique_id: str = ""
		_DefaultFieldObject.__init__(self, **kwargs)


class LoginUrl(_Serializable):
	"""https://core.telegram.org/bots/api#loginurl"""

	def __init__(self, url: str):
		self.url: str = url
		self.forward_text: Optional[str] = None
		self.bot_username: Optional[str] = None
		self.request_write_access: Optional[bool] = None


class CallbackGame(_Serializable):
	"""https://core.telegram.org/bots/api#callbackgame"""

	def __init__(
			self,
			user_id: int,
			score: int,
			force: Optional[bool] = None,
			disable_edit_message: Optional[bool] = None,
			chat_id: Optional[int] = None,
			message_id: Optional[int] = None,
			inline_message_id: Optional[str] = None
	):
		assert inline_message_id or (chat_id and message_id), "inline_message_id or chat_id and message_id must be set"
		self.user_id: int = user_id
		self.score: int = score
		self.force: Optional[bool] = force
		self.disable_edit_message: Optional[bool] = disable_edit_message
		self.chat_id: Optional[int] = chat_id
		self.message_id: Optional[int] = message_id
		self.inline_message_id: Optional[str] = inline_message_id


class KeyboardButton(_Serializable):
	"""https://core.telegram.org/bots/api#keyboardbutton"""

	def __init__(
			self,
			text: str,
			request_contact: Optional[bool] = None,
			request_location: Optional[bool] = None,
			request_poll: Optional[str] = None,  # "quiz" or "regular"
	):
		self.text: str = text
		self.request_contact: Optional[bool] = request_contact
		self.request_location: Optional[bool] = request_location
		self.request_poll: Optional[str] = request_poll

	def serialize(self):
		return _make_optional(_get_public(self))


class InlineKeyboardButton(_Serializable):
	"""https://core.telegram.org/bots/api#inlinekeyboardbutton"""

	def __init__(
			self,
			text: str,
			url: Optional[str] = None,
			login_url: Optional[str] = None,
			callback_data: Optional[str] = None,
			switch_inline_query: Optional[str] = None,
			switch_inline_query_current_chat: Optional[str] = None,
			callback_game: Optional[CallbackGame] = None,
			pay: Optional[bool] = None
	):
		self.text: str = text
		self.url: Optional[str] = url
		self.login_url: Optional[LoginUrl] = login_url
		self.callback_data: Optional[str] = callback_data
		self.switch_inline_query: Optional[str] = switch_inline_query
		self.switch_inline_query_current_chat: Optional[str] = switch_inline_query_current_chat
		self.callback_game: Optional[CallbackGame] = callback_game
		self.pay: Optional[bool] = pay

	def serialize(self):
		result = _make_optional(_get_public(self), self.callback_game)
		if self.callback_game:
			result["callback_game"] = self.callback_game.serialize()
		assert len(result) == 2, "[InlineKeyboardButton] You must use exactly one of the optional fields"
		if self.callback_data:
			assert len(self.callback_data) <= 64, "[InlineKeyboardButton] callback_data must be not longer than 64"
		return result


class InlineKeyboardMarkup(_Serializable):
	"""https://core.telegram.org/bots/api#inlinekeyboardmarkup"""

	def __init__(self, inline_keyboard: List[List[InlineKeyboardButton]]):
		self.inline_keyboard: List[List[InlineKeyboardButton]] = inline_keyboard

	def serialize(self):
		return {"inline_keyboard": [[b.serialize() for b in a] for a in self.inline_keyboard]}


class ReplyKeyboardMarkup(_Serializable):
	"""https://core.telegram.org/bots/api#replykeyboardmarkup"""

	def __init__(
			self,
			keyboard: List[List[KeyboardButton]],
			resize_keyboard: Optional[bool] = None,
			one_time_keyboard: Optional[bool] = None,
			selective: Optional[bool] = None,
	):
		self.keyboard: List[List[KeyboardButton]] = keyboard
		self.resize_keyboard: Optional[bool] = resize_keyboard
		self.one_time_keyboard: Optional[bool] = one_time_keyboard
		self.selective: Optional[bool] = selective

	def serialize(self):
		result = _get_public(self)
		if self.keyboard:
			result["keyboard"] = [[b.serialize() for b in a] for a in self.keyboard]
		return result


class ReplyKeyboardRemove(_Serializable):
	"""https://core.telegram.org/bots/api#replykeyboardmarkup"""

	def __init__(self, remove_keyboard: bool = True, selective: Optional[bool] = None):
		self.remove_keyboard: bool = remove_keyboard
		self.selective: Optional[bool] = selective


class ForceReply(_Serializable):
	"""https://core.telegram.org/bots/api#forcereply"""

	def __init__(self, force_reply: bool = True, selective: Optional[bool] = None):
		self.force_reply: bool = force_reply
		self.selective: Optional[bool] = selective


class MaskPosition(_DefaultFieldObject, _Serializable):
	"""https://core.telegram.org/bots/api#maskposition"""

	def __init__(self, **kwargs):
		self.point: str = ""
		self.x_shift: float = 0
		self.y_shift: float = 0
		self.scale: float = 0
		_DefaultFieldObject.__init__(self, **kwargs)


class PhotoSize(_FileBase, _Bounds, _DefaultFieldObject):
	"""https://core.telegram.org/bots/api#photosize"""

	def __init__(self, **kwargs):
		_FileBase.__init__(self)
		_Bounds.__init__(self)
		_DefaultFieldObject.__init__(self, **kwargs)


class Animation(_FileBase, _FileDescription, _Bounds, _DefaultFieldObject):
	"""https://core.telegram.org/bots/api#animation"""

	def __init__(self, **kwargs):
		_FileBase.__init__(self)
		_FileDescription.__init__(self)
		_Bounds.__init__(self)
		self.duration: int = 0
		_DefaultFieldObject.__init__(self, **kwargs)


class Audio(_FileBase, _FileDescription, _DefaultFieldObject):
	"""https://core.telegram.org/bots/api#audio"""

	def __init__(self, **kwargs):
		_FileBase.__init__(self)
		_FileDescription.__init__(self)
		self.duration: int = 0
		self.performer: str = ""
		self.title: str = ""
		_DefaultFieldObject.__init__(self, **kwargs)


class Document(_FileBase, _FileDescription, _DefaultFieldObject):
	"""https://core.telegram.org/bots/api#document"""

	def __init__(self, **kwargs):
		_FileBase.__init__(self)
		_FileDescription.__init__(self)
		_DefaultFieldObject.__init__(self, **kwargs)


class Video(_FileBase, _FileDescription, _Bounds, _DefaultFieldObject):
	"""https://core.telegram.org/bots/api#video"""

	def __init__(self, **kwargs):
		_FileBase.__init__(self)
		_FileDescription.__init__(self)
		_Bounds.__init__(self)
		self.duration: int = 0
		_DefaultFieldObject.__init__(self, **kwargs)


class VideoNote(_FileBase, _DefaultFieldObject):
	"""https://core.telegram.org/bots/api#videonote"""

	def __init__(self, **kwargs):
		_FileBase.__init__(self)
		self.length: int = 0  # Video width and height (diameter of the video message) as defined by sender
		self.duration: int = 0  # Duration of the video in seconds as defined by sender
		self.thumb: Optional[PhotoSize] = None
		_DefaultFieldObject.__init__(self, **kwargs)


class Voice(_FileBase, _DefaultFieldObject):
	"""https://core.telegram.org/bots/api#voice"""

	def __init__(self, **kwargs):
		_FileBase.__init__(self)
		self.duration: int = 0  # Duration of the audio in seconds as defined by sender
		self.mime_type: str = ""
		_DefaultFieldObject.__init__(self, **kwargs)


class Sticker(_FileBase, _Bounds, _DefaultFieldObject):
	"""https://core.telegram.org/bots/api#sticker"""

	def __init__(self, **kwargs):
		_FileBase.__init__(self)
		_Bounds.__init__(self)
		self.is_animated: bool = False  # True,	if the sticker is animated
		self.thumb: Optional[PhotoSize] = None  # Optional.Sticker thumbnail in the.WEBP or.JPG format
		self.emoji: str = ""  # Optional.Emoji	associated	with the sticker
		self.set_name: str = ""  # Optional.Name	of	the	sticker	set	to	which the	sticker	belongs
		self.mask_position: Optional[
			MaskPosition] = None  # Optional. For mask stickers, the position where	the	mask should	be placed
		_DefaultFieldObject.__init__(self, **kwargs)


class StickerSet(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#stickerset"""

	def __init__(self, **kwargs):
		self.name: str = ""
		self.title: str = ""
		self.is_animated: bool = False
		self.contains_masks: bool = False
		self.stickers: List[Sticker] = []
		self.thumb: Optional[PhotoSize] = None
		_DefaultFieldObject.__init__(self, **kwargs)


class User(_DefaultFieldObject, _Serializable):
	"""https://core.telegram.org/bots/api#user"""

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

		_DefaultFieldObject.__init__(self, **kwargs)


class ChatMember(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#chatmember"""

	def __init__(self, **kwargs):
		self.user: User = User()
		self.status: str = ""
		self.custom_title: Optional[str] = None
		self.is_anonymous: Optional[bool] = None
		self.can_be_edited: Optional[bool] = None
		self.can_post_messages: Optional[bool] = None
		self.can_edit_messages: Optional[bool] = None
		self.can_delete_messages: Optional[bool] = None
		self.can_restrict_members: Optional[bool] = None
		self.can_promote_members: Optional[bool] = None
		self.can_change_info: Optional[bool] = None
		self.can_invite_users: Optional[bool] = None
		self.can_pin_messages: Optional[bool] = None
		self.is_member: Optional[bool] = None
		self.can_send_messages: Optional[bool] = None
		self.can_send_media_messages: Optional[bool] = None
		self.can_send_polls: Optional[bool] = None
		self.can_send_other_messages: Optional[bool] = None
		self.can_add_web_page_previews: Optional[bool] = None
		self.until_date: Optional[int] = None

		_DefaultFieldObject.__init__(self, **kwargs)


class Chat(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#chat"""

	def __init__(self, **kwargs):
		self.id: int = 0
		self.type: ChatType = ChatType.WRONG
		self.title: Optional[str] = None
		self.username: Optional[str] = None
		self.first_name: Optional[str] = None
		self.last_name: Optional[str] = None
		self.photo: Optional[ChatPhoto] = None
		self.bio: Optional[str] = None
		self.description: Optional[str] = None
		self.invite_link: Optional[str] = None
		self.pinned_message: Optional[Message] = None
		self.permissions: Optional[ChatPermissions] = None
		self.slow_mode_delay: Optional[int] = None
		self.sticker_set_name: Optional[str] = None
		self.can_set_sticker_set: Optional[bool] = None
		self.linked_chat_id: Optional[int] = None
		self.location: Optional[ChatLocation] = None

		_DefaultFieldObject.__init__(self, **kwargs)

	@staticmethod
	def parse_field(name, value):
		if name == "type":
			return ChatType(value)
		return value

	def get_class(self, field_name: str):
		if field_name == "location":
			return ChatLocation
		return super().get_class(field_name)


class ChatLocation(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#chatlocation"""

	def __init__(self, **kwargs):
		self.location: Location = Location()
		self.address: str = ""
		_DefaultFieldObject.__init__(self, **kwargs)


class MessageEntity(_DefaultFieldObject, _Serializable):
	"""https://core.telegram.org/bots/api#messageentity"""

	def __init__(self, **kwargs):
		self.type: MessageEntityType = MessageEntityType.WRONG
		self.offset: int = 0
		self.length: int = 0

		self.url: Optional[str] = None
		self.user: Optional[User] = None
		self.language: Optional[str] = None

		_DefaultFieldObject.__init__(self, **kwargs)

	@staticmethod
	def parse_field(name, value):
		if name == "type":
			return MessageEntityType(value)
		return value

	def serialize(self):
		return {
			"type": self.type.value,
			"offset": self.offset,
			"length": self.length,
			"url": self.url,
			"user": self.user.serialize() if self.user else None,
			"language": self.language,
		}


class Message(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#message"""

	def __init__(self, **kwargs):
		self.message_id: int = 0
		self.date: int = 0
		self.chat: Chat = Chat()
		self.sender_chat: Optional[Chat] = None
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
		self.entities: Optional[List[MessageEntity]] = []
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
		self.proximity_alert_triggered: Optional[ProximityAlertTriggered] = None
		self.reply_markup: Optional[InlineKeyboardMarkup] = None

		_DefaultFieldObject.__init__(self, **kwargs)
		# we can't use "from" word in code
		self.from_user: Optional[User] = getattr(self, "from", None)


class ProximityAlertTriggered(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#proximityalerttriggered"""

	def __init__(self, **kwargs):
		self.traveler: User = User()
		self.watcher: User = User()
		self.distance: int = 0
		_DefaultFieldObject.__init__(self, **kwargs)


class Update(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#update"""

	def __init__(self, **kwargs):
		self.update_id: int = 0
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

		_DefaultFieldObject.__init__(self, **kwargs)


# Inline classes

class ChosenInlineResult(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#choseninlineresult"""

	def __init__(self, **kwargs):
		self.result_id: str = ""
		self.location: Optional[Location] = None
		self.inline_message_id: Optional[str] = None
		self.query: str = ""
		_DefaultFieldObject.__init__(self, **kwargs)
		# we can't use "from" word in code
		self.from_user: User = getattr(self, "from", None)


class InputMessageContent(_Serializable):
	"""https://core.telegram.org/bots/api#inputmessagecontent"""

	pass


class InputTextMessageContent(InputMessageContent):
	"""https://core.telegram.org/bots/api#inputtextmessagecontent"""

	def __init__(self, message_text):
		self.message_text: str = message_text
		self.parse_mode: Optional[str] = None
		self.entities: Optional[List[MessageEntity]] = None
		self.disable_web_page_preview: Optional[bool] = None

	def serialize(self):
		result = InputMessageContent.serialize(self)
		if self.entities:
			result["entities"] = [e.serialize() for e in self.entities]
		return result


class InputLocationMessageContent(InputMessageContent, _Location):
	"""https://core.telegram.org/bots/api#inputlocationmessagecontent"""

	def __init__(self, latitude: float, longitude: float):
		_Location.__init__(self, latitude, longitude)


class InputVenueMessageContent(InputMessageContent, _Venue):
	"""https://core.telegram.org/bots/api#inputvenuemessagecontent"""

	def __init__(self, latitude: float, longitude: float, title: str, address: str):
		_Venue.__init__(self, title, address)
		self.latitude: float = latitude
		self.longitude: float = longitude


class InputContactMessageContent(InputMessageContent, _Contact):
	"""https://core.telegram.org/bots/api#inputcontactmessagecontent"""

	def __init__(self, phone_number: str, first_name: str):
		_Contact.__init__(self, phone_number, first_name)


class InlineQueryResult(_Serializable):
	"""https://core.telegram.org/bots/api#inlinequeryresult"""

	def __init__(
			self,
			type_: str,
			id_: str,
			reply_markup: Optional[InlineKeyboardMarkup] = None,
			input_message_content: Optional[InputMessageContent] = None
	):
		self.type: str = type_
		self.id: str = id_
		self.reply_markup: Optional[InlineKeyboardMarkup] = reply_markup
		self.input_message_content: Optional[InputMessageContent] = input_message_content

	def serialize(self):
		result = _get_public(self)
		result["reply_markup"] = self.reply_markup.serialize() if self.reply_markup else None
		result["input_message_content"] = self.input_message_content.serialize() if self.input_message_content else None
		if "caption_entities" in result:
			caption_entities = result["caption_entities"]
			result["caption_entities"] = [e.serialize() for e in caption_entities]
		return _make_optional(result)


class InlineQueryResultArticle(InlineQueryResult):
	"""https://core.telegram.org/bots/api#inlinequeryresultarticle"""

	def __init__(self, id_: str, title: str, input_message_content: InputMessageContent):
		InlineQueryResult.__init__(self, "article", id_, input_message_content=input_message_content)
		self.title: str = title
		self.url: Optional[str] = None
		self.hide_url: Optional[bool] = None
		self.description: Optional[str] = None
		self.thumb_url: Optional[str] = None
		self.thumb_width: Optional[int] = None
		self.thumb_height: Optional[int] = None


class InlineQueryResultPhoto(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultphoto"""

	def __init__(self, id_: str, photo_url: str, thumb_url: str):
		InlineQueryResult.__init__(self, "photo", id_)
		_Caption.__init__(self)
		self.photo_url: str = photo_url
		self.thumb_url: str = thumb_url
		self.photo_width: Optional[int] = None
		self.photo_height: Optional[int] = None
		self.title: Optional[str] = None
		self.description: Optional[str] = None


class InlineQueryResultGif(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultgif"""

	def __init__(self, id_: str, gif_url: str):
		InlineQueryResult.__init__(self, "gif", id_)
		_Caption.__init__(self)
		self.gif_url: str = gif_url
		self.gif_width: Optional[int] = None
		self.gif_height: Optional[int] = None
		self.gif_duration: Optional[int] = None
		self.thumb_url: Optional[str] = None
		self.thumb_mime_type: Optional[str] = None
		self.title: Optional[str] = None


class InlineQueryResultMpeg4Gif(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultmpeg4gif"""

	def __init__(self, id_: str, mpeg4_url: str):
		InlineQueryResult.__init__(self, "mpeg4_gif", id_)
		_Caption.__init__(self)
		self.mpeg4_url: str = mpeg4_url
		self.mpeg4_width: Optional[int] = None
		self.mpeg4_height: Optional[int] = None
		self.mpeg4_duration: Optional[int] = None

		self.thumb_url: Optional[str] = None
		self.thumb_mime_type: Optional[str] = None
		self.title: Optional[str] = None


class InlineQueryResultVideo(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultvideo"""

	def __init__(self, id_: str, title: str, video_url: str, mime_type: str, thumb_url: str):
		InlineQueryResult.__init__(self, "video", id_)
		_Caption.__init__(self)
		self.title: str = title
		self.video_url: str = video_url
		self.mime_type: str = mime_type
		self.thumb_url: str = thumb_url

		self.video_width: Optional[int] = None
		self.video_height: Optional[int] = None
		self.video_duration: Optional[int] = None

		self.description: Optional[str] = None


class InlineQueryResultAudio(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultaudio"""

	def __init__(self, id_: str, title: str, audio_url: str):
		InlineQueryResult.__init__(self, "audio", id_)
		_Caption.__init__(self)
		self.title: str = title
		self.audio_url: str = audio_url
		self.performer: Optional[str] = None
		self.audio_duration: Optional[int] = None


class InlineQueryResultVoice(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultvoice"""

	def __init__(self, id_: str, title: str, voice_url: str):
		InlineQueryResult.__init__(self, "voice", id_)
		_Caption.__init__(self)
		self.title: str = title
		self.voice_url: str = voice_url
		self.voice_duration: Optional[int] = None


class InlineQueryResultDocument(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultdocument"""

	def __init__(self, id_: str, title: str, document_url: str, mime_type: str):
		InlineQueryResult.__init__(self, "document", id_)
		_Caption.__init__(self)
		self.title: str = title
		self.document_url: str = document_url
		self.mime_type: str = mime_type
		self.description: Optional[str] = None

		self.thumb_url: Optional[str] = None
		self.thumb_width: Optional[int] = None
		self.thumb_height: Optional[int] = None


class InlineQueryResultLocation(InlineQueryResult, _Location):
	"""https://core.telegram.org/bots/api#inlinequeryresultlocation"""

	def __init__(self, id_: str, latitude: float, longitude: float, title: str):
		InlineQueryResult.__init__(self, "location", id_)
		_Location.__init__(self, latitude, longitude)
		self.title: str = title

		self.thumb_url: Optional[str] = None
		self.thumb_width: Optional[int] = None
		self.thumb_height: Optional[int] = None


class InlineQueryResultVenue(InlineQueryResult, _Venue):
	"""https://core.telegram.org/bots/api#inlinequeryresultvenue"""

	def __init__(self, id_: str, latitude: float, longitude: float, title: str, address: str):
		InlineQueryResult.__init__(self, "venue", id_)
		self.latitude: float = latitude
		self.longitude: float = longitude

		_Venue.__init__(self, title, address)

		self.thumb_url: Optional[str] = None
		self.thumb_width: Optional[int] = None
		self.thumb_height: Optional[int] = None


class InlineQueryResultContact(InlineQueryResult, _Contact):
	"""https://core.telegram.org/bots/api#inlinequeryresultcontact"""

	def __init__(self, id_: str, phone_number: str, first_name: str):
		InlineQueryResult.__init__(self, "contact", id_)
		_Contact.__init__(self, phone_number, first_name)

		self.thumb_url: Optional[str] = None
		self.thumb_width: Optional[int] = None
		self.thumb_height: Optional[int] = None


class InlineQueryResultGame(InlineQueryResult):
	"""https://core.telegram.org/bots/api#inlinequeryresultgame"""

	def __init__(self, id_: str, game_short_name: str):
		InlineQueryResult.__init__(self, "game", id_)
		self.game_short_name: str = game_short_name


class InlineQueryResultCachedPhoto(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultcachedphoto"""

	def __init__(self, id_: str, photo_file_id: str):
		InlineQueryResult.__init__(self, "photo", id_)
		_Caption.__init__(self)
		self.photo_file_id: str = photo_file_id

		self.title: Optional[str] = None
		self.description: Optional[str] = None


class InlineQueryResultCachedGif(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultcachedgif"""

	def __init__(self, id_: str, gif_file_id: str):
		InlineQueryResult.__init__(self, "gif", id_)
		_Caption.__init__(self)
		self.gif_file_id: str = gif_file_id

		self.title: Optional[str] = None


class InlineQueryResultCachedMpeg4Gif(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultcachedmpeg4gif"""

	def __init__(self, id_: str, mpeg4_file_id: str):
		InlineQueryResult.__init__(self, "mpeg4_gif", id_)
		_Caption.__init__(self)
		self.mpeg4_file_id: str = mpeg4_file_id
		self.title: Optional[str] = None


class InlineQueryResultCachedSticker(InlineQueryResult):
	"""https://core.telegram.org/bots/api#inlinequeryresultcachedsticker"""

	def __init__(self, id_: str, sticker_file_id: str):
		InlineQueryResult.__init__(self, "sticker", id_)
		self.sticker_file_id: str = sticker_file_id


class InlineQueryResultCachedDocument(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultcacheddocument"""

	def __init__(self, id_: str, title: str, document_file_id: str):
		InlineQueryResult.__init__(self, "document", id_)
		_Caption.__init__(self)
		self.title: str = title
		self.document_file_id: str = document_file_id

		self.description: Optional[str] = None


class InlineQueryResultCachedVideo(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultcachedvideo"""

	def __init__(self, id_: str, title: str, video_file_id: str):
		InlineQueryResult.__init__(self, "video", id_)
		_Caption.__init__(self)
		self.title: str = title
		self.video_file_id: str = video_file_id

		self.description: Optional[str] = None


class InlineQueryResultCachedVoice(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultcachedvoice"""

	def __init__(self, id_: str, title: str, voice_file_id: str):
		InlineQueryResult.__init__(self, "voice", id_)
		_Caption.__init__(self)
		self.title: str = title
		self.voice_file_id: str = voice_file_id

		self.description: Optional[str] = None


class InlineQueryResultCachedAudio(InlineQueryResult, _Caption):
	"""https://core.telegram.org/bots/api#inlinequeryresultcachedaudio"""

	def __init__(self, id_: str, audio_file_id: str):
		InlineQueryResult.__init__(self, "audio", id_)
		_Caption.__init__(self)
		self.audio_file_id: str = audio_file_id


class LabeledPrice(_DefaultFieldObject, _Serializable):
	"""https://core.telegram.org/bots/api#labeledprice"""

	def __init__(self, label: str, amount: int, **kwargs):
		self.label: str = label
		self.amount: int = amount
		_DefaultFieldObject.__init__(self, **kwargs)


class Invoice(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#invoice"""

	def __init__(self, **kwargs):
		self.title: str = ""
		self.description: str = ""
		self.start_parameter: str = ""
		self.currency: str = ""
		self.total_amount: int = 0
		_DefaultFieldObject.__init__(self, **kwargs)


class ShippingAddress(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#shippingaddress"""

	def __init__(self, **kwargs):
		self.country_code: str = ""
		self.state: str = ""
		self.city: str = ""
		self.street_line1: str = ""
		self.street_line2: str = ""
		self.post_code: str = ""
		_DefaultFieldObject.__init__(self, **kwargs)


class OrderInfo(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#orderinfo"""

	def __init__(self, **kwargs):
		self.name: Optional[str] = None
		self.phone_number: Optional[str] = None
		self.email: Optional[str] = None
		self.shipping_address: Optional[ShippingAddress] = None

		_DefaultFieldObject.__init__(self, **kwargs)


class ShippingOption(_Serializable):
	"""https://core.telegram.org/bots/api#shippingoption"""

	def __init__(self, id_: str, title: str, prices: List[LabeledPrice]):
		self.id: str = id_
		self.title: str = title
		self.prices: List[LabeledPrice] = prices

	def serialize(self):
		result = _Serializable.serialize(self)
		result["prices"] = [p.serialize() for p in self.prices]
		return result


class SuccessfulPayment(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#successfulpayment"""

	def __init__(self, **kwargs):
		self.currency: str = ""
		self.total_amount: int = 0
		self.invoice_payload: str = ""
		self.shipping_option_id: Optional[str] = None
		self.order_info: Optional[OrderInfo] = None
		self.telegram_payment_charge_id: str = ""
		self.provider_payment_charge_id: str = ""
		_DefaultFieldObject.__init__(self, **kwargs)


class ShippingQuery(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#shippingquery"""

	def __init__(self, **kwargs):
		self.id: str = ""
		self.invoice_payload: str = ''
		self.shipping_address: ShippingAddress = ShippingAddress()
		_DefaultFieldObject.__init__(self, **kwargs)
		# we can't use "from" word in code
		self.from_user: User = getattr(self, "from", None)


class PreCheckoutQuery(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#precheckoutquery"""

	def __init__(self, **kwargs):
		self.id: str = ""
		self.currency: str = ""
		self.total_amount: int = 0
		self.invoice_payload: str = ""
		self.shipping_option_id: Optional[str] = None
		self.order_info: Optional[OrderInfo] = None
		_DefaultFieldObject.__init__(self, **kwargs)
		# we can't use "from" word in code
		self.from_user: User = getattr(self, "from", None)


# https://core.telegram.org/bots/api#telegram-passport

class EncryptedPassportElement(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#encryptedpassportelement"""

	def __init__(self, **kwargs):
		self.type: str = ""  # type is reserved word
		self.data: str = ""
		self.phone_number: Optional[str] = None
		self.email: Optional[str] = None
		self.files: Optional[List[PassportFile]] = None
		self.front_side: Optional[PassportFile] = None
		self.reverse_side: Optional[PassportFile] = None
		self.selfie: Optional[PassportFile] = None
		self.translation: Optional[List[PassportFile]] = None
		self.hash: str = ""  # hash is reserved word
		_DefaultFieldObject.__init__(self, **kwargs)


class EncryptedCredentials(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#encryptedcredentials"""

	def __init__(self, **kwargs):
		self.data: str = ""
		self.hash: str = ""
		self.secret: str = ""
		_DefaultFieldObject.__init__(self, **kwargs)


class PassportData(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#passportdata"""

	def __init__(self, **kwargs):
		self.data: List[EncryptedPassportElement] = []
		self.credentials: EncryptedCredentials = EncryptedCredentials()
		_DefaultFieldObject.__init__(self, **kwargs)


class PassportFile(_DefaultFieldObject):
	"""https://core.telegram.org/bots/api#passportfile"""

	def __init__(self, **kwargs):
		self.file_id: str = ""
		self.file_unique_id: str = ""
		self.file_size: int = 0
		self.file_date: int = 0
		_DefaultFieldObject.__init__(self, **kwargs)


class PassportElementError(_Serializable):
	"""https://core.telegram.org/bots/api#passportelementerror"""

	def __init__(self, source: str, type_: str, message: str, types_check: Optional[Tuple] = None):
		if types_check:
			assert type_ in types_check, f'Wrong type "{type_}" not expected.'

		self.source: str = source
		self.type: str = type_
		self.message: str = message

	def _check(self, *types):
		return self.type in types


class PassportElementErrorDataField(PassportElementError):
	"""https://core.telegram.org/bots/api#passportelementerrordatafield"""

	def __init__(self, type_: str, field_name: str, data_hash: str, message: str):
		types = ('personal_details', 'passport', 'driver_license', 'identity_card', 'internal_passport', 'address')
		PassportElementError.__init__(self, "data", type_, message, types)
		self.field_name: str = field_name
		self.data_hash: str = data_hash


class PassportElementErrorFrontSide(PassportElementError):
	"""https://core.telegram.org/bots/api#passportelementerrorfrontside"""

	def __init__(self, type_: str, file_hash: str, message: str):
		types = ('passport', 'driver_license', 'identity_card', 'internal_passport')
		PassportElementError.__init__(self, "front_side", type_, message, types)
		self.file_hash: str = file_hash


class PassportElementErrorReverseSide(PassportElementError):
	"""https://core.telegram.org/bots/api#passportelementerrorreverseside"""

	def __init__(self, type_: str, file_hash: str, message: str):
		types = ('driver_license', 'identity_card')
		PassportElementError.__init__(self, "reverse_side", type_, message, types)
		self.file_hash: str = file_hash


class PassportElementErrorSelfie(PassportElementError):
	"""https://core.telegram.org/bots/api#passportelementerrorselfie"""

	def __init__(self, type_: str, file_hash: str, message: str):
		types = ('passport', 'driver_license', 'identity_card', 'internal_passport')
		assert type_ in types, f'Wrong type "{type_}" not expected.'

		PassportElementError.__init__(self, "selfie", type_, message)
		self.file_hash: str = file_hash


class PassportElementErrorFile(PassportElementError):
	"""https://core.telegram.org/bots/api#passportelementerrorfile"""

	def __init__(self, type_: str, file_hash: str, message: str):
		types = (
			'utility_bill', 'bank_statement', 'rental_agreement', 'passport_registration', 'temporary_registration')
		assert type_ in types, f'Wrong type "{type_}" not expected.'

		PassportElementError.__init__(self, "file", type_, message, types)
		self.file_hash: str = file_hash


class PassportElementErrorFiles(PassportElementError):
	"""https://core.telegram.org/bots/api#passportelementerrorfiles"""

	def __init__(self, type_: str, file_hashes: List[str], message: str):
		types = (
			'utility_bill', 'bank_statement', 'rental_agreement', 'passport_registration', 'temporary_registration')
		PassportElementError.__init__(self, "files", type_, message, types)
		self.file_hashes: List[str] = file_hashes


class PassportElementErrorTranslationFile(PassportElementError):
	"""https://core.telegram.org/bots/api#passportelementerrortranslationfile"""

	def __init__(self, type_: str, file_hash: str, message: str):
		types = (
			'passport', 'driver_license', 'identity_card', 'internal_passport', 'utility_bill', 'bank_statement',
			'rental_agreement', 'passport_registration', 'temporary_registration')
		PassportElementError.__init__(self, "translation_file", type_, message, types)
		self.file_hash: str = file_hash


class PassportElementErrorTranslationFiles(PassportElementError):
	"""https://core.telegram.org/bots/api#passportelementerrortranslationfiles"""

	def __init__(self, type_: str, file_hashes: List[str], message: str):
		types = (
			'passport', 'driver_license', 'identity_card', 'internal_passport', 'utility_bill', 'bank_statement',
			'rental_agreement', 'passport_registration', 'temporary_registration')

		PassportElementError.__init__(self, "translation_files", type_, message, types)
		self.file_hashes: List[str] = file_hashes


class PassportElementErrorUnspecified(PassportElementError):
	"""https://core.telegram.org/bots/api#passportelementerrorunspecified"""

	def __init__(self, type_: str, element_hash: str, message: str):
		PassportElementError.__init__(self, "unspecified", type_, message)
		self.element_hash: str = element_hash


_FIELDS = {
	"message": Message,
	"edited_message": Message,
	"entities": MessageEntity,
	"caption_entities": MessageEntity,
	"reply_to_message": Message,
	"chat": Chat,
	"sender_chat": Chat,
	"forward_from": User,
	"forward_from_chat": Chat,
	"from": User,
	"user": User,
	"via_bot": User,
	"mask_position": MaskPosition,
	"thumb": PhotoSize,
	"anim": Video,
	"animation": Animation,
	"audio": Audio,
	"document": Document,
	"photo": PhotoSize,
	"sticker": Sticker,
	"video": Video,
	"video_note": VideoNote,
	"voice": Voice,
	"channel_post": Message,
	"edited_channel_post": Message,
	"inline_query": InlineQuery,
	"chosen_inline_result": ChosenInlineResult,
	"callback_query": CallbackQuery,
	"photos": PhotoSize,
	"option": PollOption,
	"stickers": Sticker,
	"shipping_address": ShippingAddress,
	"prices": LabeledPrice,
	"order_info": LabeledPrice,
	"data": EncryptedPassportElement,
	"credentials": EncryptedCredentials,
	"files": PassportFile,
	"front_side": PassportFile,
	"reverse_side": PassportFile,
	"selfie": PassportFile,
	"translation": PassportFile,
	"location": Location,
	"venue": Venue,
}

Keyboards = Union[InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply]


# https://core.telegram.org/bots/api
class API:
	class _MultiPartForm:
		def __init__(self):
			self.boundary = binascii.hexlify(os.urandom(16)).decode('ascii')
			self.buff = BytesIO()

		def write_params(self, params):
			for key, value in params.items():
				self.write_one_param(key, value)

		def write_one_param(self, key, value):
			value = _dumps(value)
			self._write_str(f'--{self.boundary}\r\n')
			self._write_str(f'Content-Disposition: form-data; name="{key}"\r\n')
			self._write_str('Content-Type: text/plain; charset=utf-8\r\n')
			self._write_str('\r\n')
			if value is None:
				value = ""
			self._write_str(f'{value}\r\n')

		def write_one_input(self, input_file: Union[InputFile, str], field: str):
			if isinstance(input_file, str):
				self.write_params({field: input_file})
			else:
				self.write_file(input_file, field)

		def write_file(self, input_file: InputFile, field: str = None):
			boundary = self.boundary

			path = input_file.value
			file_name = input_file.file_name
			field = field or file_name
			with open(path, mode="rb") as file:
				file_size = os.fstat(file.fileno())[stat.ST_SIZE]
				content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'

				self._write_str(f'--{boundary}\r\n')
				self._write_str(f'Content-Disposition: form-data; name="{field}"; filename="{file_name}"\r\n')
				self._write_str(f'Content-Type: {content_type}; charset=utf-8\r\n')
				self._write_str(f'Content-Length: {file_size}\r\n')

				file.seek(0)
				self.buff.write(b'\r\n')
				self.buff.write(file.read())
				self.buff.write(b'\r\n')

		def _write_str(self, value: str):
			self.buff.write(value.encode('utf-8'))

		def get_data(self):
			self._write_str(f'--{self.boundary}--\r\n')
			return self.boundary, self.buff.getvalue()

		def make_request(self, host, url):
			boundary, buffer = self.get_data()
			buffer_size = len(buffer)

			conn = http.client.HTTPSConnection(host)
			conn.connect()
			conn.putrequest("POST", url)
			conn.putheader('Connection', 'Keep-Alive')
			conn.putheader('Cache-Control', 'no-cache')
			conn.putheader('Accept', 'application/json')
			conn.putheader('Content-type', f'multipart/form-data; boundary={boundary}')
			conn.putheader('Content-length', str(buffer_size))
			conn.endheaders()

			conn.send(buffer)

			return conn.getresponse()

	def __init__(self, token: str, host: str = "api.telegram.org"):
		"""https://core.telegram.org/bots/api"""

		self.__host: str = host
		self.__token: str = token

	# https://core.telegram.org/bots/api#getupdates
	def get_updates(self, offset=None, limit=None, timeout=None, allowed_updates=None) -> List[Update]:
		return [Update(**d) for d in self.__simple("getUpdates", locals())]

	# https://core.telegram.org/bots/api#setwebhook
	def set_webhook(
			self,
			url: str,
			certificate: Optional[InputFile] = None,
			ip_address: Optional[str] = None,
			max_connections: Optional[int] = None,
			allowed_updates: Optional[List[str]] = None,
			drop_pending_updates: Optional[bool] = None
	) -> bool:
		params = _make_optional(locals(), self, certificate)
		form = self._MultiPartForm()
		form.write_params(params)
		if certificate:
			form.write_file(certificate, "certificate")

		data = self.__make_multipart_request(form, "setWebhook")
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#deletewebhook
	def delete_webhook(self, drop_pending_updates: Optional[bool] = None) -> bool:
		return bool(self.__simple("deleteWebhook", locals()))

	# https://core.telegram.org/bots/api#getwebhookinfo
	def get_webhook_info(self) -> WebhookInfo:
		data = self.__make_request("getWebhookInfo", params={})
		return WebhookInfo(**data.get("result"))

	# https://core.telegram.org/bots/api#getme
	def get_me(self) -> User:
		return User(**self.__simple("getMe", {}))

	# https://core.telegram.org/bots/api#logout
	def log_out(self) -> bool:
		return bool(self.__simple("logOut", {}))

	# https://core.telegram.org/bots/api#close
	def close(self) -> bool:
		return bool(self.__simple("close", {}))

	# https://core.telegram.org/bots/api#sendmessage
	def send_message(
			self,
			chat_id: Union[int, str],
			text: str,
			parse_mode: Optional[str] = None,
			entities: Optional[List[MessageEntity]] = None,
			disable_web_page_preview: Optional[bool] = None,
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None
	) -> Message:
		# assert not (parse_mode and entities)
		return Message(**self.__simple("sendMessage", locals()))

	# https://core.telegram.org/bots/api#forwardmessage
	def forward_message(
			self,
			chat_id: Union[int, str],
			from_chat_id: Union[int, str],
			message_id: int,
			disable_notification: Optional[bool] = None
	) -> Message:
		return Message(**self.__simple("forwardMessage", locals()))

	# https://core.telegram.org/bots/api#copymessage
	def copy_message(
			self,
			chat_id: Union[int, str],
			from_chat_id: Union[int, str],
			message_id: int,
			caption: Optional[str] = None,
			parse_mode: Optional[str] = None,
			caption_entities: Optional[List[MessageEntity]] = None,
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None
	) -> MessageId:
		return MessageId(**self.__simple("copyMessage", locals()))

	# https://core.telegram.org/bots/api#sendphoto
	def send_photo(
			self,
			chat_id: Union[int, str],
			photo: Union[InputFile, str],
			caption: Optional[str] = None,
			parse_mode: Optional[str] = None,
			caption_entities: Optional[List[MessageEntity]] = None,
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None

	):
		params = _make_optional(locals(), self, photo)
		form = self._MultiPartForm()
		form.write_params(params)
		form.write_one_input(photo, "photo")

		data = self.__make_multipart_request(form, "sendPhoto")
		return Message(**data.get("result", None))

	# https://core.telegram.org/bots/api#sendaudio
	def send_audio(
			self,
			chat_id: Union[int, str],
			audio: Union[InputFile, str],
			caption: Optional[str] = None,
			parse_mode: Optional[str] = None,
			caption_entities: Optional[List[MessageEntity]] = None,
			duration: Optional[int] = None,
			performer: Optional[str] = None,
			title: Optional[str] = None,
			thumb: Optional[Union[InputFile, str]] = None
	):
		params = _make_optional(locals(), self, audio, thumb)
		form = self._MultiPartForm()
		form.write_params(params)
		form.write_one_input(audio, "audio")
		if thumb:
			form.write_one_input(thumb, "thumb")

		data = self.__make_multipart_request(form, "sendAudio")
		return Message(**data.get("result", None))

	# https://core.telegram.org/bots/api#senddocument
	def send_document(
			self,
			chat_id: Union[int, str],
			document: Union[InputFile, str],
			thumb: Optional[Union[InputFile, str]] = None,
			caption: Optional[str] = None,
			parse_mode: Optional[str] = None,
			caption_entities: Optional[List[MessageEntity]] = None,

			disable_content_type_detection: Optional[bool] = None,
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None
	):
		params = _make_optional(locals(), self, document, thumb)

		form = self._MultiPartForm()
		form.write_params(params)
		form.write_one_input(document, "document")
		if thumb:
			form.write_one_input(thumb, "thumb")

		data = self.__make_multipart_request(form, "sendDocument")
		return Message(**data.get("result", None))

	# https://core.telegram.org/bots/api#sendvideo
	def send_video(
			self,
			chat_id: Union[int, str],
			video: Union[InputFile, str],
			thumb: Optional[Union[InputFile, str]] = None,
			duration: Optional[int] = None,
			width: Optional[int] = None,
			height: Optional[int] = None,

			caption: Optional[str] = None,
			parse_mode: Optional[str] = None,
			caption_entities: Optional[List[MessageEntity]] = None,

			supports_streaming: Optional[bool] = None,
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None
	):
		params = _make_optional(locals(), self, video, thumb)
		form = self._MultiPartForm()
		form.write_params(params)
		form.write_one_input(video, "video")
		if thumb:
			form.write_one_input(thumb, "thumb")

		data = self.__make_multipart_request(form, "sendVideo")
		return Message(**data.get("result", None))

	# https://core.telegram.org/bots/api#sendanimation
	def send_animation(
			self,
			chat_id: Union[int, str],
			animation: Union[InputFile, str],
			thumb: Optional[Union[InputFile, str]] = None,
			duration: Optional[int] = None,
			width: Optional[int] = None,
			height: Optional[int] = None,

			caption: Optional[str] = None,
			parse_mode: Optional[str] = None,
			caption_entities: Optional[List[MessageEntity]] = None,

			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None
	):
		params = _make_optional(locals(), self, animation, thumb)
		form = self._MultiPartForm()
		form.write_params(params)
		form.write_one_input(animation, "animation")
		if thumb:
			form.write_one_input(thumb, "thumb")

		data = self.__make_multipart_request(form, "sendAnimation")
		return Message(**data.get("result", None))

	# https://core.telegram.org/bots/api#sendvoice
	def send_voice(
			self,
			chat_id: Union[int, str],
			voice: Union[InputFile, str],

			caption: Optional[str] = None,
			parse_mode: Optional[str] = None,
			caption_entities: Optional[List[MessageEntity]] = None,

			duration: Optional[int] = None,

			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None
	):
		params = _make_optional(locals(), self, voice)
		form = self._MultiPartForm()
		form.write_params(params)
		form.write_one_input(voice, "voice")

		data = self.__make_multipart_request(form, "sendVoice")
		return Message(**data.get("result", None))

	# https://core.telegram.org/bots/api#sendvideonote
	def send_video_note(
			self,
			chat_id: Union[int, str],
			video_note: Union[InputFile, str],

			duration: Optional[int] = None,
			length: Optional[int] = None,

			thumb: Optional[Union[InputFile, str]] = None,

			caption: Optional[str] = None,
			parse_mode: Optional[str] = None,
			caption_entities: Optional[List[MessageEntity]] = None,

			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None
	):
		params = _make_optional(locals(), self, video_note, thumb)
		form = self._MultiPartForm()
		form.write_params(params)
		form.write_one_input(video_note, "video_note")
		if thumb:
			form.write_one_input(thumb, "thumb")

		data = self.__make_multipart_request(form, "sendVideoNote")
		return Message(**data.get("result", None))

	# https://core.telegram.org/bots/api#sendmediagroup
	def send_media_group(
			self,
			chat_id: Union[int, str],
			media: List[InputMedia],
			disable_notification: bool = None,
			reply_to_message_id: int = None,
			allow_sending_without_reply: bool = None
	) -> List[Message]:
		params = _make_optional(locals(), self)
		form = self._MultiPartForm()
		for m in media:
			if isinstance(m.media, str):
				continue
			form.write_file(m.media)
		form.write_params(params)

		data = self.__make_multipart_request(form, "sendMediaGroup")
		return [Message(**d) for d in data.get("result", None)]

	# https://core.telegram.org/bots/api#sendlocation
	def send_location(
			self,
			chat_id: Union[int, str],
			latitude: float,
			longitude: float,
			horizontal_accuracy: Optional[float] = None,
			live_period: Optional[int] = None,
			heading: Optional[int] = None,
			proximity_alert_radius: Optional[int] = None,
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None
	) -> Message:
		return Message(**self.__simple("sendLocation", locals()))

	# https://core.telegram.org/bots/api#editmessagelivelocation
	def edit_message_live_location(
			self,
			latitude: float,
			longitude: float,
			chat_id: Optional[Union[int, str]] = None,
			message_id: Optional[int] = None,
			inline_message_id: Optional[str] = None,
			horizontal_accuracy: Optional[float] = None,
			heading: Optional[int] = None,
			proximity_alert_radius: Optional[int] = None,
			reply_markup: Optional[Keyboards] = None
	) -> Union[Message, bool]:
		assert (chat_id and message_id) or inline_message_id, "chat_id and message_id or inline_message_id must be set"
		data = self.__simple("editMessageLiveLocation", locals())
		return bool(data) if inline_message_id else Message(**data)

	# https://core.telegram.org/bots/api#stopmessagelivelocation
	def stop_message_live_location(
			self,
			chat_id: Optional[Union[int, str]] = None,
			message_id: Optional[int] = None,
			inline_message_id: Optional[str] = None,
			reply_markup: Optional[Keyboards] = None
	) -> Union[Message, bool]:
		assert (chat_id and message_id) or inline_message_id, "chat_id and message_id or inline_message_id must be set"
		data = self.__simple("stopMessageLiveLocation", locals())
		return bool(data) if inline_message_id else Message(**data)

	# https://core.telegram.org/bots/api#sendvenue
	def send_venue(
			self,
			chat_id: Union[int, str],
			latitude: float,
			longitude: float,
			title: str,
			address: str,
			foursquare_id: Optional[str] = None,
			foursquare_type: Optional[str] = None,
			google_place_id: Optional[str] = None,
			google_place_type: Optional[str] = None,
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None

	) -> Message:
		return Message(**self.__simple("sendVenue", locals()))

	# https://core.telegram.org/bots/api#sendcontact
	def send_contact(
			self,
			chat_id: Union[int, str],
			phone_number: str,
			first_name: str,
			last_name: Optional[str] = None,
			vcard: Optional[str] = None,
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None

	) -> Message:
		return Message(**self.__simple("sendContact", locals()))

	# https://core.telegram.org/bots/api#sendpoll
	def send_poll(
			self,
			chat_id: Union[int, str],
			question: str,
			options: List[str],
			is_anonymous: Optional[bool] = None,
			type_: Optional[PollType] = PollType.REGULAR,
			allows_multiple_answers: Optional[bool] = None,
			correct_option_id: Optional[int] = None,
			explanation: Optional[str] = None,
			explanation_parse_mode: Optional[str] = None,
			explanation_entities: Optional[List[MessageEntity]] = None,
			open_period: Optional[int] = None,
			close_date: Optional[int] = None,
			is_closed: Optional[bool] = None,

			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None

	) -> Message:
		params = _make_optional(locals(), self, type_)
		params["type"] = type_.value
		assert type_ != PollType.QUIZ or correct_option_id, "correct_option_id must be set for PollType.QUIZ"
		data = self.__make_request("sendPoll", params=params)
		return Message(**data.get("result"))

	# https://core.telegram.org/bots/api#senddice
	def send_dice(
			self,
			chat_id: Union[int, str],
			emoji: Optional[str] = None,
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None

	) -> Message:
		return Message(**self.__simple("sendDice", locals()))

	# https://core.telegram.org/bots/api#sendchataction
	def send_chat_action(
			self,
			chat_id: Union[int, str],
			action: Optional[str] = None,
	) -> bool:
		return bool(self.__simple("sendChatAction", locals()))

	# https://core.telegram.org/bots/api#getuserprofilephotos
	def get_user_profile_photos(
			self,
			user_id: int,
			offset: Optional[int] = None,
			limit: Optional[int] = None,
	) -> UserProfilePhotos:
		return UserProfilePhotos(**self.__simple("getUserProfilePhotos", locals()))

	# https://core.telegram.org/bots/api#getfile
	def get_file(self, file_id: str) -> File:
		return File(**self.__simple("getFile", {"file_id": file_id}))

	# https://core.telegram.org/bots/api#kickchatmember
	def kick_chat_member(self, chat_id: Union[int, str], user_id: int, until_date: Optional[int] = None) -> bool:
		return bool(self.__simple("kickChatMember", locals()))

	# https://core.telegram.org/bots/api#unbanchatmember
	def unban_chat_member(self, chat_id: Union[int, str], user_id: int, only_if_banned: Optional[bool] = None) -> bool:
		return bool(self.__simple("unbanChatMember", locals()))

	# https://core.telegram.org/bots/api#restrictchatmember
	def restrict_chat_member(
			self,
			chat_id: Union[int, str],
			user_id: int,
			permissions: ChatPermissions,
			until_date: Optional[int] = None
	) -> bool:
		return bool(self.__simple("restrictChatMember", locals()))

	# https://core.telegram.org/bots/api#promotechatmember
	def promote_chat_member(
			self,
			chat_id: Union[int, str],
			user_id: int,
			is_anonymous: Optional[bool] = None,
			can_change_info: Optional[bool] = None,
			can_post_messages: Optional[bool] = None,
			can_edit_messages: Optional[bool] = None,
			can_delete_messages: Optional[bool] = None,
			can_invite_users: Optional[bool] = None,
			can_restrict_members: Optional[bool] = None,
			can_pin_messages: Optional[bool] = None,
			can_promote_members: Optional[bool] = None
	) -> bool:
		return bool(self.__simple("promoteChatMember", locals()))

	# https://core.telegram.org/bots/api#setchatadministratorcustomtitle
	def set_chat_administrator_custom_title(
			self,
			chat_id: Union[int, str],
			user_id: int,
			custom_title: str,
	) -> bool:
		return bool(self.__simple("setChatAdministratorCustomTitle", locals()))

	# https://core.telegram.org/bots/api#setchatpermissions
	def set_chat_permissions(
			self,
			chat_id: Union[int, str],
			permissions: ChatPermissions,
	) -> bool:
		return bool(self.__simple("setChatPermissions", {"chat_id": chat_id, "permissions": permissions}))

	# https://core.telegram.org/bots/api#exportchatinvitelink
	def export_chat_invite_link(self, chat_id: Union[int, str]) -> str:
		return str(self.__simple("exportChatInviteLink", {"chat_id": chat_id}))

	# https://core.telegram.org/bots/api#setchatphoto
	def set_chat_photo(
			self,
			chat_id: Union[int, str],
			photo: InputFile,
	) -> bool:
		form = self._MultiPartForm()
		form.write_params({"chat_id": chat_id})
		form.write_one_input(photo, "photo")

		data = self.__make_multipart_request(form, "setChatPhoto")
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#deletechatphoto
	def delete_chat_photo(self, chat_id: Union[int, str]) -> bool:
		return bool(self.__simple("deleteChatPhoto", {"chat_id": chat_id}))

	# https://core.telegram.org/bots/api#setchattitle
	def set_chat_title(self, chat_id: Union[int, str], title: str) -> bool:
		return bool(self.__simple("setChatTitle", {"chat_id": chat_id, "title": title}))

	# https://core.telegram.org/bots/api#setchatdescription
	def set_chat_description(self, chat_id: Union[int, str], description: str) -> bool:
		return bool(self.__simple("setChatDescription", {"chat_id": chat_id, "description": description}))

	# https://core.telegram.org/bots/api#pinchatmessage
	def pin_chat_message(
			self,
			chat_id: Union[int, str],
			message_id: int,
			disable_notification: Optional[bool] = None
	) -> bool:
		return bool(self.__simple("pinChatMessage", locals()))

	# https://core.telegram.org/bots/api#unpinchatmessage
	def unpin_chat_message(self, chat_id: Union[int, str], message_id: Optional[int]) -> bool:
		return bool(self.__simple("unpinChatMessage", locals()))

	# https://core.telegram.org/bots/api#unpinallchatmessages
	def unpin_all_chat_messages(self, chat_id: Union[int, str]) -> bool:
		return bool(self.__simple("unpinAllChatMessages", {"chat_id": chat_id}))

	# https://core.telegram.org/bots/api#leavechat
	def leave_chat(self, chat_id: Union[int, str]) -> bool:
		return bool(self.__simple("leaveChat", {"chat_id": chat_id}))

	# https://core.telegram.org/bots/api#getchat
	def get_chat(self, chat_id: Union[int, str]) -> Chat:
		return Chat(**self.__simple("getChat", {"chat_id": chat_id}))

	# https://core.telegram.org/bots/api#getchatadministrators
	def get_chat_administrators(self, chat_id: Union[int, str]) -> List[ChatMember]:
		return [ChatMember(**d) for d in self.__simple("getChatAdministrators", {"chat_id": chat_id})]

	# https://core.telegram.org/bots/api#getchatmemberscount
	def get_chat_members_count(self, chat_id: Union[int, str]) -> int:
		return int(self.__simple("getChatMembersCount", {"chat_id": chat_id}))

	# https://core.telegram.org/bots/api#getchatmemberscount
	def get_chat_member(self, chat_id: Union[int, str], user_id: int) -> ChatMember:
		return ChatMember(**self.__simple("getChatMember", {"chat_id": chat_id, "user_id": user_id}))

	# https://core.telegram.org/bots/api#setchatstickerset
	def set_chat_sticker_set(self, chat_id: Union[int, str], sticker_set_name: str) -> bool:
		return bool(self.__simple("setChatStickerSet", {"chat_id": chat_id, "sticker_set_name": sticker_set_name}))

	# https://core.telegram.org/bots/api#deletechatstickerset
	def delete_chat_sticker_set(self, chat_id: Union[int, str]) -> bool:
		data = self.__make_request("deleteChatStickerSet", {"chat_id": chat_id})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#answercallbackquery
	def answer_callback_query(
			self,
			callback_query_id: str,
			text: Optional[str] = None,
			show_alert: Optional[bool] = None,
			url: Optional[str] = None,
			cache_time: Optional[int] = None
	) -> bool:
		return bool(self.__simple("answerCallbackQuery", locals()))

	# https://core.telegram.org/bots/api#setmycommands
	def set_my_commands(self, commands: List[BotCommand]) -> bool:
		data = self.__make_request("setMyCommands", {"commands": commands})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#getmycommands
	def get_my_commands(self) -> List[BotCommand]:
		data = self.__make_request("getMyCommands", {})
		return [BotCommand(**c) for c in data.get("result")]

	# https://core.telegram.org/bots/api#editmessagetext
	def edit_message_text(
			self,
			chat_id: Optional[Union[int, str]] = None,
			message_id: Optional[int] = None,
			inline_message_id: Optional[str] = None,
			text: Optional[str] = None,
			parse_mode: Optional[str] = None,
			entities: Optional[List[MessageEntity]] = None,
			disable_web_page_preview: Optional[bool] = None,
			reply_markup: Optional[InlineKeyboardMarkup] = None,
	) -> Message:
		assert (chat_id and message_id) or inline_message_id, "chat_id and message_id or inline_message_id must be set"
		return Message(**self.__simple("editMessageText", locals()))

	# https://core.telegram.org/bots/api#editmessagecaption
	def edit_message_caption(
			self,
			chat_id: Optional[Union[int, str]] = None,
			message_id: Optional[int] = None,
			inline_message_id: Optional[str] = None,
			caption: Optional[str] = None,
			parse_mode: Optional[str] = None,
			caption_entities: Optional[List[MessageEntity]] = None,
			reply_markup: Optional[InlineKeyboardMarkup] = None,
	) -> Message:
		assert (chat_id and message_id) or inline_message_id, "chat_id and message_id or inline_message_id must be set"
		return Message(**self.__simple("editMessageCaption", locals()))

	# https://core.telegram.org/bots/api#editmessagecaption
	def edit_message_media(
			self,
			media: InputMedia,
			chat_id: Optional[Union[int, str]] = None,
			message_id: Optional[int] = None,
			inline_message_id: Optional[str] = None,
			reply_markup: Optional[InlineKeyboardMarkup] = None,
	) -> Message:
		assert isinstance(media.media, str), "can't upload file while edit message"
		assert (chat_id and message_id) or inline_message_id, "chat_id and message_id or inline_message_id must be set"
		return Message(**self.__simple("editMessageMedia", locals()))

	# https://core.telegram.org/bots/api#editmessagereplymarkup
	def edit_message_reply_markup(
			self,
			chat_id: Optional[Union[int, str]] = None,
			message_id: Optional[int] = None,
			inline_message_id: Optional[str] = None,
			reply_markup: Optional[InlineKeyboardMarkup] = None,
	) -> Union[bool, Message]:
		assert (chat_id and message_id) or inline_message_id, "chat_id and message_id or inline_message_id must be set"
		data = self.__simple("editMessageReplyMarkup", locals())
		return bool(data) if inline_message_id else Message(**data)

	# https://core.telegram.org/bots/api#stoppoll
	def stop_poll(
			self,
			chat_id: Union[int, str],
			message_id: int,
			reply_markup: Optional[InlineKeyboardMarkup] = None,
	) -> Poll:
		return Poll(**self.__simple("stopPoll", locals()))

	# https://core.telegram.org/bots/api#deletemessage
	def delete_message(self, chat_id: Union[int, str], message_id: int) -> bool:
		return bool(self.__simple("deleteMessage", {"chat_id": chat_id, "message_id": message_id}))

	# https://core.telegram.org/bots/api#sendsticker
	def send_sticker(
			self,
			chat_id: Union[int, str],
			sticker: Union[InputFile, str],
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[Keyboards] = None

	) -> Message:
		params = _make_optional(locals(), self, sticker)
		form = self._MultiPartForm()
		form.write_params(params)
		form.write_one_input(sticker, "sticker")

		data = self.__make_multipart_request(form, "sendSticker")
		return Message(**data.get("result"))

	# https://core.telegram.org/bots/api#getstickerset
	def get_sticker_set(self, name: str) -> StickerSet:
		return StickerSet(**self.__simple("getStickerSet", {"name": name}))

	# https://core.telegram.org/bots/api#uploadstickerfile
	def upload_sticker_file(
			self,
			user_id: int,
			png_sticker: InputFile
	) -> File:
		form = self._MultiPartForm()
		form.write_params({"user_id": user_id})
		form.write_one_input(png_sticker, "png_sticker")

		data = self.__make_multipart_request(form, "uploadStickerFile")
		return File(**data.get("result"))

	def __stickers(self, method, params, png_sticker, tgs_sticker):
		assert bool(png_sticker) ^ bool(tgs_sticker), "png_sticker or tgs_sticker must be set"
		form = self._MultiPartForm()
		form.write_params(params)
		if png_sticker:
			form.write_one_input(png_sticker, "png_sticker")
		if tgs_sticker:
			form.write_one_input(tgs_sticker, "tgs_sticker")

		data = self.__make_multipart_request(form, method)
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#createnewstickerset
	def create_new_sticker_set(
			self,
			user_id: int,
			name: str,
			title: str,
			emojis: str,
			png_sticker: Optional[Union[InputFile, str]] = None,
			tgs_sticker: Optional[InputFile] = None,
			contains_masks: Optional[bool] = None,
			mask_position: Optional[MaskPosition] = None
	) -> bool:
		params = _make_optional(locals(), self, png_sticker, tgs_sticker)
		return self.__stickers("createNewStickerSet", params, png_sticker, tgs_sticker)

	# https://core.telegram.org/bots/api#addstickertoset
	def add_sticker_to_set(
			self,
			user_id: int,
			name: str,
			emojis: str,
			png_sticker: Optional[Union[InputFile, str]] = None,
			tgs_sticker: Optional[InputFile] = None,
			mask_position: Optional[MaskPosition] = None
	) -> bool:
		params = _make_optional(locals(), self, png_sticker, tgs_sticker)
		return self.__stickers("addStickerToSet", params, png_sticker, tgs_sticker)

	# https://core.telegram.org/bots/api#setstickerpositioninset
	def set_sticker_position_in_set(self, sticker: str, position: int) -> bool:
		return bool(self.__simple("setStickerPositionInSet", {"sticker": sticker, "position": position}))

	# https://core.telegram.org/bots/api#deletestickerfromset
	def delete_sticker_from_set(self, sticker: str) -> bool:
		return bool(self.__simple("deleteStickerFromSet", {"sticker": sticker}))

	# https://core.telegram.org/bots/api#setstickersetthumb
	def set_sticker_set_thumb(
			self,
			name: str,
			user_id: int,
			thumb: Optional[Union[InputFile, str]]
	) -> File:
		form = self._MultiPartForm()
		form.write_params({"name": name, "user_id": user_id})
		if thumb:
			form.write_one_input(thumb, "thumb")

		data = self.__make_multipart_request(form, "setStickerSetThumb")
		return File(**data.get("result"))

	# https://core.telegram.org/bots/api#answerinlinequery
	def answer_inline_query(
			self,
			inline_query_id: str,
			results: List[InlineQueryResult],
			cache_time: Optional[int] = None,
			is_personal: Optional[bool] = None,
			next_offset: Optional[str] = None,
			switch_pm_text: Optional[str] = None,
			switch_pm_parameter: Optional[str] = None,
	) -> bool:
		return bool(self.__simple("answerInlineQuery", locals()))

	# https://core.telegram.org/bots/api#sendinvoice
	def send_invoice(
			self,
			chat_id: int,
			title: str,
			description: str,
			payload: str,
			provider_token: str,
			start_parameter: str,
			currency: str,  # Three-letter ISO 4217 currency code, see more on currencies
			prices: List[LabeledPrice],
			provider_data: Optional[str] = None,
			photo_url: Optional[str] = None,
			photo_size: Optional[int] = None,
			photo_width: Optional[int] = None,
			photo_height: Optional[int] = None,
			need_name: Optional[bool] = None,
			need_phone_number: Optional[bool] = None,
			need_email: Optional[bool] = None,
			need_shipping_address: Optional[bool] = None,
			send_phone_number_to_provider: Optional[bool] = None,
			send_email_to_provider: Optional[bool] = None,
			is_flexible: Optional[bool] = None,
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[InlineKeyboardMarkup] = None,
	) -> Message:
		return Message(**self.__simple("sendInvoice", locals()))

	# https://core.telegram.org/bots/api#answershippingquery
	def answer_shipping_query(
			self,
			shipping_query_id: str,
			ok: bool,
			shipping_options: Optional[List[ShippingOption]] = None,
			error_message: Optional[str] = None,
	) -> bool:
		assert ok or error_message, "error_message Required if ok is False"
		return bool(self.__simple("answerShippingQuery", locals()))

	# https://core.telegram.org/bots/api#answerprecheckoutquery
	def answer_pre_checkout_query(
			self,
			pre_checkout_query_id: str,
			ok: bool,
			error_message: Optional[str] = None,
	) -> bool:
		assert ok or error_message, "error_message Required if ok is False"
		return bool(self.__simple("answerPreCheckoutQuery", locals()))

	def set_passport_data_errors(self, user_id: int, errors: List[PassportElementError]) -> bool:
		return bool(self.__simple("setPassportDataErrors", locals()))

	def send_game(
			self,
			chat_id: int,
			game_short_name: str,
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[InlineKeyboardMarkup] = None,
	) -> Message:
		return Message(**self.__simple("sendGame", locals()))

	def get_game_high_scores(
			self,
			user_id: int,
			chat_id: Optional[int] = None,
			message_id: Optional[int] = None,
			inline_message_id: Optional[str] = None,
	) -> List[GameHighScore]:
		return [GameHighScore(**d) for d in self.__simple("getGameHighScores", locals())]

	def __get_url(self, api_method) -> str:
		return f'https://{self.__host}/bot{self.__token}/{api_method}'

	def __make_multipart_request(self, form, api_method):
		url = self.__get_url(api_method)
		resp = form.make_request(self.__host, url)
		return self.__process_response(resp)

	def __simple(self, method: str, params: dict) -> Union[bool, str, int, dict, list]:
		params = _make_optional(params, self)
		data = self.__make_request(method, params)
		return data.get("result")

	def __make_request(self, api_method: str, params: Optional[dict] = None, method="POST"):

		url = self.__get_url(api_method)
		params = {k: _dumps(v) for k, v in params.items()}
		params = urlencode(params)

		headers = {
			"Content-type": "application/x-www-form-urlencoded",
			"Accept": "application/json"
		}

		conn = http.client.HTTPSConnection(self.__host)
		conn.request(method, url, params, headers)

		return self.__process_response(conn.getresponse())

	@staticmethod
	def __process_response(resp):
		if resp.reason != "OK":
			data = resp.read()
			raise ValueError("unexpected reason", data)

		if resp.getcode() != 200:
			data = resp.read()
			raise ValueError("unexpected code", data)

		data = resp.read()
		parsed_data = json.loads(data)
		return parsed_data
