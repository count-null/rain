import time
import csv
import traceback
from mempool import Mempool, MempoolCreds
from notify import Logger
from lnd import Lnd


class FundingListenerConfig:
    def __init__(self, onchain_deposit: str, onchain_send: str, channel_open_broadcast: str, channel_open_confirmed: str, channel_open_active: str, channel_close_broadcast: str, channel_close_confirmed: str, ln_payment_sent: str, ln_invoice_paid: str):
        self.onchain_deposit = bool(onchain_deposit)
        self.onchain_send = bool(onchain_send)
        self.channel_open_broadcast = bool(channel_open_broadcast)
        self.channel_open_confirmed = bool(channel_open_confirmed)
        self.channel_open_active = bool(channel_open_active)
        self.channel_close_broadcast = bool(channel_close_broadcast)
        self.channel_close_confirmed = bool(channel_close_confirmed)
        self.ln_payment_sent = bool(ln_payment_sent)
        self.ln_invoice_paid = bool(ln_invoice_paid)


class FundingListener:
    """Get notificatinos when the node sends/recieves funds"""

    def __init_(self, config: FundingListenerConfig, _, node: Lnd, log: Logger):
        self.tg = log.notify_connector
        self.node = node
        self.onchain_deposit = config['onchain_deposit']
        self.onchain_send = config['onchain_send']
        self.channel_open_broadcast = config['channel_open_broadcast']
        self.channel_open_confirmed = config['channel_open_confirmed']
        self.channel_open_active = config['channel_open_active']
        self.channel_close_broadcast = config['channel_close_broadcast']
        self.channel_close_confirmed = config['channel_close_confirmed']
        self.ln_payment_sent = config['ln_payment_sent']
        self.ln_invoice_paid = config['ln_invoice_paid']

    def mainLoop(self):
        while True:
            time.sleep(30)


class MempoolListenerConfig:
    def __init__(self, on_mempool_empty: str, mempool_empty_mb: str, on_mempool_change: str, mempool_delta_mb: str, on_channel_confirmed: str):
        self.on_mempool_empty = bool(on_mempool_empty)
        self.mempool_empty_mb = int(mempool_empty_mb)
        self.on_mempool_change = bool(on_mempool_change)
        self.mempool_delta_mb = int(mempool_delta_mb)
        self.on_channel_confirmed = bool(on_channel_confirmed) 


class MempoolListener:
    """
    Get notifications about mempool activity
    """

    def __init__(self, config: MempoolListenerConfig, CREDS: dict, node: Lnd, log: Logger):
        self.tg = log.notify_connector
        self.node = node
        self.config = config
        self.mempool = Mempool(MempoolCreds(api_url=CREDS['MEMPOOL']['api_url']), log)
        self.bytes = self.get_bytes()
        self.last_notify_bytes = None
        self.pending_channels = self.get_pending_channels()

    def get_bytes(self):
        bytes = self.mempool.get_mempool_bytes()
        self.last_notify_bytes = bytes if not self.last_notify_bytes else self.last_notify_bytes
        return bytes

    def get_pending_channels(self):
        pending_channels = self.node.get_pending_channel_open_tx_ids()
        self.pending_channels = pending_channels
        return pending_channels

    def mainLoop(self):
        MB_BYTES = 1_000_000
        while True:
            # get latest bytes
            self.get_bytes()
            mb = round(bytes/MB_BYTES, 2)
            if self.config.on_mempool_empty:
                if mb < self.config.mempool_empty_mb and not self.last_notify_bytes/MB_BYTES < self.empty_mb:
                    self.last_notify_bytes = bytes
                    self.tg.send_message(f"🫗  Mempool is good as empty! Currently {mb}MB")
            elif self.config.on_mempool_change:
                if mb > ((self.last_notify_bytes/MB_BYTES) + self.config.mempool_delta_mb):
                    self.last_notify_bytes = bytes
                    self.tg.send_message(f"⬆️  Mempool growing! Currently {mb}MB")
                elif mb < ((self.last_notify_bytes/MB_BYTES) - self.config.mempool_delta_mb):
                    self.last_notify_bytes = bytes
                    self.tg.send_message(f"⬇️  Mempool shrinking! Currently {mb}MB")
            elif self.config.on_channel_confirmed:
                for channel in self.pending_channels:
                    tx_status = self.mempool.check_tx(channel.chanel_point.split(":")[0])
                    if tx_status["confirmed"]:
                        conf_block_height = int(tx_status["block_height"])
                        tip = int(self.mempool.get_tip_height())
                        diff = tip - conf_block_height + 1
                        if diff == 0:
                            self.tg.send_message(f"✅ Channel confirmed...")
                        elif diff == 6:
                            self.tg.send_message(f"✅ Channel active...")


class HtlcStreamLoggerConfig:
    def __init__(self, csv_file: str, log_to_console: bool, notify_events: str):
        self.csv_file = csv_file
        self.log_to_console = log_to_console
        self.notify_events = notify_events.split(' ')


class HtlcStreamLogger:
    """
    Monitor and store HTLCs as they sream across your node. 
        Optional notify telegram on forwards, sends, etc.
    """
    def __init__(self, config: HtlcStreamLoggerConfig, _, node: Lnd, log: Logger):
        self.log = log
        self.node = node
        self.config = config
        self.mychannels = {}
        self.lastchannelfetchtime = 0
        self.chandatatimeout = 15
        self.forward_event_cache = {}

    def getChanInfo(self, chanid):
        """
        Fetches channel data from LND
        Uses a cache that times out after `chandatatimeout` seconds
        Also queries closed channels if `chanid` is not in open channels
        """
        uptodate = (time.time() - self.lastchannelfetchtime < self.chandatatimeout)

        if uptodate and chanid in self.mychannels:
            return self.mychannels[chanid]

        for chan in self.node.get_channels():
            self.mychannels[chan.chan_id] = chan

        self.lastchannelfetchtime = time.time()

        if chanid in self.mychannels:
            return self.mychannels[chanid]

        for chan in self.node.get_closed_channels():
            self.mychannels[chan.chan_id] = chan

        if chanid in self.mychannels:
            return self.mychannels[chanid]

        print('ERROR: Unknown chanid', chanid)
        return None

    def getAlias4ChanID(self, chanid):
        chan = self.getChanInfo(chanid)
        if chan is None:
            return chanid
        alias = self.node.get_node_alias(chan.remote_pubkey)
        return alias

    def getFailureAttribute(self, einfo, attr):
        i = getattr(einfo, attr)
        x = einfo.DESCRIPTOR.fields_by_name[attr]

        return x.enum_type.values_by_number[i].name

    def popamountsfromcache(self, key):
        amount = self.forward_event_cache[key]['amt']
        fee = self.forward_event_cache[key]['fee']
        del self.forward_event_cache[key]
        return amount, fee

    def subscribeEventsPersistent(self):
        failures = 0

        while True:
            events = self.node.subscribe_htlc_events()
            try:
                _ = self.node.get_info() # test connection
                print('Connected to LND. Waiting for first event...')
                for e in events:
                    yield e
            except StopIteration:
                raise
            except Exception as e:
                details = 'no details'
                try:
                    details = e.details()
                except:
                    pass

                print('Error:', details)
                unavailable = ('Connection refused' in details)
                unready = ('not yet ready' in details or 'wallet locked' in details)
                terminated = (details == "htlc event subscription terminated")

                if any((unavailable, unready, terminated)):
                    failures += 1
                    timeout = 4**failures
                    print(f'Could not connect to lnd, retrying in {timeout}s')
                    time.sleep(timeout)
                    continue

                print('Unhandled exception:', repr(e))
                raise e

    def mainLoop(self):
        events = self.subscribeEventsPersistent()
        print('Now listening for HTLCs')

        for i, event in enumerate(events):
            try:
                inchanid = event.incoming_channel_id
                outchanid = event.outgoing_channel_id

                outcome = event.ListFields()[-1][0].name
                eventinfo = getattr(event, outcome)
                eventtype = event.EventType.keys()[event.event_type]
                timetext = time.ctime(event.timestamp_ns/1e9)

                in_htlc_id = event.incoming_htlc_id
                out_htlc_id = event.outgoing_htlc_id

                inalias = outalias = 'N/A'
                inrbal = incap = outlbal = outcap = '-'
                if inchanid:
                    inalias = self.getAlias4ChanID(inchanid)
                    inchan = self.getChanInfo(inchanid)
                    incap = getattr(inchan, 'capacity', 'UNKNOWN')
                    inrbal = getattr(inchan, 'remote_balance', 'UNKNOWN')

                if outchanid:
                    outalias = self.getAlias4ChanID(outchanid)
                    outchan = self.getChanInfo(outchanid)
                    # If channel is unknown (closed?) cannot guarantee these values exist
                    outcap = getattr(outchan, 'capacity', 'UNKNOWN')
                    outlbal = getattr(outchan, 'local_balance', 'UNKNOWN')

                # Extract forward amount data, if available
                amount = fee = '-'
                if hasattr(eventinfo, 'info'):
                    if eventinfo.info.outgoing_amt_msat > 0:
                        amt_msat = eventinfo.info.outgoing_amt_msat
                        amount = amt_msat/1000
                        fee = (eventinfo.info.incoming_amt_msat - amt_msat)/1000

                    elif eventinfo.info.incoming_amt_msat > 0:
                        amt_msat = eventinfo.info.incoming_amt_msat
                        amount = amt_msat/1000

                # Add a note to quickly point out common scenarios
                note = ''
                fwdcachekey = (in_htlc_id, out_htlc_id, inchanid, outchanid)
                if outcome == 'forward_event':
                    note = '💸 HTLC in flight.'
                    self.forward_event_cache[fwdcachekey] = {'amt':amount, 'fee':fee}

                elif outcome == 'forward_fail_event':
                    note = '❌ Downstream fwding failure.'
                    if fwdcachekey in self.forward_event_cache:
                        # This data is only found in forward_event, need to fetch it from cache
                        amount, fee = self.popamountsfromcache(fwdcachekey)

                elif outcome == 'link_fail_event':
                    failure_string = eventinfo.failure_string
                    failure_detail = self.getFailureAttribute(eventinfo, 'failure_detail')
                    wire_failure = self.getFailureAttribute(eventinfo, 'wire_failure')

                    if eventtype == 'RECEIVE' and failure_detail == 'UNKNOWN_INVOICE':
                        note += 'Probe detected. '

                    note += f'❌ Failure(wire: {wire_failure}, detail: {failure_detail}, string: {failure_string})'

                elif outcome == 'settle_event' and eventtype == 'FORWARD':
                    note = '✅ Forward successful.'
                    if fwdcachekey in self.forward_event_cache:
                        # This data is only found in forward_event, need to fetch it from cache
                        amount, fee = self.popamountsfromcache(fwdcachekey)

                elif outcome == 'settle_event':
                    note = '✅'

                if self.config.notify_events:
                    if "forwards" in self.config.notify_events:
                        if eventtype == "FORWARD" and "successful" in note:
                            fee_ppm = "--"
                            if (isinstance(fee, float) or isinstance(fee, int)) and (isinstance(amount, float) or isinstance(amount, int)):
                                fee_ppm = round((fee/amount) * 1_000_000)
                            self.log.notify(f"✅ FORWARD {inalias} ➜ {outalias} for {fee} \[{fee_ppm}]")
                    elif "sends" in self.config.notify_events:
                        if eventtype == "SEND" and outcome == "settle_event":
                            self.log.notify(f"✅ SEND {amount} out {outalias} for {fee}")

                if self.config.log_to_console:
                    print(eventtype,
                        in_htlc_id, out_htlc_id,
                        timetext, amount,'for', fee,
                        inalias, f'{inrbal}/{incap}',
                        '➜',
                        outalias, f'{outlbal}/{outcap}',
                        # ~ inchanid, '➜', outchanid,
                        outcome,
                        # ~ eventinfo,
                        note,
                            )

                with open(self.config.csv_file, 'a', newline='') as f:
                    writer = csv.writer(f)

                    if i % 30 == 0:
                        writer.writerow(['Eventtype', 'Htlc_id_in', 'Htlc_id_out',
                                        'Timestamp', 'Amount', 'Fee',
                                        'Alias_in','Alias_out',
                                        'Balance_in','Capacity_in',
                                        'Balance_out', 'Capacity_out',
                                        'Chanid_in','Chanid_out',
                                        'Outcome', 'Details', 'Note'])

                    writer.writerow([eventtype,
                                    event.incoming_htlc_id,
                                    event.outgoing_htlc_id,
                                    timetext, amount, fee,
                                    inalias, outalias,
                                    inrbal, incap,
                                    outlbal, outcap,
                                    f"{inchanid}", f"{outchanid}",
                                    outcome, eventinfo, note])

            except Exception as e:
                print('Exception while handling event.', repr(e))
                print(event)
                traceback.print_exc()
