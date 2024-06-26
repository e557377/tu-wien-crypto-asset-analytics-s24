import json
import pickle
from collections import Counter
from datetime import timedelta
from pathlib import Path
from timeit import default_timer as timer

import pandas as pd
import requests
# from bitcoin_explorer import BitcoinDB
from blockchain_parser.blockchain import Blockchain
# needed for any cluster connection
from couchbase.auth import PasswordAuthenticator
from couchbase.cluster import Cluster
from couchbase.options import (ClusterOptions)
from requests import RequestException

auth = PasswordAuthenticator("username", "password")
cluster = Cluster('couchbase://localhost', ClusterOptions(auth))

# Wait until the cluster is ready for use.
cluster.wait_until_ready(timedelta(seconds=5))

# get a reference to our bucket
cb = cluster.bucket("blocks")

# Get a reference to the default collection, required for older Couchbase server versions
cb_coll_default = cb.default_collection()

path_blocks = Path('/bitcoin/blocks')
# path_blocks_index = Path('/bitcoin/blocks/index')

# path_blocks = Path('/bitcoin/blocks')
path_blocks_index = Path('/bitcoin/blocks/index')

block_height_taproot: int = 709_632
block_height_current: int = 849_000

block_height_start: int = block_height_current - block_height_taproot


async def req(url, method, **kwargs):
    pass


def blockchain_parser() -> None:
    start = timer()

    blockchain = Blockchain(path_blocks)
    blocks = blockchain.get_ordered_blocks(
        str(path_blocks_index),
        start=block_height_taproot,
        end=block_height_taproot + 10_000,
        cache='./data/index-cache.pickle'
    )
    txs = []
    block_dicts = []

    # try:
    #     r = requests.get(f"https://mempool.space/api/blocks-bulk/{block_height_start}/{block_height_start + 20}")
    #     r.raise_for_status()
    # except RequestException as exc:
    #     print(f"Failed to get blocks")
    # else:
    #     block_dicts = r.json()

    for block in blocks:
        block_dicts.append({
            'hash': block.hash,
            'size': block.size,
            'height': block.height,
            'timestamp': block.header.timestamp,
            'transaction_count': block.n_transactions,
            'transactions': [],
        })
    pickle.dump(block_dicts, open('./data/blocks.pickle', 'wb'))

    stop = timer()
    print(f"Iterating blocks took: {stop - start}")

    start = timer()

    for block in block_dicts:
        try:
            r = requests.get(f"https://mempool.space/api/block/{block['hash']}/txs")
            r.raise_for_status()
        except RequestException as exc:
            print(f"Failed to get transactions for block {block['hash']}")
        else:
            block['transactions'] = r.json()
            print(block)
            break
            # cb_coll_default.insert(block['hash'], block)

    stop = timer()
    print(f"Processing transactions took: {stop - start}")


def bitcoin_explorer() -> None:
    db = BitcoinDB(str(path_blocks / '..'))

    # print(f"Current block height: {db.get_block_count()}")

    count = 0
    counter = Counter()

    start = timer()
    df = pd.DataFrame(['tx_id', 'tx_time', 'is_taproot'])

    txs = dict()

    for block in db.get_block_iter_range(start=block_height_start, stop=block_height_current, simplify=False):
        for tx in block.get('txdata'):
            id = tx['txid']
            for input in tx['inputs']:
                txs[id]['script'] = input['script_sig']
            for output in tx.get('output'):
                txs[id]['type'] = output['script_type']
                # counter[output['script_type']] += 1
        count += 1
        if count % 100 == 0:
            print(f"{count:06d}\t{timer() - start:.2f}\t{counter}")

    stop = timer()

    print(f"Count: {count}, Time: {stop - start}")


def read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=';')
    return df


def load_config(path: str = 'config.json') -> dict:
    with open(path, 'r') as f:
        return json.load(f)


if __name__ == '__main__':
    blockchain_parser()
    # bitcoin_explorer()

    # read_csv('data/unspent-575250-580000.csv.zst')
