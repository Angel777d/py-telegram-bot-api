import binascii
import http.client
import json
import mimetypes
import os
import stat
from enum import Enum
from io import BytesIO
from typing import List, Optional, Tuple, KeysView, Any, Union
from urllib.parse import urlencode


# https://core.telegram.org/bots/api#messageentity
class MessageEntityType(Enum):
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

	WRONG = "wrong"


# https://core.telegram.org/bots/api#chat
class ChatType(Enum):
	PRIVATE = "private"
	GROUP = "group"
	SUPERGROUP = "supergroup"
	CHANNEL = "channel"

	WRONG = "wrong"


def _get_public(obj: Any):
	return {name: getattr(obj, name) for name in vars(obj) if not name.startswith('_')}


def _make_optional(params: dict, exclude=()):
	return {k: v for k, v in params.items() if v is not None and v not in exclude}


def _fill_object(target, data):
	for k, v in data.items():
		setattr(target, k, __ch_list(target, k, v))


def __ch_list(target, k, v):
	return [__ch_list(target, k, a) for a in v] if type(v) is list else __ch_obj(target, k, v)


def __ch_obj(target, k, v):
	return target.get_fields_map().get(k, _DefaultFieldObject)(**v) if type(v) is dict else target.get_simple_field(k,
																													v)


# service class
class _Serializable:
	def serialize(self):
		raise NotImplementedError("serialize method must be implemented")


# https://core.telegram.org/bots/api#inputfile
class InputFile(_Serializable):
	class InputType(Enum):
		FILE = 0
		URL = 1
		TELEGRAM = 2

	def __init__(self, type_: InputType, value: Union[int, str]) -> None:
		super().__init__()
		self.type = type_
		self.value = value
		self.file_name = value
		if type_ == InputFile.InputType.FILE:
			self.file_name = value.split('/')[-1]

	def serialize(self):
		raise NotImplementedError("serialize method must be implemented")


# service class
class MultiPartForm:
	def __init__(self):
		self.boundary = binascii.hexlify(os.urandom(16)).decode('ascii')
		self.buff = BytesIO()

	def write_params(self, params):
		boundary = self.boundary
		for key, value in params.items():
			self._write_str(f'--{boundary}\r\n')
			self._write_str(f'Content-Disposition: form-data; name="{key}"\r\n')
			self._write_str('Content-Type: text/plain; charset=utf-8\r\n')
			self._write_str('\r\n')
			if value is None:
				value = ""
			self._write_str(f'{value}\r\n')

	def write_one_input(self, input_file: Union[InputFile, str], field: str):
		if type(input_file) is str:
			self.write_params({field: input_file})
		elif input_file.type != InputFile.InputType.FILE:
			self.write_params({field: input_file.value})
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
			print("[Req]", "\r\n...file data...\r\n", end="")

	def _write_str(self, value: str):
		print("[Req]", value, end="")
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


# https://core.telegram.org/bots/api#inputmedia
class InputMedia(_Serializable, _Caption):
	def __init__(self, type_: str, media: Union[str, InputFile]):
		super().__init__()
		self.type: str = type_
		self.media: Union[str, InputFile] = media

	def serialize(self):
		if type(self.media) == str:
			media = self.media
		elif self.media.type == InputFile.InputType.FILE:
			media = f'attach://{self.media.file_name}'
		else:
			media = self.media.value

		return _make_optional({
			"type": self.type,
			"media": media,
			"caption": self.caption,
			"parse_mode": self.parse_mode,
			"caption_entities": [m.serialize() for m in self.caption_entities] if self.caption_entities else None,
		})


# service class
class _InputThumb(InputMedia):
	def __init__(self, type_: str, media: str):
		super().__init__(type_, media)
		self.thumb: Optional[InputFile] = None

	def serialize(self):
		result = super().serialize()
		result.update(_make_optional({
			"thumb": self.thumb.serialize() if self.thumb else None
		}))
		return result


# https://core.telegram.org/bots/api#inputmediaphoto
class InputMediaPhoto(InputMedia):

	def __init__(self, media: [str, InputFile]):
		super().__init__("photo", media)


# https://core.telegram.org/bots/api#inputmediavideo
class InputMediaVideo(_InputThumb):
	def __init__(self, media: [str, InputFile]):
		super().__init__("video", media)
		self.width: Optional[int] = None
		self.height: Optional[int] = None
		self.duration: Optional[int] = None
		self.supports_streaming: Optional[bool] = None

	def serialize(self):
		result = super().serialize()
		result.update(_make_optional({
			"width": self.width,
			"height": self.height,
			"duration": self.duration,
			"supports_streaming": self.supports_streaming,
		}))
		return result


# https://core.telegram.org/bots/api#inputmediaanimation
class InputMediaAnimation(_InputThumb):
	def __init__(self, media: [str, InputFile]):
		super().__init__("animation", media)
		self.width: Optional[int] = None
		self.height: Optional[int] = None
		self.duration: Optional[int] = None

	def serialize(self):
		result = super().serialize()
		result.update(_make_optional({
			"width": self.width,
			"height": self.height,
			"duration": self.duration,
		}))
		return result


# https://core.telegram.org/bots/api#inputmediaaudio
class InputMediaAudio(_InputThumb):
	def __init__(self, media: [str, InputFile]):
		super().__init__("audio", media)
		self.duration: Optional[int] = None
		self.performer: Optional[str] = None
		self.title: Optional[str] = None

	def serialize(self):
		result = super().serialize()
		result.update(_make_optional({
			"duration": self.duration,
			"performer": self.performer,
			"title": self.title,
		}))
		return result


# https://core.telegram.org/bots/api#inputmediadocument
class InputMediaDocument(_InputThumb):
	def __init__(self, media: [str, InputFile]):
		super().__init__("document", media)
		self.disable_content_type_detection: Optional[bool] = None

	def serialize(self):
		result = super().serialize()
		result.update(_make_optional({
			"disable_content_type_detection": self.disable_content_type_detection,
		}))
		return result


# service class
class _DefaultFieldObject:
	def __init__(self, **kwargs):
		self.__data: dict = kwargs
		_fill_object(self, kwargs)

	def __repr__(self):
		return f'[{self.__class__.__name__}] data: {self.__dict__}'

	def get_fields(self) -> KeysView[str]:
		return self.__data.keys()

	def get_source(self) -> dict:
		return self.__data

	@staticmethod
	def get_simple_field(name, value):
		return value

	@staticmethod
	def get_fields_map():
		return {
			"message": Message,
			"entities": MessageEntity,
			"caption_entities": MessageEntity,
			"reply_to_message": Message,
			"chat": Chat,
			"from": User,
			"user": User,
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
			"inline_query": InlineQuery,
			"photos": PhotoSize,
			"option": PollOption,
			"stickers": Sticker,
		}.copy()


# https://core.telegram.org/bots/api#botcommand
class BotCommand(_Serializable):
	def __init__(self, command: str, description: str):
		self.command: str = command
		self.description: str = description

	def serialize(self):
		return _get_public(self)


# https://core.telegram.org/bots/api#messageid
class MessageId(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.message_id: int = 0
		super().__init__(**kwargs)


# https://core.telegram.org/bots/api#userprofilephotos
class UserProfilePhotos(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.total_count: int = 0
		self.photos: List[List[PhotoSize]]
		super().__init__(**kwargs)


# https://core.telegram.org/bots/api#userprofilephotos
class File(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.file_id: str = ""
		self.file_unique_id: str = ""
		self.file_size: Optional[int] = None
		self.file_path: Optional[str] = None
		super().__init__(**kwargs)


# https://core.telegram.org/bots/api#webhookinfo
class WebhookInfo(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.url: str = ""
		self.has_custom_certificate: bool = False
		self.pending_update_count: int = 0
		self.ip_address: Optional[str] = None
		self.last_error_date: Optional[int] = None
		self.last_error_message: Optional[str] = None
		self.max_connections: Optional[int] = None
		self.allowed_updates: Optional[List[str]] = None
		super().__init__(**kwargs)


# https://core.telegram.org/bots/api#inlinequery
class InlineQuery(_DefaultFieldObject):

	def __init__(self, **kwargs):
		self.id: str = ""  # Unique identifier for this query
		self.from_user: User = User()
		self.location: Optional[Location] = None
		self.query: str = ""  # Text of the query (up to 256 characters)
		self.offset: str = ""  # Offset of the results to be returned, can be controlled by the bot
		super().__init__(**kwargs)


# https://core.telegram.org/bots/api#callbackquery
class CallbackQuery(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.id: str = ""
		self.from_user: User = User()
		self.message: Optional[Message] = None
		self.inline_message_id: Optional[str] = None
		self.chat_instance: Optional[str] = None
		self.data: Optional[str] = None
		self.game_short_name: Optional[str] = None
		super().__init__(**kwargs)


# https://core.telegram.org/bots/api#polloption
class PollOption(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.text: str = ""
		self.voter_count: int = 0
		super().__init__(**kwargs)


# https://core.telegram.org/bots/api#poll
class Poll(_DefaultFieldObject):
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
		super().__init__(**kwargs)


# https://core.telegram.org/bots/api#pollanswer
class PollAnswer(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.poll_id: str = ""
		self.user: User = User()
		self.option_ids: List[int] = []
		super().__init__(**kwargs)


# https://core.telegram.org/bots/api#contact
class Contact(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.phone_number: str = ""
		self.first_name: str = ""
		self.last_name: Optional[str] = None
		self.user_id: Optional[int] = None
		self.vcard: Optional[str] = None
		super().__init__(**kwargs)


class ShippingQuery(_DefaultFieldObject):
	pass


class PreCheckoutQuery(_DefaultFieldObject):
	pass


class PassportData(_DefaultFieldObject):
	pass


class SuccessfulPayment(_DefaultFieldObject):
	pass


class Invoice(_DefaultFieldObject):
	pass


# https://core.telegram.org/bots/api#location
class Location(_Location, _DefaultFieldObject):
	def __init__(self, **kwargs):
		_Location.__init__(self, 0, 0)
		_DefaultFieldObject.__init__(self, **kwargs)


class Venue(_Venue, _DefaultFieldObject):
	def __init__(self, **kwargs):
		_Venue.__init__(self, "", "")
		self.location: Location = Location()
		_DefaultFieldObject.__init__(self, **kwargs)


# https://core.telegram.org/bots/api#game
class Game(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.title: str = ""
		self.description: str = ""
		self.photo: List[PhotoSize] = []
		self.text: Optional[str] = None
		self.text_entities: Optional[List[MessageEntity]] = None
		self.animation: Optional[Animation] = None
		super().__init__(**kwargs)


# https://core.telegram.org/bots/api#dice
class Dice(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.emoji: str = ""
		self.value: int = 0
		super().__init__(**kwargs)


class ChatPermissions(_DefaultFieldObject, _Serializable):
	def __init__(self, **kwargs):
		self.can_send_messages: Optional[bool] = None
		self.can_send_media_messages: Optional[bool] = None
		self.can_send_polls: Optional[bool] = None
		self.can_send_other_messages: Optional[bool] = None
		self.can_add_web_page_previews: Optional[bool] = None
		self.can_change_info: Optional[bool] = None
		self.can_invite_users: Optional[bool] = None
		self.can_pin_messages: Optional[bool] = None
		super().__init__(**kwargs)

	def serialize(self):
		return _make_optional(_get_public(self))


# https://core.telegram.org/bots/api#chatphotos
class ChatPhoto(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.small_file_id: str = ""
		self.small_file_unique_id: str = ""
		self.big_file_id: str = ""
		self.big_file_unique_id: str = ""
		super().__init__(**kwargs)


# https://core.telegram.org/bots/api#loginurl
class LoginUrl(_Serializable):
	def __init__(self, url: str):
		self.url: str = url
		self.forward_text: Optional[str] = None
		self.bot_username: Optional[str] = None
		self.request_write_access: Optional[bool] = None

	def serialize(self):
		return _make_optional(_get_public(self))


# https://core.telegram.org/bots/api#callbackgame
class CallbackGame(_Serializable):
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

	def serialize(self):
		return _make_optional(_get_public(self))


# https://core.telegram.org/bots/api#inlinekeyboardbutton
class InlineKeyboardButton(_Serializable):
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
		result = _make_optional(_get_public(self), (self.callback_game,))
		if self.callback_game:
			result["callback_game"] = self.callback_game.serialize()
		assert len(result) == 2, "[InlineKeyboardButton] You must use exactly one of the optional fields"
		return result


# service class
class _KeyboardMarkup(_Serializable):
	def serialize(self):
		raise NotImplementedError("serialize method must be implemented")


# https://core.telegram.org/bots/api#inlinekeyboardmarkup
class InlineKeyboardMarkup(_KeyboardMarkup):
	def __init__(self, inline_keyboard: List[List[InlineKeyboardButton]]):
		self.inline_keyboard: List[List[InlineKeyboardButton]] = inline_keyboard

	def serialize(self):
		return {
			"inline_keyboard": [[b.serialize() for b in a] for a in self.inline_keyboard]
		}


# https://core.telegram.org/bots/api#replykeyboardmarkup
class ReplyKeyboardMarkup(_KeyboardMarkup):
	def __init__(
			self,
			keyboard: List[List[InlineKeyboardButton]],
			resize_keyboard: Optional[bool] = None,
			one_time_keyboard: Optional[bool] = None,
			selective: Optional[bool] = None,
	):
		self.keyboard: List[List[InlineKeyboardButton]] = keyboard
		self.resize_keyboard: Optional[bool] = resize_keyboard
		self.one_time_keyboard: Optional[bool] = one_time_keyboard
		self.selective: Optional[bool] = selective

	def serialize(self):
		result = _make_optional(_get_public(self))
		if self.keyboard:
			result["keyboard"] = [[b.serialize() for b in a] for a in self.keyboard]
		return result


# https://core.telegram.org/bots/api#replykeyboardmarkup
class ReplyKeyboardRemove(_KeyboardMarkup):
	def __init__(self, remove_keyboard: bool = True, selective: Optional[bool] = None):
		self.remove_keyboard: bool = remove_keyboard
		self.selective: Optional[bool] = selective

	def serialize(self):
		return _make_optional(_get_public(self))


# https://core.telegram.org/bots/api#forcereply
class ForceReply(_KeyboardMarkup):
	def __init__(self, force_reply: bool = True, selective: Optional[bool] = None):
		self.force_reply: bool = force_reply
		self.selective: Optional[bool] = selective

	def serialize(self):
		return _make_optional(_get_public(self))


class MaskPosition(_DefaultFieldObject, _Serializable):
	def __init__(self, **kwargs):
		self.point: str = ""
		self.x_shift: float = 0
		self.y_shift: float = 0
		self.scale: float = 0
		_DefaultFieldObject.__init__(self, **kwargs)

	def serialize(self):
		return _make_optional(_get_public(self))


class FileBase:
	def __init__(self):
		self.file_id: str = ""  # Identifier for this file, which can be used to download or reuse the file
		# Unique identifier for this file, which is supposed to be the same over time and for different bots.
		# Can't be used to download or reuse the file.
		self.file_unique_id: str = ""
		self.file_size: int = 0  # Optional. File size


class Bounds:
	def __init__(self):
		self.width: int = 0  # Photo width
		self.height: int = 0  # Photo height


class PhotoSize(FileBase, Bounds, _DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		Bounds.__init__(self)
		_DefaultFieldObject.__init__(self, **kwargs)


class FileDescription:
	def __init__(self):
		self.file_name: str = ""
		self.mime_type: str = ""
		self.thumb: Optional[PhotoSize] = None


class Animation(FileBase, FileDescription, Bounds, _DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		FileDescription.__init__(self)
		Bounds.__init__(self)
		self.duration: int = 0
		_DefaultFieldObject.__init__(self, **kwargs)


class Audio(FileBase, FileDescription, _DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		FileDescription.__init__(self)
		self.duration: int = 0
		self.performer: str = ""
		self.title: str = ""
		_DefaultFieldObject.__init__(self, **kwargs)


class Document(FileBase, FileDescription, _DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		FileDescription.__init__(self)
		_DefaultFieldObject.__init__(self, **kwargs)


class Video(FileBase, FileDescription, Bounds, _DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		FileDescription.__init__(self)
		Bounds.__init__(self)
		self.duration: int = 0
		_DefaultFieldObject.__init__(self, **kwargs)


class VideoNote(FileBase, _DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		self.length: int = 0  # Video width and height (diameter of the video message) as defined by sender
		self.duration: int = 0  # Duration of the video in seconds as defined by sender
		self.thumb: Optional[PhotoSize] = None
		_DefaultFieldObject.__init__(self, **kwargs)


class Voice(FileBase, _DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		self.duration: int = 0  # Duration of the audio in seconds as defined by sender
		self.mime_type: str = ""
		_DefaultFieldObject.__init__(self, **kwargs)


class Sticker(FileBase, Bounds, _DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		Bounds.__init__(self)
		self.is_animated: bool = False  # True,	if the sticker is animated
		self.thumb: Optional[PhotoSize] = None  # Optional.Sticker thumbnail in the.WEBP or.JPG format
		self.emoji: str = ""  # Optional.Emoji	associated	with the sticker
		self.set_name: str = ""  # Optional.Name	of	the	sticker	set	to	which the	sticker	belongs
		self.mask_position: Optional[
			MaskPosition] = None  # Optional. For mask stickers, the position where	the	mask should	be placed
		_DefaultFieldObject.__init__(self, **kwargs)


class StickerSet(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.name: str = ""
		self.title: str = ""
		self.is_animated: bool = False
		self.contains_masks: bool = False
		self.stickers: List[Sticker] = []
		self.thumb: Optional[PhotoSize] = None
		super().__init__(**kwargs)


class User(_DefaultFieldObject, _Serializable):
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

	def serialize(self):
		return _make_optional({
			"id": self.id,
			"is_bot": self.is_bot,
			"first_name": self.first_name,
			"last_name": self.last_name,
			"username": self.username,
			"language_code": self.language_code,
			"can_join_groups": self.can_join_groups,
			"can_read_all_group_messages": self.can_read_all_group_messages,
			"supports_inline_queries": self.supports_inline_queries,
		})


class ChatMember(_DefaultFieldObject):
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
	def __init__(self, **kwargs):
		self.id: int = 0
		self.type: ChatType = ChatType.WRONG
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

		_DefaultFieldObject.__init__(self, **kwargs)

	@staticmethod
	def get_simple_field(name, value):
		if name == "type":
			return ChatType(value)
		return value


class MessageEntity(_DefaultFieldObject, _Serializable):
	def __init__(self, **kwargs):
		self.type: MessageEntityType = MessageEntityType.WRONG
		self.offset: int = 0
		self.length: int = 0

		self.url: Optional[str] = None
		self.user: Optional[User] = None
		self.language: Optional[str] = None

		_DefaultFieldObject.__init__(self, **kwargs)

	def get_value(self, text: str) -> str:
		return text[self.offset:self.offset + self.length]

	@staticmethod
	def get_simple_field(name, value):
		if name == "type":
			return MessageEntityType(value)
		return value

	def serialize(self):
		return _make_optional({
			"type": self.type.value,
			"offset": self.offset,
			"length": self.length,
			"url": self.url,
			"user": self.user.serialize() if self.user else None,
			"language": self.language,
		})


class Message(_DefaultFieldObject):
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
		self.reply_markup: Optional[InlineKeyboardMarkup] = None

		_DefaultFieldObject.__init__(self, **kwargs)
		# we can't use "from" word in code
		self.from_user: Optional[User] = getattr(self, "from")

	def get_entities_by_type(self, entity_type: MessageEntityType) -> Tuple[str]:
		return tuple(e.get_value(self.text) for e in self.entities if e.type == entity_type)


class Update(_DefaultFieldObject):
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

		_DefaultFieldObject.__init__(self, **kwargs)

	def __repr__(self):
		return f'[Update] update_id: {self.update_id}, type: {self.update_types}, value: {self.__data.values()}'


# Inline classes

# https://core.telegram.org/bots/api#choseninlineresult
class ChosenInlineResult(_DefaultFieldObject):
	def __init__(self, **kwargs):
		self.result_id: str = ""
		self.from_user: User = User()
		self.location: Optional[Location] = None
		self.inline_message_id: Optional[str] = None
		self.query: str = ""
		super().__init__(**kwargs)


# https://core.telegram.org/bots/api#inputmessagecontent
class InputMessageContent(_Serializable):
	def serialize(self):
		return _make_optional(_get_public(self))


# https://core.telegram.org/bots/api#inputtextmessagecontent
class InputTextMessageContent(InputMessageContent):
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


# https://core.telegram.org/bots/api#inputlocationmessagecontent
class InputLocationMessageContent(InputMessageContent, _Location):
	def __init__(self, latitude: float, longitude: float):
		_Location.__init__(self, latitude, longitude)


# https://core.telegram.org/bots/api#inputvenuemessagecontent
class InputVenueMessageContent(InputMessageContent, _Venue):
	def __init__(self, latitude: float, longitude: float, title: str, address: str):
		_Venue.__init__(self, title, address)
		self.latitude: float = latitude
		self.longitude: float = longitude


# https://core.telegram.org/bots/api#inputcontactmessagecontent
class InputContactMessageContent(InputMessageContent, _Contact):
	def __init__(self, phone_number: str, first_name: str):
		_Contact.__init__(self, phone_number, first_name)


# https://core.telegram.org/bots/api#inlinequeryresult
class InlineQueryResult(_Serializable):
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


# https://core.telegram.org/bots/api#inlinequeryresultarticle
class InlineQueryResultArticle(InlineQueryResult):
	def __init__(self, id_: str, title: str, input_message_content: InputMessageContent):
		InlineQueryResult.__init__(self, "article", id_, input_message_content=input_message_content)
		self.title: str = title
		self.url: Optional[str] = None
		self.hide_url: Optional[bool] = None
		self.description: Optional[str] = None
		self.thumb_url: Optional[str] = None
		self.thumb_width: Optional[int] = None
		self.thumb_height: Optional[int] = None


# https://core.telegram.org/bots/api#inlinequeryresultphoto
class InlineQueryResultPhoto(InlineQueryResult, _Caption):
	def __init__(self, id_: str, photo_url: str, thumb_url: str):
		InlineQueryResult.__init__(self, "photo", id_)
		_Caption.__init__(self)
		self.photo_url: str = photo_url
		self.thumb_url: str = thumb_url
		self.photo_width: Optional[int] = None
		self.photo_height: Optional[int] = None
		self.title: Optional[str] = None
		self.description: Optional[str] = None


# https://core.telegram.org/bots/api#inlinequeryresultgif
class InlineQueryResultGif(InlineQueryResult, _Caption):
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


# https://core.telegram.org/bots/api#inlinequeryresultmpeg4gif
class InlineQueryResultMpeg4Gif(InlineQueryResult, _Caption):
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


# https://core.telegram.org/bots/api#inlinequeryresultvideo
class InlineQueryResultVideo(InlineQueryResult, _Caption):
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


# https://core.telegram.org/bots/api#inlinequeryresultaudio
class InlineQueryResultAudio(InlineQueryResult, _Caption):
	def __init__(self, id_: str, title: str, audio_url: str):
		InlineQueryResult.__init__(self, "audio", id_)
		_Caption.__init__(self)
		self.title: str = title
		self.audio_url: str = audio_url
		self.performer: Optional[str] = None
		self.audio_duration: Optional[int] = None


# https://core.telegram.org/bots/api#inlinequeryresultvoice
class InlineQueryResultVoice(InlineQueryResult, _Caption):
	def __init__(self, id_: str, title: str, voice_url: str):
		InlineQueryResult.__init__(self, "voice", id_)
		_Caption.__init__(self)
		self.title: str = title
		self.voice_url: str = voice_url
		self.voice_duration: Optional[int] = None


# https://core.telegram.org/bots/api#inlinequeryresultdocument
class InlineQueryResultDocument(InlineQueryResult, _Caption):
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


# https://core.telegram.org/bots/api#inlinequeryresultlocation
class InlineQueryResultLocation(InlineQueryResult, _Location):
	def __init__(self, id_: str, latitude: float, longitude: float, title: str):
		InlineQueryResult.__init__(self, "location", id_)
		_Location.__init__(self, latitude, longitude)
		self.title: str = title

		self.thumb_url: Optional[str] = None
		self.thumb_width: Optional[int] = None
		self.thumb_height: Optional[int] = None


# https://core.telegram.org/bots/api#inlinequeryresultvenue
class InlineQueryResultVenue(InlineQueryResult, _Venue):
	def __init__(self, id_: str, latitude: float, longitude: float, title: str, address: str):
		InlineQueryResult.__init__(self, "venue", id_)
		self.latitude: float = latitude
		self.longitude: float = longitude

		_Venue.__init__(self, title, address)

		self.thumb_url: Optional[str] = None
		self.thumb_width: Optional[int] = None
		self.thumb_height: Optional[int] = None


# https://core.telegram.org/bots/api#inlinequeryresultcontact
class InlineQueryResultContact(InlineQueryResult, _Contact):
	def __init__(self, id_: str, phone_number: str, first_name: str):
		InlineQueryResult.__init__(self, "contact", id_)
		_Contact.__init__(self, phone_number, first_name)

		self.thumb_url: Optional[str] = None
		self.thumb_width: Optional[int] = None
		self.thumb_height: Optional[int] = None


# https://core.telegram.org/bots/api#inlinequeryresultgame
class InlineQueryResultGame(InlineQueryResult):
	def __init__(self, id_: str, game_short_name: str):
		InlineQueryResult.__init__(self, "game", id_)
		self.game_short_name: str = game_short_name


# https://core.telegram.org/bots/api#inlinequeryresultcachedphoto
class InlineQueryResultCachedPhoto(InlineQueryResult, _Caption):
	def __init__(self, id_: str, photo_file_id: str):
		InlineQueryResult.__init__(self, "photo", id_)
		_Caption.__init__(self)
		self.photo_file_id: str = photo_file_id

		self.title: Optional[str] = None
		self.description: Optional[str] = None


# https://core.telegram.org/bots/api#inlinequeryresultcachedgif
class InlineQueryResultCachedGif(InlineQueryResult, _Caption):
	def __init__(self, id_: str, gif_file_id: str):
		InlineQueryResult.__init__(self, "gif", id_)
		_Caption.__init__(self)
		self.gif_file_id: str = gif_file_id

		self.title: Optional[str] = None


# https://core.telegram.org/bots/api#inlinequeryresultcachedmpeg4gif
class InlineQueryResultCachedMpeg4Gif(InlineQueryResult, _Caption):
	def __init__(self, id_: str, mpeg4_file_id: str):
		InlineQueryResult.__init__(self, "mpeg4_gif", id_)
		_Caption.__init__(self)
		self.mpeg4_file_id: str = mpeg4_file_id
		self.title: Optional[str] = None


# https://core.telegram.org/bots/api#inlinequeryresultcachedsticker
class InlineQueryResultCachedSticker(InlineQueryResult):
	def __init__(self, id_: str, sticker_file_id: str):
		InlineQueryResult.__init__(self, "sticker", id_)
		self.sticker_file_id: str = sticker_file_id


# https://core.telegram.org/bots/api#inlinequeryresultcacheddocument
class InlineQueryResultCachedDocument(InlineQueryResult, _Caption):
	def __init__(self, id_: str, title: str, document_file_id: str):
		InlineQueryResult.__init__(self, "document", id_)
		_Caption.__init__(self)
		self.title: str = title
		self.document_file_id: str = document_file_id

		self.description: Optional[str] = None


# https://core.telegram.org/bots/api#inlinequeryresultcachedvideo
class InlineQueryResultCachedVideo(InlineQueryResult, _Caption):
	def __init__(self, id_: str, title: str, video_file_id: str):
		InlineQueryResult.__init__(self, "video", id_)
		_Caption.__init__(self)
		self.title: str = title
		self.video_file_id: str = video_file_id

		self.description: Optional[str] = None


# https://core.telegram.org/bots/api#inlinequeryresultcachedvoice
class InlineQueryResultCachedVoice(InlineQueryResult, _Caption):
	def __init__(self, id_: str, title: str, voice_file_id: str):
		InlineQueryResult.__init__(self, "voice", id_)
		_Caption.__init__(self)
		self.title: str = title
		self.voice_file_id: str = voice_file_id

		self.description: Optional[str] = None


# https://core.telegram.org/bots/api#inlinequeryresultcachedaudio
class InlineQueryResultCachedAudio(InlineQueryResult, _Caption):
	def __init__(self, id_: str, audio_file_id: str):
		InlineQueryResult.__init__(self, "audio", id_)
		_Caption.__init__(self)
		self.audio_file_id: str = audio_file_id


# API METHODS
class API:
	def __init__(self, token: str, host: str = "api.telegram.org"):
		self.__host = host
		self.__token = token

	# https://core.telegram.org/bots/api#getupdates
	def get_updates(self, offset=None, limit=None, timeout=None, allowed_updates=None) -> List[Update]:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("getUpdates", params=params)
		update_list = data.get("result", None)
		return [Update(**d) for d in update_list]

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
		params = _make_optional(locals(), (self, certificate))
		form = MultiPartForm()
		form.write_params(params)
		if certificate:
			form.write_file(certificate, "certificate")

		data = self.__make_multipart_request(form, "setWebhook")
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#deletewebhook
	def delete_webhook(self, drop_pending_updates: Optional[bool] = None) -> bool:
		params = _make_optional({"drop_pending_updates": drop_pending_updates})
		data = self.__make_request("deleteWebhook", params=params)
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#getwebhookinfo
	def get_webhook_info(self):
		data = self.__make_request("getWebhookInfo", params={})
		return WebhookInfo(**data.get("result"))

	# https://core.telegram.org/bots/api#getme
	def get_me(self) -> User:
		data = self.__make_request("getMe", params={})
		return User(**data.get("result"))

	# https://core.telegram.org/bots/api#logout
	def log_out(self) -> bool:
		data = self.__make_request("logOut", params={})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#close
	def close(self) -> bool:
		data = self.__make_request("close", params={})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#sendmessage
	def send_message(
			self,
			chat_id: int,
			text: str,
			parse_mode: str = None,
			disable_web_page_preview: bool = None,
			disable_notification: bool = None,
			reply_to_message_id: int = None,
			reply_markup=None
	) -> Message:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("sendMessage", params=params)
		return Message(**data.get("result"))

	# https://core.telegram.org/bots/api#forwardmessage
	def forward_message(
			self,
			chat_id: Union[int, str],
			from_chat_id: Union[int, str],
			message_id: int,
			disable_notification: Optional[bool] = None
	) -> Message:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("forwardMessage", params=params)
		return Message(**data.get("result"))

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
			reply_markup: Optional[_KeyboardMarkup] = None
	) -> MessageId:
		params = _make_optional(locals(), (self, caption_entities))
		if caption_entities:
			params["caption_entities"] = json.dumps([e.serialize() for e in caption_entities])

		data = self.__make_request("copyMessage", params=params)
		return MessageId(**data.get("result"))

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
			reply_markup: Optional[_KeyboardMarkup] = None
	):
		params = _make_optional(locals(), (self, photo, caption_entities))
		if caption_entities:
			params["caption_entities"] = json.dumps([e.serialize() for e in caption_entities])

		form = MultiPartForm()
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
		params = _make_optional(locals(), (self, audio, caption_entities, thumb))
		if caption_entities:
			params["caption_entities"] = json.dumps([e.serialize() for e in caption_entities])

		form = MultiPartForm()
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
			reply_markup: Optional[_KeyboardMarkup] = None,
	):
		params = _make_optional(locals(), (self, document, caption_entities, thumb))
		if caption_entities:
			params["caption_entities"] = json.dumps([e.serialize() for e in caption_entities])

		form = MultiPartForm()
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
			reply_markup: Optional[_KeyboardMarkup] = None,
	):
		params = _make_optional(locals(), (self, video, caption_entities, thumb))
		if caption_entities:
			params["caption_entities"] = json.dumps([e.serialize() for e in caption_entities])

		form = MultiPartForm()
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
			reply_markup: Optional[_KeyboardMarkup] = None,
	):
		params = _make_optional(locals(), (self, animation, caption_entities, thumb))
		if caption_entities:
			params["caption_entities"] = json.dumps([e.serialize() for e in caption_entities])

		form = MultiPartForm()
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
			reply_markup: Optional[_KeyboardMarkup] = None,
	):
		params = _make_optional(locals(), (self, voice, caption_entities))
		if caption_entities:
			params["caption_entities"] = json.dumps([e.serialize() for e in caption_entities])

		form = MultiPartForm()
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
			reply_markup: Optional[_KeyboardMarkup] = None,
	):
		params = _make_optional(locals(), (self, video_note, caption_entities, thumb))
		if caption_entities:
			params["caption_entities"] = json.dumps([e.serialize() for e in caption_entities])

		form = MultiPartForm()
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
	):
		params = _make_optional(locals(), (self, media))
		params["media"] = json.dumps([m.serialize() for m in media])

		form = MultiPartForm()
		for m in media:
			if type(m.media) is str:
				continue
			input_file: InputFile = m.media
			if input_file.type == InputFile.InputType.FILE:
				form.write_file(input_file)
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
			reply_markup: Optional[_KeyboardMarkup] = None
	) -> MessageId:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("sendLocation", params=params)
		return MessageId(**data.get("result"))

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
			reply_markup: Optional[_KeyboardMarkup] = None
	) -> Union[MessageId, bool]:
		params = _make_optional(locals(), (self,))
		assert (chat_id and message_id) or inline_message_id, "chat_id and message_id or inline_message_id must be set"
		data = self.__make_request("editMessageLiveLocation", params=params)
		result = bool(data.get("result")) if inline_message_id else MessageId(**data.get("result"))
		return result

	# https://core.telegram.org/bots/api#stopmessagelivelocation
	def stop_message_live_location(
			self,
			chat_id: Optional[Union[int, str]] = None,
			message_id: Optional[int] = None,
			inline_message_id: Optional[str] = None,
			reply_markup: Optional[_KeyboardMarkup] = None
	) -> Union[MessageId, bool]:
		params = _make_optional(locals(), (self,))
		assert (chat_id and message_id) or inline_message_id, "chat_id and message_id or inline_message_id must be set"
		data = self.__make_request("stopMessageLiveLocation", params=params)
		result = bool(data.get("result")) if inline_message_id else MessageId(**data.get("result"))
		return result

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
			reply_markup: Optional[_KeyboardMarkup] = None
	) -> MessageId:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("sendVenue", params=params)
		return MessageId(**data.get("result"))

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
			reply_markup: Optional[_KeyboardMarkup] = None
	) -> MessageId:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("sendContact", params=params)
		return MessageId(**data.get("result"))

	# https://core.telegram.org/bots/api#sendcontact
	def send_poll(
			self,
			chat_id: Union[int, str],
			question: str,
			options: List[str],
			is_anonymous: Optional[bool] = None,
			type_: Optional[str] = None,
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
			reply_markup: Optional[_KeyboardMarkup] = None
	) -> MessageId:
		params = _make_optional(locals(), (self, type_))
		params["type"] = type_
		if explanation_entities:
			params["explanation_entities"] = json.dumps([e.serialize() for e in explanation_entities])
		data = self.__make_request("sendPoll", params=params)
		return MessageId(**data.get("result"))

	# https://core.telegram.org/bots/api#senddice
	def send_dice(
			self,
			chat_id: Union[int, str],
			emoji: Optional[str] = None,
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[_KeyboardMarkup] = None
	) -> MessageId:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("sendDice", params=params)
		return MessageId(**data.get("result"))

	# https://core.telegram.org/bots/api#sendchataction
	def send_chat_action(
			self,
			chat_id: Union[int, str],
			action: Optional[str] = None,
	) -> bool:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("sendChatAction", params=params)
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#getuserprofilephotos
	def get_user_profile_photos(
			self,
			user_id: int,
			offset: Optional[int] = None,
			limit: Optional[int] = None,
	) -> UserProfilePhotos:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("getUserProfilePhotos", params=params)
		return UserProfilePhotos(**data.get("result"))

	# https://core.telegram.org/bots/api#getfile
	def get_file(self, file_id: str) -> File:
		data = self.__make_request("getFile", params={"file_id": file_id})
		return File(**data.get("result"))

	# https://core.telegram.org/bots/api#kickchatmember
	def kick_chat_member(self, chat_id: Union[int, str], user_id: int, until_date: Optional[int] = None) -> bool:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("kickChatMember", params=params)
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#unbanchatmember
	def unban_chat_member(self, chat_id: Union[int, str], user_id: int, only_if_banned: Optional[bool] = None) -> bool:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("unbanChatMember", params=params)
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#restrictchatmember
	def restrict_chat_member(
			self,
			chat_id: Union[int, str],
			user_id: int,
			permissions: ChatPermissions,
			until_date: Optional[int] = None
	) -> bool:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("restrictChatMember", params=params)
		return bool(data.get("result"))

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
		params = _make_optional(locals(), (self,))
		data = self.__make_request("promoteChatMember", params=params)
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#setchatadministratorcustomtitle
	def set_chat_administrator_custom_title(
			self,
			chat_id: Union[int, str],
			user_id: int,
			custom_title: str,
	) -> bool:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("setChatAdministratorCustomTitle", params=params)
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#setchatpermissions
	def set_chat_permissions(
			self,
			chat_id: Union[int, str],
			permissions: ChatPermissions,
	) -> bool:
		data = self.__make_request("setChatPermissions", {"chat_id": chat_id, "permissions": permissions})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#exportchatinvitelink
	def export_chat_invite_link(self, chat_id: Union[int, str]) -> str:
		data = self.__make_request("exportChatInviteLink", {"chat_id": chat_id})
		return str(data.get("result"))

	# https://core.telegram.org/bots/api#setchatphoto
	def set_chat_photo(
			self,
			chat_id: Union[int, str],
			photo: InputFile,
	) -> bool:
		form = MultiPartForm()
		form.write_params({"chat_id": chat_id})
		form.write_one_input(photo, "photo")

		data = self.__make_multipart_request(form, "setChatPhoto")
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#deletechatphoto
	def delete_chat_photo(self, chat_id: Union[int, str]) -> bool:
		data = self.__make_request("deleteChatPhoto", {"chat_id": chat_id})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#setchattitle
	def set_chat_title(self, chat_id: Union[int, str], title: str) -> bool:
		data = self.__make_request("setChatTitle", {"chat_id": chat_id, "title": title})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#setchatdescription
	def set_chat_description(self, chat_id: Union[int, str], description: str) -> bool:
		data = self.__make_request("setChatDescription", {"chat_id": chat_id, "description": description})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#pinchatmessage
	def pin_chat_message(
			self,
			chat_id: Union[int, str],
			message_id: int,
			disable_notification: Optional[bool] = None
	) -> bool:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("pinChatMessage", params)
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#unpinchatmessage
	def unpin_chat_message(self, chat_id: Union[int, str], message_id: Optional[int]) -> bool:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("unpinChatMessage", params)
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#unpinallchatmessages
	def unpin_all_chat_messages(self, chat_id: Union[int, str]) -> bool:
		data = self.__make_request("unpinAllChatMessages", {"chat_id": chat_id})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#leavechat
	def leave_chat(self, chat_id: Union[int, str]) -> bool:
		data = self.__make_request("leaveChat", {"chat_id": chat_id})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#getchat
	def get_chat(self, chat_id: Union[int, str]) -> Chat:
		data = self.__make_request("getChat", {"chat_id": chat_id})
		return Chat(**data.get("result"))

	# https://core.telegram.org/bots/api#getchatadministrators
	def get_chat_administrators(self, chat_id: Union[int, str]) -> List[ChatMember]:
		data = self.__make_request("getChatAdministrators", {"chat_id": chat_id})
		return [ChatMember(**d) for d in data.get("result")]

	# https://core.telegram.org/bots/api#getchatmemberscount
	def get_chat_members_count(self, chat_id: Union[int, str]) -> int:
		data = self.__make_request("getChatMembersCount", {"chat_id": chat_id})
		return int(data.get("result"))

	# https://core.telegram.org/bots/api#getchatmemberscount
	def get_chat_member(self, chat_id: Union[int, str], user_id: int) -> ChatMember:
		data = self.__make_request("getChatMember", {"chat_id": chat_id, "user_id": user_id})
		return ChatMember(**data.get("result"))

	# https://core.telegram.org/bots/api#setchatstickerset
	def set_chat_sticker_set(self, chat_id: Union[int, str], sticker_set_name: str) -> bool:
		data = self.__make_request("setChatStickerSet", {"chat_id": chat_id, "sticker_set_name": sticker_set_name})
		return bool(data.get("result"))

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
		params = _make_optional(locals(), (self,))
		data = self.__make_request("answerCallbackQuery", params=params)
		return bool(data.get("result"))

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
		params = _make_optional(locals(), (self, entities))
		assert (chat_id and message_id) or inline_message_id, "chat_id and message_id or inline_message_id must be set"
		if entities:
			params["entities"] = [e.serialize() for e in entities]
		data = self.__make_request("editMessageText", params)
		return Message(**data.get("result"))

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
		params = _make_optional(locals(), (self, caption_entities))
		assert (chat_id and message_id) or inline_message_id, "chat_id and message_id or inline_message_id must be set"
		if caption_entities:
			params["caption_entities"] = [e.serialize() for e in caption_entities]
		data = self.__make_request("editMessageCaption", params)
		return Message(**data.get("result"))

	# https://core.telegram.org/bots/api#editmessagecaption
	def edit_message_media(
			self,
			media: InputMedia,
			chat_id: Optional[Union[int, str]] = None,
			message_id: Optional[int] = None,
			inline_message_id: Optional[str] = None,
			reply_markup: Optional[InlineKeyboardMarkup] = None,
	) -> Message:
		params = _make_optional(locals(), (self,))
		assert media.media.type != InputFile.InputType.FILE, "can't upload file while edit message"
		assert (chat_id and message_id) or inline_message_id, "chat_id and message_id or inline_message_id must be set"
		data = self.__make_request("editMessageMedia", params)
		return Message(**data.get("result"))

	# https://core.telegram.org/bots/api#editmessagereplymarkup
	def edit_message_reply_markup(
			self,
			chat_id: Optional[Union[int, str]] = None,
			message_id: Optional[int] = None,
			inline_message_id: Optional[str] = None,
			reply_markup: Optional[InlineKeyboardMarkup] = None,
	) -> Message:
		params = _make_optional(locals(), (self,))
		assert (chat_id and message_id) or inline_message_id, "chat_id and message_id or inline_message_id must be set"
		data = self.__make_request("editMessageReplyMarkup", params)
		result = bool(data.get("result")) if inline_message_id else Message(**data.get("result"))
		return result

	# https://core.telegram.org/bots/api#stoppoll
	def stop_poll(
			self,
			chat_id: Union[int, str],
			message_id: int,
			reply_markup: Optional[InlineKeyboardMarkup] = None,
	) -> Poll:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("stopPoll", params)
		return Poll(**data.get("result"))

	# https://core.telegram.org/bots/api#deletemessage
	def delete_message(self, chat_id: Union[int, str], message_id: int) -> bool:
		data = self.__make_request("deleteMessage", {"chat_id": chat_id, "message_id": message_id})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#sendsticker
	def send_sticker(
			self,
			chat_id: Union[int, str],
			sticker: Union[InputFile, str],
			disable_notification: Optional[bool] = None,
			reply_to_message_id: Optional[int] = None,
			allow_sending_without_reply: Optional[bool] = None,
			reply_markup: Optional[_KeyboardMarkup] = None
	) -> Message:
		params = _make_optional(locals(), (self, sticker))
		form = MultiPartForm()
		form.write_params(params)
		form.write_one_input(sticker, "sticker")

		data = self.__make_multipart_request(form, "sendSticker")
		return Message(**data.get("result"))

	# https://core.telegram.org/bots/api#getstickerset
	def get_sticker_set(self, name: str) -> StickerSet:
		data = self.__make_request("getStickerSet", {"name": name})
		return StickerSet(**data.get("result"))

	# https://core.telegram.org/bots/api#uploadstickerfile
	def upload_sticker_file(
			self,
			user_id: int,
			png_sticker: InputFile
	) -> File:
		form = MultiPartForm()
		form.write_params({"user_id": user_id})
		form.write_one_input(png_sticker, "png_sticker")

		data = self.__make_multipart_request(form, "uploadStickerFile")
		return File(**data.get("result"))

	def __stickers(self, method, params, png_sticker, tgs_sticker):
		assert bool(png_sticker) ^ bool(tgs_sticker), "png_sticker or tgs_sticker must be set"
		form = MultiPartForm()
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
		params = _make_optional(locals(), (self, png_sticker, tgs_sticker))
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
		params = _make_optional(locals(), (self, png_sticker, tgs_sticker))
		return self.__stickers("addStickerToSet", params, png_sticker, tgs_sticker)

	# https://core.telegram.org/bots/api#setstickerpositioninset
	def set_sticker_position_in_set(self, sticker: str, position: int) -> bool:
		data = self.__make_request("setStickerPositionInSet", {"sticker": sticker, "position": position})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#deletestickerfromset
	def delete_sticker_from_set(self, sticker: str) -> bool:
		data = self.__make_request("deleteStickerFromSet", {"sticker": sticker})
		return bool(data.get("result"))

	# https://core.telegram.org/bots/api#setstickersetthumb
	def set_sticker_set_thumb(
			self,
			name: str,
			user_id: int,
			thumb: Optional[Union[InputFile, str]]
	) -> File:
		form = MultiPartForm()
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
	):
		params = _make_optional(locals(), (self, results))
		params["results"] = [r.serialize() for r in results]
		data = self.__make_request("answerInlineQuery", params)

	def __get_url(self, api_method) -> str:
		return f'https://{self.__host}/bot{self.__token}/{api_method}'

	def __make_multipart_request(self, form, api_method):
		url = self.__get_url(api_method)
		resp = form.make_request(self.__host, url)
		return self.__process_response(resp)

	def __make_request(self, api_method: str, params: Optional[dict] = None, method="POST"):
		url = self.__get_url(api_method)
		params = {k: json.dumps(v.serialize()) if hasattr(v, "serialize") else v for k, v in params.items()}
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
			print(resp)
			raise ValueError("unexpected reason", data)

		if resp.getcode() != 200:
			data = resp.read()
			raise ValueError("unexpected code", data)

		data = resp.read()
		parsed_data = json.loads(data)
		return parsed_data
