import configparser
from listeners import FundingListenerConfig, FundingListener, MempoolListenerConfig, MempoolListener, HtlcStreamLoggerConfig, HtlcStreamLogger
from channels import SinkNodeConfig, SinkNodeState, SinkNodeManager, SourceNodeConfig, SourceNodeState, SourceNodeManager
from notify import Logger
from kraken import Kraken, KrakenCreds
from nicehash import Nicehash, NicehashCreds
from muun import Muun, MuunCreds
from telegram import TelegramCreds


class Config:
    def __init__(self, config_file):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)


class SwapMethod:
    def get_onchain_address(self):
        # returns address string
        raise NotImplementedError

    def send_onchain(self):
        # sends entire account balance to saved onchain address
        raise NotImplementedError

    def get_account_balance(self):
        # returns total balance in sats
        raise NotImplementedError

    def pay_invoice(self, inv):
        # attempts to pay the invoice using account balance
        raise NotImplementedError

    def get_lightning_invoice(self):
        # returns bolt11 invoice string
        raise NotImplementedError

    def estimate_onchain_fee(self):
        # returns the total fee in satoshis
        raise NotImplementedError


swap_methods = {
    "KRAKEN": {
        'creds': KrakenCreds,
        'operator': Kraken
    },
    "NICEHASH": {
        'creds': NicehashCreds,
        'operator': Nicehash
    },
    "MUUN": {
        'creds': MuunCreds,
        'operator': Muun
    }
}

listen_methods = {
    'HTLC_STREAM_LOGGER': {
        'config': HtlcStreamLoggerConfig,
        'listener': HtlcStreamLogger
    },
    "MEMPOOL_NOTIFY": {
        'config': MempoolListenerConfig,
        'listener': MempoolListener
    },
    "FUNDING_NOTIFY": {
        'config': FundingListenerConfig,
        'listener': FundingListener
    }
}

channel_managers = {
    'SINK': {
        'config': SinkNodeConfig,
        'state': SinkNodeState,
        'operator': SinkNodeManager
    },
    'SOURCE': {
        'config': SourceNodeConfig,
        'state': SourceNodeState,
        'operator': SourceNodeManager
    }
}


CREDS = Config('creds.config').config
LISTEN_CONFIG = Config('listen.config').config
CHANNELS_CONFIG = Config('channels.config').config

tg_creds = TelegramCreds(CREDS['TELEGRAM']['api_token'], CREDS['TELEGRAM']['chat_id'])

PLAY_LOG = Logger("logs/play.log", tg_creds)
LISTEN_LOG = Logger('logs/listen.log', tg_creds)
