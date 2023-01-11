from threading import Thread
from config import LISTEN_CONFIG, CREDS, LISTEN_LOG, listen_map
from lnd import Lnd, LndCreds


def main():
    LISTEN_LOG.info("Running...")

    lnd_creds = LndCreds(grpc_host=CREDS['LND']['grpc_host'], tls_cert_path=CREDS['LND']['tls_cert_path'], macaroon_path=CREDS['LND']['tls_cert_path'])
    node = Lnd(lnd_creds, LISTEN_LOG)

    thread_pool = []

    for key in LISTEN_CONFIG:
        if key != 'DEFAULT':
            if LISTEN_CONFIG[key]['execute'] == "1":
                daemon = listen_map[key](config=LISTEN_CONFIG[key], CREDS=CREDS, node=node, log=log)
                thread_pool.append(Thread(target=daemon.mainLoop))

    for thread in thread_pool:
        thread.start()


if __name__ == "__main__":
    main()
