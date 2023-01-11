import logging
from telegram import Telegram, TelegramCreds


class Logger:
    def __init__(self, filename: str, notify_creds: TelegramCreds):
        logging.basicConfig(filename=filename, filemode='a', format='[%(asctime)s] %(levelname)-8s %(message)s') 
        self.log = logging.getLogger()
        self.log.setLevel(logging.INFO)
        self.notify_connector = Telegram(notify_creds, self)
        self.filename = filename

    def info(self, message):
        self.log.info(message)

    def warning(self, message):
        self.log.warning(message)

    def error(self, message):
        self.log.error(message)

    def debug(self, message):
        self.log.debug(message)

    def notify(self, message):
        self.info(f"Notifying the operator: {message}")
        self.notify_connector.send_message(message)
