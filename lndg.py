import requests
import json
from mempool import Mempool
from notify import Logger


class RecordList:
    """Useful class for filtering a list of dicts"""

    def __init__(self, list_of_dicts=False):
        self.list = list_of_dicts if list_of_dicts else []

    def sort(self, sort_func):
        return RecordList(sorted(self.list, key=sort_func)) if self.list else self

    def filter(self, filter_func):
        return RecordList(list(filter(filter_func, self.list))) if self.list else self

    def sum(self, key):
        return sum(r[key] for r in self.list if key in r)

    def add_key(self, new_key, new_value_func):
        if self.list:
            for d in self.list:
                d[new_key] = new_value_func(d)
            return RecordList(self.list)
        return self


class LndgCreds:
    def __init__(self, creds: dict):
        self.auth_user = creds['auth_user']
        self.auth_pass = creds['auth_pass']
        self.api_url = creds['api_url']


class Lndg:
    def __init__(self, creds: LndgCreds, mempool: Mempool, log: Logger):
        self.log = log
        self.mempool = mempool
        self.creds = creds
        self.invoices = RecordList()
        self.payments = RecordList()
        self.onchain = RecordList()
        self.closures = RecordList()
        self.forwards = RecordList()

    def lndg_request(self, url, acc):
        req = requests.get(url, auth=(self.creds.auth_user, self.creds.auth_pass))
        res = json.loads(req.content)
        acc.list.extend(res['results'])
        if res['next']:
            self.lndg_request(res['next'], acc)

    def get_url(self, endpoint):
        return f"{self.creds.api_url}{endpoint}/?format=json"

    def get_invoices(self):
        self.lndg_request(self.get_url('invoices'), self.invoices)
        return self.invoices

    def get_payments(self):
        self.lndg_request(self.get_url('payments'), self.payments)
        return self.payments

    def get_onchain(self):
        self.lndg_request(self.get_url('onchain'), self.onchain)
        self.onchain = self.onchain.sort(lambda r: r['block_height'])
        return self.onchain

    def get_closures(self):
        self.lndg_request(self.get_url('closures'), self.closures)
        return self.closures

    def get_forwards(self):
        self.lndg_request(self.get_url('forwards'), self.forwards)
        return self.forwards
