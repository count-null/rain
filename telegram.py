import requests
from notify import Logger


class TelegramCreds:
    def __init__(self, api_token: str, chat_id: str):
        self.api_token = api_token
        self.chat_id = chat_id


class Telegram:
    def __init__(self, creds: TelegramCreds, log: Logger):
        self.creds = creds
        self.log = log
        self.last_update_id = None

    def telegram_request(self, endpoint, params):
        url = f"https://api.telegram.org/bot{self.creds.api_token}/{endpoint}{params}"
        res = requests.get(url).json()
        if res['ok']:
            return res['result']
        self.log.warning(f"Telegram failed !!! {endpoint}{params}")

    def send_message(self, message):
        return self.telegram_request('sendMessage', f'?chat_id={self.creds.chat_id}&text={message}&parse_mode=Markdown')

    def get_updates(self):
        return self.telegram_request('getUpdates', f'?chat_id={self.creds.chat_id}&offset={self.last_update_id}')

    def ack_update(self, update_id):
        self.last_update_id = int(update_id) + 1
