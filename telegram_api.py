import binascii
import http.client
import json
import mimetypes
import os
import stat
from enum import Enum
from io import BytesIO
from typing import List, Optional, Tuple, KeysView
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


def _make_optional(params: dict, exclude=()):
	return {k: v for k, v in params.items() if v is not None and v not in exclude}


def _fill_object(target, data):
	for k, v in data.items():
		setattr(target, k, __ch_list(target, k, v))


def __ch_list(target, k, v):
	return [__ch_obj(target, k, a) for a in v] if type(v) is list else __ch_obj(target, k, v)


def __ch_obj(target, k, v):
	return target.get_fields_map().get(k, DefaultFieldObject)(**v) if type(v) is dict else target.get_simple_field(k, v)


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

	def __init__(self, type_: InputType, value: [int, str]) -> None:
		super().__init__()
		self.type = type_
		self.value = value
		self.file_name = value
		if type_ == InputFile.InputType.FILE:
			self.file_name = value.split('/')[-1]

	def serialize(self):
		raise NotImplementedError("serialize method must be implemented")


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


# service class
class _InputBase(_Serializable):
	def __init__(self, type_: str, media: [str, InputFile]):
		self.type: str = type_
		self.media: [str, InputFile] = media
		self.caption: Optional[str] = None
		self.parse_mode: Optional[str] = None
		self.caption_entities: Optional[List[MessageEntity]] = None

	def serialize(self):
		if type(self.media) == str:
			media = self.media
		elif self.media.type == InputFile.InputType.FILE:
			media = f'attach://{self.media.value}'
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
class _InputThumb(_InputBase):
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
class InputMediaPhoto(_InputBase):

	def __init__(self, media: [str, InputFile]):
		super().__init__("photo", media)


# https://core.telegram.org/bots/api#inputmediavideo
class InputMediaVideo(_InputThumb):
	def __init__(self, type_: str, media: str):
		super().__init__(type_, media)
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
	def __init__(self, type_: str, media: str):
		super().__init__(type_, media)
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
	def __init__(self, type_: str, media: str):
		super().__init__(type_, media)
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
	def __init__(self, type_: str, media: str):
		super().__init__(type_, media)
		self.disable_content_type_detection: Optional[bool] = None

	def serialize(self):
		result = super().serialize()
		result.update(_make_optional({
			"disable_content_type_detection": self.disable_content_type_detection,
		}))
		return result


# API Classes
class DefaultFieldObject:
	def __init__(self, **kwargs):
		self.__data: dict = kwargs
		_fill_object(self, kwargs)

	def __repr__(self):
		return f'[DefaultDataClass] data: {self.__data}'

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
		}.copy()


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


class MaskPosition(DefaultFieldObject):
	def __init__(self, **kwargs):
		self.point: str = ""
		self.x_shift: float = 0
		self.y_shift: float = 0
		self.scale: float = 0
		DefaultFieldObject.__init__(self, **kwargs)


class FileBase:
	def __init__(self):
		self.file_id: str = ""  # Identifier for this file, which can be used to download or reuse the file
		self.file_unique_id: str = ""  # Unique	identifier for this file, which is supposed to be the same over time and for different bots. Can't be used to download or reuse the file.
		self.file_size: int = 0  # Optional. File size


class Bounds:
	def __init__(self):
		self.width: int = 0  # Photo width
		self.height: int = 0  # Photo height


class PhotoSize(FileBase, Bounds, DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		Bounds.__init__(self)
		DefaultFieldObject.__init__(self, **kwargs)


class FileDescription:
	def __init__(self):
		self.file_name: str = ""
		self.mime_type: str = ""
		self.thumb: Optional[PhotoSize] = None


class Animation(FileBase, FileDescription, Bounds, DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		FileDescription.__init__(self)
		Bounds.__init__(self)
		self.duration: int = 0
		DefaultFieldObject.__init__(self, **kwargs)


class Audio(FileBase, FileDescription, DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		FileDescription.__init__(self)
		self.duration: int = 0
		self.performer: str = ""
		self.title: str = ""
		DefaultFieldObject.__init__(self, **kwargs)


class Document(FileBase, FileDescription, DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		FileDescription.__init__(self)
		DefaultFieldObject.__init__(self, **kwargs)


class Video(FileBase, FileDescription, Bounds, DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		FileDescription.__init__(self)
		Bounds.__init__(self)
		self.duration: int = 0
		DefaultFieldObject.__init__(self, **kwargs)


class VideoNote(FileBase, DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		self.length: int = 0  # Video width and height (diameter of the video message) as defined by sender
		self.duration: int = 0  # Duration of the video in seconds as defined by sender
		self.thumb: Optional[PhotoSize] = None
		DefaultFieldObject.__init__(self, **kwargs)


class Voice(FileBase, DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		self.duration: int = 0  # Duration of the audio in seconds as defined by sender
		self.mime_type: str = ""
		DefaultFieldObject.__init__(self, **kwargs)


class Sticker(FileBase, Bounds, DefaultFieldObject):
	def __init__(self, **kwargs):
		FileBase.__init__(self)
		Bounds.__init__(self)
		self.is_animated: bool = False  # True,	if the sticker is animated
		self.thumb: Optional[PhotoSize] = None  # Optional.Sticker thumbnail in the.WEBP or.JPG format
		self.emoji: str = ""  # Optional.Emoji	associated	with the sticker
		self.set_name: str = ""  # Optional.Name	of	the	sticker	set	to	which the	sticker	belongs
		self.mask_position: Optional[
			MaskPosition] = None  # Optional. For mask stickers, the position where	the	mask should	be placed
		DefaultFieldObject.__init__(self, **kwargs)


class User(DefaultFieldObject, _Serializable):
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


class ChatMember(DefaultFieldObject):
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

		DefaultFieldObject.__init__(self, **kwargs)


class Chat(DefaultFieldObject):
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

		DefaultFieldObject.__init__(self, **kwargs)

	@staticmethod
	def get_simple_field(name, value):
		if name == "type":
			return ChatType(value)
		return value


class MessageEntity(DefaultFieldObject, _Serializable):
	def __init__(self, **kwargs):
		self.type: MessageEntityType = MessageEntityType.WRONG
		self.offset: int = 0
		self.length: int = 0

		self.url: Optional[str] = None
		self.user: Optional[User] = None
		self.language: Optional[str] = None

		DefaultFieldObject.__init__(self, **kwargs)

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

		DefaultFieldObject.__init__(self, **kwargs)
		# we can't use "from" word in code
		self.from_user: Optional[User] = getattr(self, "from")

	def get_entities_by_type(self, entity_type: MessageEntityType) -> Tuple[str]:
		return tuple(e.get_value(self.text) for e in self.entities if e.type == entity_type)


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


# API METHODS
class API:
	def __init__(self, token: str, host: str = "api.telegram.org"):
		self.__host = host
		self.__token = token

	def __get_url(self, api_method) -> str:
		return f'https://{self.__host}/bot{self.__token}/{api_method}'

	def __make_request(self, api_method, method="POST", params=None):
		url = self.__get_url(api_method)
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
			raise ValueError("unexpected reason")

		if resp.getcode() != 200:
			raise ValueError("unexpected code")

		data = resp.read()
		parsed_data = json.loads(data)
		return parsed_data

	# https://core.telegram.org/bots/api#getupdates
	def get_updates(self, offset=None, limit=None, timeout=None, allowed_updates=None) -> List[Update]:
		params = _make_optional(locals(), (self,))
		data = self.__make_request("getUpdates", params=params)
		update_list = data.get("result", None)
		return [Update(**d) for d in update_list]

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
	):
		params = {"chat_id": chat_id, "text": text}
		params.update(_make_optional(locals(), (self, chat_id, params, text)))
		data = self.__make_request("sendMessage", params=params)
		return data

	# https://core.telegram.org/bots/api#sendphoto
	def send_photo(
			self,
			chat_id: [int, str],
			photo: [InputFile, str],
			caption: str = None,
			parse_mode: str = None,
			caption_entities: list = None,
			disable_notification: bool = None,
			reply_to_message_id: int = None,
			allow_sending_without_reply: bool = None,
			reply_markup=None,
	):
		params = {"chat_id": chat_id}
		params.update(_make_optional(locals(), (self, chat_id, photo, params)))

		if type(photo) is str:
			params.update({"photo": photo})
			return self.__make_request("sendPhoto", params=params)

		photo: InputFile = photo

		# Do multipart request in this case
		form = MultiPartForm()

		if photo.type != InputFile.InputType.FILE:
			params.update({"photo": photo.value})
		else:
			with open(photo.value, mode="rb") as f:
				form.write_file(photo, "photo")

		form.write_params(params)

		url = self.__get_url("sendPhoto")
		resp = form.make_request(self.__host, url)
		data = self.__process_response(resp)
		return Message(**data.get("result", None))

	# https://core.telegram.org/bots/api#sendmediagroup
	def send_media_group(
			self,
			chat_id: [int, str],
			media: List[_InputBase],
			disable_notification: bool = None,
			reply_to_message_id: int = None,
			allow_sending_without_reply: bool = None
	):
		params = _make_optional(locals(), (self, media))
		params["media"] = [m.serialize() for m in media]

		form = MultiPartForm()
		form.write_params(params)
		for m in media:
			if type(m.media) is str:
				continue
			input_file: InputFile = m.media
			if input_file.type == InputFile.InputType.FILE:
				with open(input_file.value, mode="rb") as f:
					form.write_file(input_file)

		url = self.__get_url("sendMediaGroup")
		resp = form.make_request(self.__host, url)
		data = self.__process_response(resp)
		return Message(**data.get("result", None))

	# https://core.telegram.org/bots/api#getchatadministrators
	def get_chat_administrators(self, chat_id: [int, str]) -> List[ChatMember]:
		params = {"chat_id": chat_id}
		data = self.__make_request("getChatAdministrators", params=params)
		result_list = data.get("result", None)
		return [ChatMember(**d) for d in result_list]
