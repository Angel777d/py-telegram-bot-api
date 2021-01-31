from telegram_api import API, Update, MessageEntityType
from pooling import Pooling

BOT_NAME = "Test Bot"
api = API(token="Your bot API key here")


def handler(update: Update):
	# this bot support only messages
	if not update.message:
		return
	msg = update.message

	# this bot support only messages, contains "/". /help for example
	commands = msg.get_entities_by_type(MessageEntityType.BOT_COMMAND)
	for command in commands:

		if command == "/help":
			api.send_message(msg.chat.id, f'This is a /help message for {BOT_NAME}.')
			return
		if command == "/start":
			user = msg.from_user
			user_name = user.username or user.first_name or user.last_name
			api.send_message(msg.chat.id, f'/start command processed by {BOT_NAME} for {user_name}.')
			return

	api.send_message(msg.chat.id, f'Sorry, {BOT_NAME} can\'t help you with "{msg.text}"')


pooling = Pooling(api, handler, 1).start()
