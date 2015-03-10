# yablo

## Installation

Prerequisites: python 2.7; [redis](http://redis.io/) server running; [btcd](https://github.com/btcsuite/btcd) operating on testnet or mainnet; dev packages for python, libffi, and libssl (`apt-get install python-dev libffi-dev libssl-dev`)

For yablo itself:

```
pip install -r requirements.txt -U
python setup_yablo.py
```

You may want to adjust `yablo.cfg` for your environment.


## Running

```
supervisord
```

You may want to adjust `supervisord.conf` for your environment. Using `supervisord` is optional and running everything in the same machine is good for testing and checking how it works.

The command above will start 6 processes, one for each service present in yablo. If you are not interested in answering blockchain queries, then `supervisorctl stop api-query` will stop it. If you want to temporarily disable the API, then `supervisorctl stop api:*` does that. If you need to stop processing events, `supervisorctl stop evt:evt-process`.


## Overview

yablo is a backend system for handling blockchain events. At this moment, its main purpose is to act as a notifier for new blocks and new transactions.

![yablo overview](http://i.imgur.com/KrE1POD.png)

Notifications are sent as JSON POST requests to registered webhooks, which are referred as callbacks. To register a webhook, a HTTP request needs to be sent to the front server, which redirects the request to the watch server, which then records the subscription.

Consult the [wiki](https://github.com/g-p-g/yablo/wiki) for more information. Improvements to the documentation and code are very welcome!


## Sample callbacks

The following callback was sent to a subscriber that was watching for new transactions involving the address "n3vp66W5kuMGARYxNQkWaDuMgz5mdUrU4b". In this case, a callback was fired because the transaction spent an earlier output that involved the address specified.

```json
{
  "id": "34f42ccc-94bb-40b2-baea-59aeb294cd2f",
  "type": "address",
  "address": "n3vp66W5kuMGARYxNQkWaDuMgz5mdUrU4b",
  "origin_time": 1423586417,
  "data": {
    "event_id": "aa7390f0-877a-4945-a92d-2bd4ecd55595",
    "txid": "9643a428800fbbc0....",
    "block_hash": null,
    "confirmations": 0,
    "input": [
      {
        "address": ["n3vp66W5kuMGARYxNQkWaDuMgz5mdUrU4b"],
        "value": 45999406
      }
    ],
    "output": [
      {
        "address": ["n34tHk1PMr17jR5iTaEoRacBrqfErt96qL"],
        "value": 3991893
      },
      {
        "address": ["mrDhESUMK6zVWFNmKomqkhnNmFtRZ1z2q8"],
        "value": 41997513
      }
    ]
  }
}
```

The full txid is included in callbacks, in the sample above it was shortened to fit. The same id will be used for every callback involving a specific condition for a specific subscriber, the event_id will change for each callback. Details about a specific callback are always in the data field.

### New blocks

For new block events, the following format is used in callbacks:

```json
{
  "data": {
    "block_hash": "000000001c8d59223069...",
    "difficulty": 1,
    "event_id": "50952e8b-5216-4a52-a7b7-dc35cae3781d",
    "height": 323748,
    "previousblockhash": "000000007f357d4d7cee...",
    "time": 1424629657,
    "tx": [
      "f1fa694ccf4b601738ce0261cc8741c65b0dbdf5fdb3abb5b62553d172c83ed0",
      "d1edcb76b40a111609c6034223a3a992c57e5e081048e980b72bc217560c1798",
      "a5ddb87e40bcf33d120b031ac76d763ae3ae7e021c20ebf4035fe0dc5664e186",
      "cd59e27321161789966f539d9768b1b379e72b3c9b9e20f36bce55d4e6d8b344",
      "7066eec4f1411a6b8324bf345bbd949b7649f7b5160b6f7c4a1ff263009b3adc",
      "c04ff9a2e887321326fa58a71c04afb6f3e3de2b5c80b0dd939d4cab93ecf729",
      "b1e3953b44e6ab8ef0022d51fc91bad2fd2cb0cb50df8879d74352e0c4faea45"
     ]
  },
  "id": "4ec8dd51-b72e-4690-8a93-7a9783f44084",
  "origin_time": 1424623707,
  "type": "newblock"
}
```
