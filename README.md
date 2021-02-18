# Simple Telegram Bot API

## Designed to be simple, zero dependency, one file python telegram bot api wrapper

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/6d8bcaad92474d448d74fd8c7a8a39a4)](https://app.codacy.com/gh/Angel777d/py-telegram-bot-api?utm_source=github.com&utm_medium=referral&utm_content=Angel777d/py-telegram-bot-api&utm_campaign=Badge_Grade)
[![license](https://img.shields.io/github/license/angel777d/py-telegram-bot-api?style=flat-square)](https://github.com/Angel777d/py-telegram-bot-api/blob/main/LICENSE)
[![pip version](https://img.shields.io/pypi/v/py-telegram-bot-api.svg?style=flat-square)](https://pypi.org/project/py-telegram-bot-api/)
[![python version](https://img.shields.io/badge/python-3.6+-blue.svg?style=flat-square)](https://pypi.org/project/py-telegram-bot-api/)

[![telegram chat](https://img.shields.io/badge/telegram-chat-blue.svg?style=flat-square&logo=telegram)](https://t.me/joinchat/H-ktOmOiJgFuR7ls)

### Introduction

This library implements telegram bot [API](https://core.telegram.org/bots/api)
in python. With no dependencies.

All fields and methods of
[API](https://core.telegram.org/bots/api)
use [typing](https://docs.python.org/3/library/typing.html).

Bot API 5.0 (November 4, 2020) is fully supported.

### Disclaimer
This library and its author neither associated, nor affiliated with Telegram in any way. 

### Installation

`pip install py-telegram-bot-api`

Or you can just download
[api.py](https://raw.githubusercontent.com/Angel777d/py-telegram-bot-api/main/telegram_bot_api/api.py)
file and do whatever you want.

### Quick start

*   Copy code from [`bot_example.py`](https://github.com/Angel777d/py-telegram-bot-api/blob/main/bot_example.py)
*   Create your bot with [this instruction](https://core.telegram.org/bots#3-how-do-i-create-a-bot) and get bot API key
*   Put bot API key in [`bot_example.py`](https://github.com/Angel777d/py-telegram-bot-api/blob/main/bot_example.py)
*   Run script: `python bot_example.py`
*   Write "/start" or "/help" to your bot in telegram

### Documentation

All documentation you need can be found [here](https://core.telegram.org/bots/api).

Differences:

*   Library methods use "snake_case_style" instead of "camelCaseStyle" in telegram docs.

*   Message structure use `from_user` instead of `from`
  (from is a reserved word in Python)

### Lib Structure

`api.py` module represents all telegram bot API methods and structures. This is the only file you really want to work
with telegram bot API.

`pooling.py`
calls [`getUpdates()`](https://core.telegram.org/bots/api#getupdates)
method in a loop. Can be used instead of webhook. More info about pooling and webhooks
are [here](https://core.telegram.org/bots/api#getting-updates).

`utils.py` module contains useful code.

### Status

Development done. Tests in progress.

<details>
  <summary>Progress status</summary>

*   All classes added
*   All methods added

  ---------------------

#### Tested methods

*   get_updates
*   set_webhook
*   delete_webhook
*   get_webhook_info
*   get_me
*   log_out
*   close
*   send_message
*   forward_message
*   copy_message
*   send_photo
*   send_audio
*   send_document
*   send_video
*   send_animation
*   send_voice
*   send_video_note
*   send_media_group
*   send_location
*   edit_message_live_location
*   stop_message_live_location
*   send_venue
*   send_contact
*   send_poll

#### Not tested methods

*   send_dice
*   send_chat_action
*   get_user_profile_photos
*   get_file
*   kick_chat_member
*   unban_chat_member
*   restrict_chat_member
*   promote_chat_member
*   set_chat_administrator_custom_title
*   set_chat_permissions
*   export_chat_invite_link
*   set_chat_photo
*   delete_chat_photo
*   set_chat_title
*   set_chat_description
*   pin_chat_message
*   unpin_chat_message
*   unpin_all_chat_messages
*   leave_chat
*   get_chat
*   get_chat_administrators
*   get_chat_members_count
*   get_chat_member
*   set_chat_sticker_set
*   delete_chat_sticker_set
*   answer_callback_query
*   set_my_commands
*   get_my_commands
*   edit_message_text
*   edit_message_caption
*   edit_message_media
*   edit_message_reply_markup
*   stop_poll
*   delete_message
*   send_sticker
*   get_sticker_set
*   upload_sticker_file
*   create_new_sticker_set
*   add_sticker_to_set
*   set_sticker_position_in_set
*   delete_sticker_from_set
*   set_sticker_set_thumb
*   answer_inline_query
*   send_invoice
*   answer_shipping_query
*   answer_pre_checkout_query
*   set_passport_data_errors
*   send_game
*   get_game_high_scores

  ---------------------

#### Known issues

*   No issues yet

</details>
