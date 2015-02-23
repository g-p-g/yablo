from copy import deepcopy

import jsonschema

from .error import YabloException


# JSON returned from the http-front server in case of errors.
FRONT_ERROR = {
    "description": "Request not processed due to user error",
    "type": "object",
    "properties": {
        "msg": {"type": "string"},
        "code": {
            "type": "integer",
            "minimum": 400
        }
    },
    "required": ["msg", "code"],
    "additionalProperties": False
}

# Base schema for queries.
_QUERY = {
    "type": "object",
    "properties": None,
    "required": ["query", "data"],
    "additionalProperties": False
}

# No category found for the query entered.
QUERY_NORESULT = _QUERY.copy()
QUERY_NORESULT['description'] = "Query did not match any expected format"
QUERY_NORESULT['properties'] = {
    "query": {"type": "null"},
    "data": {"type": "null"}
}

# No results found for the query entered.
QUERY_EMPTYRESULT = _QUERY.copy()
QUERY_EMPTYRESULT['description'] = "No results found"
QUERY_EMPTYRESULT['properties'] = {
    "query": {
        "type": "array",
        "items": {"type": "string"},
        "minItems": 1,
        "uniqueItems": True
    },
    "data": {
        "type": "null"
    }
}

# Found a transaction for the query entered.
_TRANSACTION_OBJ = {
    "title": "Transaction",
    "type": "object",
    "properties": {
        "blockhash": {"type": "string"},
        "blocktime": {"type": "integer"},
        "locktime": {"type": "integer"},
        "time": {"type": "integer"},
        "txid": {"type": "string"},
        "version": {"type": "integer"},
        "vin": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "integer"},
                    "txid": {"type": "string"},
                    "vout": {
                        "type": "integer",
                        "minimum": 0
                    }
                },
                "required": ["sequence"],
                "additionalProperties": False
            },
            "minItems": 1
        },  # end vin
        "vout": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "minimum": 0
                    },
                    "scriptPubKey": {
                        "type": "object",
                        "properties": {
                            "addresses": {
                                "type": "array",
                                "items": {"type": "string"},
                                "minItems": 1
                            },
                            "reqSigs": {"type": "integer"},
                            "type": {"type": "string"}
                        },
                        "required": ["type"],
                        "additionalProperties": False
                    },  # end scriptPubKey
                    "value": {
                        # "value" is a number in queries, but
                        # always an integer in notifications.
                        "type": "number"
                    }
                },
                "required": ["n", "scriptPubKey", "value"],
                "additionalProperties": False
            },
            "minItems": 1
        }  # end vout
    },  # end properties
    "required": ["blockhash", "blocktime", "locktime", "time", "txid",
                 "version", "vin", "vout"],
    "additionalProperties": False
}  # end transaction object

QUERY_TRANSACTION = deepcopy(QUERY_EMPTYRESULT)
QUERY_TRANSACTION['description'] = "A Transaction returned from a query"
QUERY_TRANSACTION['properties']['data'] = _TRANSACTION_OBJ

# Found a block for the query entered.
QUERY_BLOCK = deepcopy(QUERY_EMPTYRESULT)
QUERY_BLOCK['description'] = "A Block returned from a query"
QUERY_BLOCK['properties']['data'] = {
    "title": "Block",
    "type": "object",
    "properties": {
        "bits": {"type": "string"},
        "difficulty": {"type": "number"},
        "hash": {"type": "string"},
        "merkleroot": {"type": "string"},
        "nextblockhash": {"type": "string"},
        "nonce": {"type": "integer"},
        "previousblockhash": {"type": "string"},
        "size": {"type": "integer"},
        "version": {"type": "integer"},
        "time": {"type": "integer"},
        "height": {
            "type": "integer",
            "minimum": 0
        },
        "rawtx": {
            "type": "array",
            "items": _TRANSACTION_OBJ
        }
    },
    "required": ["bits", "difficulty", "hash", "height", "merkleroot",
                 "nextblockhash", "nonce", "previousblockhash",
                 "rawtx", "size", "version", "time"],
    "additionalProperties": False
}  # end block object

# Query for an address (currently unsupported).
QUERY_ADDRESS = deepcopy(QUERY_EMPTYRESULT)
QUERY_ADDRESS['description'] = ("An address returned from a query, "
                                "currently not supported")
QUERY_ADDRESS['properties']['data'] = {
    "title": "Address",
    "type": "object",
    "properties": {
        "note": {"type": "string"},
        "address": {"type": "string"}
    },
    "required": ["address"],
    "additionalProperties": False
}

# JSON returned after a call to /watch/cancel
WATCH_CANCEL = {
    "description": "Result after asking to cancel subscription to an event",
    "type": "object",
    "properties": {
        "success": {"type": "boolean"}
    },
    "required": ["success"],
    "additionalProperties": False
}

# JSON returned after a successfull call to /watch/<...>
WATCH_BLOCK = {
    "description": ('Result after subscribing to the "newblock" '
                    'or "discblock" events'),
    "type": "object",
    "properties": {
        "callback": {"type": "string"},
        "id": {"type": "string"},
        "success": {"type": "boolean"},
        "type": {"type": "string"}
    },
    "required": ["callback", "id", "success", "type"],
    "additionalProperties": False
}

WATCH_ADDRESS = deepcopy(WATCH_BLOCK)
WATCH_ADDRESS['description'] = 'Result after subscribing to an "address" event'
WATCH_ADDRESS['properties']['address'] = {"type": "string"}
WATCH_ADDRESS['required'].append('address')

# Base schema for events.
_EVENT = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "origin_time": {"type": "integer"},
        "type": {"type": "string"},
        "data": None
    },
    "required": ["id", "origin_time", "type", "data"],
    "additionalProperties": False
}

# JSON for "address" event.
_ADDRESS_ENTRIES = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "value": {"type": "integer"},
            "address": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1
            }
        },
        "required": ["address", "value"],
        "additionalProperties": False
    },
    "minItems": 1
}

EVENT_ADDRESS = deepcopy(_EVENT)
EVENT_ADDRESS['required'].append('address')
EVENT_ADDRESS['description'] = 'Callback for an "address" event'
EVENT_ADDRESS['properties']['address'] = {"type": "string"}
EVENT_ADDRESS['properties']['data'] = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "txid": {"type": "string"},
        "block_hash": {"type": ["string", "null"]},
        "confirmations": {
            "type": "integer",
            "minimum": 0
        },
        "input": _ADDRESS_ENTRIES,
        "output": _ADDRESS_ENTRIES
    },
    "required": ["event_id", "txid", "block_hash", "confirmations",
                 "input", "output"],
    "additionalProperties": False
}

# JSON for "newblock" event.
EVENT_NEWBLOCK = _EVENT.copy()
EVENT_NEWBLOCK['description'] = 'Callback for a "newblock" event'
EVENT_NEWBLOCK['properties']['data'] = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "block_hash": {"type": "string"},
        "difficulty": {"type": "number"},
        "previousblockhash": {"type": "string"},
        "time": {"type": "integer"},
        "height": {
            "type": "integer",
            "minimum": 0
        },
        "tx": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
        }
    },
    "required": ["block_hash", "difficulty", "event_id",
                 "height", "previousblockhash", "time", "tx"],
    "additionalProperties": False
}

# JSON for "blockdisconnected" event.
EVENT_DISCBLOCK = _EVENT.copy()
EVENT_DISCBLOCK['description'] = 'Callback for a "discblock" event'
EVENT_DISCBLOCK['properties']['data'] = {
    "type": "object",
    "properties": {
        "event_id": {"type": "string"},
        "block_hash": {"type": "string"},
        "height": {
            "type": "integer",
            "minimum": 0
        }
    },
    "required": ["block_hash", "event_id", "height"],
    "additionalProperties": False
}


def validate(obj, schema=None):
    """
    Validate the JSON in obj according to the schema specified.
    If schema is None, a guess is made and if none is found an
    exception is raised.
    """
    if schema is None:
        if 'code' in obj:
            schema = FRONT_ERROR
        elif 'query' in obj and obj['query'] is None:
            schema = QUERY_NORESULT
        elif 'origin_time' in obj and 'type' in obj:
            if obj['type'] == 'address':
                schema = EVENT_ADDRESS
            elif obj['type'] == 'newblock':
                schema = EVENT_NEWBLOCK
            elif obj['type'] == 'discblock':
                schema = EVENT_DISCBLOCK
        elif 'data' in obj:
            if obj['data'] is None:
                schema = QUERY_EMPTYRESULT
            elif 'merkleroot' in obj['data']:
                schema = QUERY_BLOCK
            elif 'txid' in obj['data']:
                schema = QUERY_TRANSACTION
            elif 'address' in obj['data']:
                schema = QUERY_ADDRESS
        elif 'success' in obj and len(obj) == 1:
            schema = WATCH_CANCEL

        if schema is None:
            raise YabloException("no schema known")

    return jsonschema.validate(obj, schema)
