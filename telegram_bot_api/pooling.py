import logging
from threading import Thread
from time import sleep
from typing import Callable

from telegram_bot_api import API, Update


class Pooling:
	def __init__(self, api, handler: Callable[[Update], None], update_time: float = 5, dev_mode: bool = False):
		self.__api: API = api
		self.__handler: Callable[[Update], None] = handler
		self.__update_time: float = update_time
		self.__pooling: [Thread, None] = None
		self.__lastUpdate: int = 0
		self.__isRunning = False
		self.__dev_mode = dev_mode

	def start(self):
		if self.__pooling:
			raise RuntimeError("Pooling already running")

		self.__isRunning = True
		self.__pooling = Thread(target=self.__request_update)
		self.__pooling.start()

		return self

	def stop(self):
		if not self.__pooling:
			raise RuntimeError("Pooling not running")

		self.__isRunning = False

	def __request_update(self):
		logging.debug("[Pooling] started")
		while self.__isRunning:
			if self.__dev_mode:
				self.__do_request()
			else:
				try:
					self.__do_request()
				except Exception as ex:
					logging.error("[Pooling] got exception", exc_info=ex)
			sleep(self.__update_time)
		self.__pooling = None
		logging.debug("[Pooling] stopped")

	def __do_request(self):
		updates = self.__api.get_updates(offset=self.__lastUpdate)
		for update in updates:
			self.__lastUpdate = update.update_id + 1
			self.__handler(update)
