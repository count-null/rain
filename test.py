import unittest
from channels import ChannelState, SinkNodeConfig, SinkNodeState, SinkNodeManager, SourceNodeConfig, SourceNodeState, SourceNodeManager
from config import SwapMethod


class TestSinkChannelManager(unittest.TestCase):
    def __init__(self):
        self.test_sink_config = SinkNodeConfig(
            config={
                'pubkey': 'testpubkeyanythingworkscauseitsatest',
                'host': '127.0.0.1:9385',
                'capacity': 100_000_000,
                'num_channels': 3,
                'close_ratio': 0.05,
                'base_fee': 0,
                'fee_ppm': 1000,
                'cltv_delta': 144,
                'min_htlc_sat': 100_000,
                'mempool_fee_rec': 'fastestFee',
                'max_sat_per_vbyte': 100,
            }
        )

    def test_close_empty_channels(self):
        test_sink_state = SinkNodeState(
            channels=[
                ChannelState(
                    chan_id='test1',
                    capacity=100_000_000,
                    local_balance=2_000_000,  # empty channel
                    local_chan_reserve_sat=1_000_000,
                ),
                ChannelState(
                    chan_id='test2',
                    capacity=100_000_000,
                    local_balance=20_000_000,
                    local_chan_reserve_sat=1_000_000,
                ),
                ChannelState(
                    chan_id='test3',
                    capacity=100_000_000,
                    local_balance=20_000_000,
                    local_chan_reserve_sat=1_000_000,
                ),
            ],
            sat_per_vbyte=10,
            config=self.test_sink_config
        )
        jobs = SinkNodeManager(state=test_sink_state, node=None, log=None, mock=True).get_jobs()
        self.assertEqual(jobs, ["CLOSE_EMPTY_CHANNELS"])

    def test_open_channel(self):
        test_sink_state = SinkNodeState(
            channels=[  # not enough channels
                ChannelState(
                    chan_id='test3',
                    capacity=100_000_000,
                    local_balance=20_000_000,
                    local_chan_reserve_sat=1_000_000,
                ),
            ],
            sat_per_vbyte=10,
            config=self.test_sink_config
        )
        jobs = SinkNodeManager(state=test_sink_state, node=None, log=None, mock=True).get_jobs()
        self.assertEqual(jobs, ["OPEN_CHANNEL"])


class TestSourceChannelManager(unittest.TestCase):
    def __init__(self):
        self.test_source_config = SourceNodeConfig(
            config={
                'pubkey': 'testpubkeyanythingworkscauseitsatest',
                'host': '127.0.0.1:9385',
                'capacity': 100_000_000,
                'num_channels': 1,
                'base_fee': 0,
                'fee_ppm': 1000,
                'cltv_delta': 144,
                'min_htlc_sat': 100_000,
                'swap_method': 'kraken',
                'loop_out_amount': 10_000_000,
                'loop_out_backoff': 0.93,
                'max_account_balance': 50_000_000,
                'mempool_fee_rec': 'fastestFee',
                'max_sat_per_vbyte': 100,
            }
        )

    def test_open_channel(self):
        test_source_state = SourceNodeState(
            channels=[],  # not enough sources
            sat_per_vbyte=10,
            account_balance=0,
            config=self.test_source_config,
            swap_method=SwapMethod()
        )
        jobs = SourceNodeManager(state=test_source_state, node=None, log=None, mock=True).get_jobs()
        self.assertEqual(jobs, ['OPEN_CHANNEL'])

    def test_drain_channels(self):
        test_source_state = SourceNodeState(
            channels=[
                ChannelState(
                    chan_id='test3',
                    capacity=100_000_000,
                    local_balance=20_000_000,  # balance > loop_out_amount
                    local_chan_reserve_sat=1_000_000,
                ),
            ],
            sat_per_vbyte=10,
            account_balance=0,
            config=self.test_source_config,
            swap_method=SwapMethod()
        )
        jobs = SourceNodeManager(state=test_source_state, node=None, log=None, mock=True).get_jobs()
        self.assertEqual(jobs, ['DRAIN_CHANNELS'])

    def test_account_send_onchain(self):
        test_source_state = SourceNodeState(
            channels=[
                ChannelState(
                    chan_id='test3',
                    capacity=100_000_000,
                    local_balance=8_000_000,
                    local_chan_reserve_sat=1_000_000,
                ),
            ],
            sat_per_vbyte=10,
            account_balance=50_100_000,  # balance > max_account_balance
            config=self.test_source_config,
            swap_method=SwapMethod()
        )
        jobs = SourceNodeManager(state=test_source_state, node=None, log=None, mock=True).get_jobs()       
        self.assertEqual(jobs, ['ACCOUNT_SEND_ONCHAIN'])


if __name__ == '__main__':
    unittest.main()
