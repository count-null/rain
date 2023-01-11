from ppadb.client import Client as AdbClient
from time import sleep
from bs4 import BeautifulSoup as bs
from config import SwapMethod
from notify import Logger


def parse_bounds(bounds_str):
    return [[int(x) for x in point.split(",")] for point in bounds_str[1:-1].split("][")]


def get_midpoint(bounds):
    return [(c1 + c2) / 2 for c1, c2 in zip(*bounds)]


class MuunCreds:
    def __init__(self, creds: dict):
        self.device_name = creds['device_name']
        self.widthdraw_address = creds['widthdraw_address']


class Muun(SwapMethod):
    def __init__(self, creds: MuunCreds, log: Logger):
        self.log = log
        self.log_msg_map = {
            "get_onchain_address": lambda addr: f"muun deposit address: {addr}",
            "send_onchain": lambda sats: f"muun initiated {sats} sat widthdrawl",
            "get_onchain_fee": lambda fee, sats: f"muun fee: {fee} sats widthdraw amount: {sats} sats",
            "get_pending_send_sats": lambda amt: f"muun send of {amt} sats",
            "get_account_balance": lambda sats: f"muun wallet balance: {sats} sats",
            "send_to_acct": lambda sats: f"sending {int(sats)} sats into muun wallet",
            "get_lightning_invoice": lambda sats, invoice: f"muun wallet request for {sats} sats invoice: {invoice}"
        }
        # connect to self.device
        client = AdbClient()
        self.address = creds.widthdraw_address
        self.device = client.device(creds.device_name)
        if self.init_wallet():
            # change the denominated amount!!
            self.change_denomination()
            self.get_backup_key()
        else:
            print("wallet initialized")

    def get_onchain_address(self):
        return

    def send_onchain(self, _, sat_per_vbyte):
        self.restart_app()
        self.tap(element_dict["send-btn"])
        self.tap(element_dict["address-input"])
        self.device.input_text(self.address)
        self.tap(element_dict["confirm-address-btn"])
        self.tap(element_dict["use-all-funds"])
        self.device.input_text(":high-voltage:")
        self.tap(element_dict["confirm-note"])
        self.tap(element_dict["network-fee"])
        self.tap(element_dict["enter-fee-manually"])
        self.device.input_text(sat_per_vbyte)
        self.tap(element_dict["confirm-fee"])
        self.tap(element_dict["send-btn"])

    def get_screen_layout(self):
        xml_dump = self.device.shell(
            """uiautomator dump /dev/tty | awk '{gsub("UI hierchary dumped to: /dev/tty", "");print}'""")
        # print(xml_dump)
        soup_obj = bs(xml_dump, features="xml")
        return soup_obj

    def tap(self, param_dict):
        screen = self.get_screen_layout()
        obj = screen.find("node", param_dict)
        bounds = parse_bounds(obj["bounds"])
        x, y = get_midpoint(bounds)
        self.device.shell(f"input tap {x} {y}")

    def delete_wallet(self):
        self.restart_app()
        balance = self.get_account_balance()
        if balance == 0:
            print("Balance is 0...")
            self.log.info("Deleting wallet...")
            self.device.shell("am force-stop io.muun.apollo")
            sleep(1)
            self.device.shell("pm clear io.muun.apollo")
            return True
        else:
            print("Balance is {}...".format(balance))
            self.log.info("ERROR: Attempted to delete wallet with non-zero balance...")
            return False

    def get_account_balance(self):
        self.log.info("Getting (potentially inaccurate) balance...")
        self.restart_app()
        sleep(2) # my phone is slow
        screen = self.get_screen_layout()
        balance_obj = screen.find("node", element_dict["balance"])
        balance = None
        try:
            balance = int(float(balance_obj["text"].replace(",", "")) * 1e6)
        except TypeError:
            self.log.notify("Err! Could not read balance from Muun. Check your android device!")
        return balance

    def get_lightning_invoice(self, sats):
        self.log.info("Getting invoice...")
        self.restart_app()

        # click receive
        self.tap(element_dict["receive-btn"])

        # click address settings
        self.tap(element_dict["address-settings"])

        # get dump to find location of add button and settings button
        loc_screen = self.get_screen_layout()

        # click lightning
        self.tap(element_dict["lightning-tab"])

        # click invoice settings
        self.tap(element_dict["invoice-settings"])

        # click location of add button
        obj = loc_screen.find("node", element_dict["add-button"])
        add_btn_bounds = parse_bounds(obj["bounds"])
        x, y = get_midpoint(add_btn_bounds)
        self.device.shell(f"input tap {x} {y}")

        # input amount
        self.device.input_text(f"{sats}")
        self.tap(element_dict["confirm-amt-btn"])
        sleep(1)

        # tap settings to close timer
        obj = loc_screen.find("node", element_dict["address-settings"])
        settings_bounds = parse_bounds(obj["bounds"])
        x, y = get_midpoint(settings_bounds)
        self.device.shell(f"input tap {x} {y}")

        # get bolt11 invoice
        screen = self.get_screen_layout()
        invoice_obj = screen.find("node", element_dict["qr-code"])
        bolt11 = invoice_obj["text"]
        return bolt11

    def close_app(self):
        self.device.shell("input keyevent KEYCODE_APP_SWITCH")
        sleep(1)
        self.device.shell("input keyevent 20")
        sleep(1)
        self.device.shell("input keyevent DEL")

    def restart_app(self):
        self.log.info("Restarting app...")
        self.device.shell("am force-stop io.muun.apollo")
        self.device.shell("monkey -p io.muun.apollo -c android.intent.category.LAUNCHER 1")
        sleep(1)

    def init_wallet(self):
        self.restart_app()
        screen = self.get_screen_layout()
        create_wallet_btn = screen.find("node", element_dict["create-wallet"])
        if create_wallet_btn:
            self.log.info("Creating wallet....")
            self.tap(element_dict["create-wallet"])
            sleep(2)
            self.log.info("Doing a trick so we don't have to make a pin...")
            self.close_app()
            sleep(1)
            self.device.shell("monkey -p io.muun.apollo -c android.intent.category.LAUNCHER 1")
            return True
        else:
            self.log.info("Wallet already created...")
            return False

    def change_denomination(self):
        self.log.info("Changing denominations...")
        self.restart_app()
        self.tap(element_dict["settings"])
        self.tap(element_dict["unit-setting"])
        self.tap(element_dict["satoshi-unit"])
        sleep(1)
        self.tap(element_dict["main-currency"])
        self.tap(element_dict["bitcoin-main"])

    def get_backup_key(self):
        self.log.info("Getting backup key...")
        self.restart_app()
        self.tap(element_dict["security-tab"])
        screen = self.get_screen_layout()
        backup_steps = screen.findAll("node", element_dict["backup-step"])
        if screen.find("node", element_dict["email-skipped"]):
            pass
        else:
            self.tap({"text": backup_steps[0]["text"], **element_dict["backup-step"]})
            self.tap(element_dict["no-email"])
            self.tap(element_dict["confirm-btn"])
        self.tap({"text": backup_steps[1]["text"], **element_dict["backup-step"]})
        self.tap(element_dict["start-backup"])

        screen = self.get_screen_layout()
        key = " ".join([x["text"] for x in screen.findAll("node", element_dict["backup-chunk"])])
        self.log.info(key)
        return key

    def get_transaction_id(self):
        self.restart_app()
        self.tap(element_dict["chevron"])
        self.tap(element_dict["payment"])
        self.device.input_swipe(400, 500, 400, 0, duration=1000)
        screen = self.get_screen_layout()
        transaction_obj = screen.findAll("node", element_dict["payment-detail"])[-1]
        transaction = transaction_obj["text"]
        return transaction


element_dict = {
    "balance": {"resource-id": "io.muun.apollo:id/balance_main_currency_amount"},
    "settings": {"resource-id": "io.muun.apollo:id/settings_fragment"},
    "delete-wallet": {"resource-id": "io.muun.apollo:id/log_out_text_view"},
    "confirm-btn": {"resource-id": "io.muun.apollo:id/positive_button"},
    "create-wallet": {"resource-id": "io.muun.apollo:id/signup_start"},
    "qr-code": {"resource-id": "io.muun.apollo:id/show_qr_content"},
    "receive-btn": {"resource-id": "io.muun.apollo:id/muun_button_button", "text": "RECEIVE"},
    "send-btn": {"resource-id": "io.muun.apollo:id/muun_button_button", "text": "SEND"},
    "lightning-tab": {"content-desc": "LIGHTNING"},
    "wallet-backup": {"resource-id": "io.muun.apollo:id/muun_text_input_edit_text"},
    "security-tab": {"resource-id": "io.muun.apollo:id/security_center_fragment", },
    "backup-step": {"resource-id": "io.muun.apollo:id/title"},
    "email-skipped": {"resource-id": "io.muun.apollo:id/tag_email_skipped", "text": "Skipped"},
    "no-email": {"content-desc": "I don't want to use my email"},
    "start-backup": {"resource-id": "io.muun.apollo:id/muun_button_button", "text": "START"},
    "backup-chunk": {"resource-id": "io.muun.apollo:id/muun_text_input_edit_text"},
    "invoice-settings": {"resource-id": "io.muun.apollo:id/invoice_settings"},
    "address-settings": {"resource-id": "io.muun.apollo:id/address_settings"},
    "add-button": {"resource-id": "io.muun.apollo:id/add_amount"},
    "confirm-amt-btn": {"resource-id": "io.muun.apollo:id/confirm_amount_button"},
    "unit-setting": {"resource-id": "io.muun.apollo:id/settings_bitcoin_unit"},
    "satoshi-unit": {"resource-id": "io.muun.apollo:id/bitcoin_unit_sat"},
    "main-currency": {"text": "Main currency", "resource-id": "io.muun.apollo:id/setting_item_label"},
    "bitcoin-main": {"text": " Bitcoin (SAT)", "resource-id": "io.muun.apollo:id/currency_item_label"},
    "address-input": {"text": "Enter a bitcoin address or invoice", "resource-id": "io.muun.apollo:id/text_input"},
    "confirm-address-btn": {"resource-id": "io.muun.apollo:id/confirm"},
    "use-all-funds": {"resource-id": "io.muun.apollo:id/use_all_funds"},
    "confirm-note": {"text": "CONFIRM NOTE", "resource-id": "io.muun.apollo:id/muun_button_button"},
    "confirm-fee": {"text": "CONFIRM FEE", "resource-id": "io.muun.apollo:id/muun_button_button"},
    "network-fee": {"text": "Network fee", "resource-id": "io.muun.apollo:id/fee_label"},
    "enter-fee-manually": {"resource-id": "io.muun.apollo:id/enter_fee_manually"},
    "chevron": {"resource-id": "io.muun.apollo:id/chevron"},
    "payment": {"text": "You paid", "resource-id": "io.muun.apollo:id/home_operations_item_title"},
    "payment-detail": {"resource-id": "io.muun.apollo:id/operation_detail_item_text_content"}
}
