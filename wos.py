import requests
import time
import hmac
import hashlib
from json import dumps
from config import SwapMethod
from notify import Logger

BASE_URL = "https://www.livingroomofsatoshi.com"


def create_wos_account():
    ext = "/api/v1/wallet/account"
    data = {
        "referrer": "walletofsatoshi"
    }
    json = requests.post(BASE_URL + ext, json=data).json()
    print(dumps(json, indent=2))


class WosCreds:
    def __init__(self, creds: dict):
        self.api_secret = creds['api_secret']
        self.api_token = creds['api_token']
        self.btc_deposit_address = creds['btc_deposit_address']
        self.lightning_address = creds['lightning_address']


class Wos(SwapMethod):
    def __init__(self, creds: WosCreds, log: Logger):
        self.session = requests.Session()
        self.creds = creds
        self.session.headers.update({"api-token": self.creds.api_token})
        print(self.get_account_balance())

    def wos_request(self, ext, data_str: str, sign: bool):
        path_url = BASE_URL + ext
        if sign and data_str:
            self.sign_session(ext, data_str)
        resp_json = self.session.post(path_url, data=data_str.encode("utf-8")).json()
        self.unsign_session()
        return resp_json

    def sign_session(self, ext, params):
        nonce = str(int(time.time() * 1000))
        api_token = self.creds.api_token
        api_secret = self.creds.api_secret

        m = ext + nonce + api_token + params
        hmac_key = api_secret.encode("utf-8")
        signature = hmac.new(hmac_key, m.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()

        self.session.headers.update({
            'signature': signature,
            'nonce': nonce,
            'api-token': api_token,
        })

    def unsign_session(self):
        self.session.headers.pop("signature", None)
        self.session.headers.pop("nonce", None)

    def get_onchain_address(self):
        return self.creds.btc_deposit_address

    def get_account_balance(self):
        ext = "/api/v1/wallet/walletData"
        json = self.session.get(BASE_URL + ext).json()
        _sum = sum(map(float, [json[kwarg] for kwarg in ["btc", "lightning", "btcUnconfirmed"]]))
        return int(json["btc"]) + int(json["lightning"]) + int(json["btcUnconfirmed"])

    def pay_invoice(self, invoice: str, amount_btc: float):
        ext = "/api/v1/wallet/payment"
        data_str = '{"address":"%s","currency":"LIGHTNING","amount":%d,"sendMaxLightning":true,"description":""}' % invoice, amount_btc
        resp_json = self.wos_request(ext, str(data_str), sign=True)
        status = resp_json["status"]
        tx_id = resp_json["transactionId"]
        return status == "PAID", tx_id

    def get_lightning_invoice(self, sats):
        ext = "/api/v1/wallet/createInvoice"
        data_str = '{"amount":%d,"description":"Wallet of Satoshi"}' % sats
        resp_json = self.wos_request(ext, data_str, sign=True)
        invoice = resp_json["invoice"]
        return invoice

    def estimate_onchain_fee(self):
        ext = "/api/v1/wallet/feeEstimate"
        params = {
            "address": "34c5izdES7Wt4x38SEfnUCVtoNj6F2wPPe",
            "amount": 0
        }
        resp_json = self.session.get(BASE_URL + ext, params=params).json()
        return resp_json["btcFixedFee"]

    def send_onchain(self, address: str, amount_btc: float):
        ext = "/api/v1/wallet/payment"
        data_str = '{"address":"%s","currency":"BTC","amount":%d,"sendMaxLightning":true,"description":null}' % address, amount_btc
        resp_json = self.wos_request(ext, str(data_str), sign=True)
        status = resp_json["status"]
        tx_id = resp_json["transactionId"]
        return status == "PAID", tx_id
