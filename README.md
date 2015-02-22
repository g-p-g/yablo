# yablo

## Installation

Prerequisites: python 2.7; [redis](http://redis.io/) server running; [btcd](https://github.com/btcsuite/btcd) operating on testnet or mainnet

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

Notifications are sent as POST requests to the registered webhooks. To register a webhook, a HTTP requests needs to be sent to the front server, which redirects the request to the watch server, which then records the subscription.


## Sample callback

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
