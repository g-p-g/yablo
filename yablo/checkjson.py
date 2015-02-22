from copy import deepcopy

import jsonschema

from .error import YabloException


# JSON returned from the http-front server in case of errors.
FRONT_ERROR = {
    "type": "object",
    "properties": {
        "msg": {
            "type": "string"
        },
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
QUERY_NORESULT['properties'] = {
    "query": {
        "type": "null"
    },
    "data": {
        "type": "null"
    }
}

# No results found for the query entered.
QUERY_EMPTYRESULT = _QUERY.copy()
QUERY_EMPTYRESULT['properties'] = {
    "query": {
        "type": "array",
        "items": {
            "type": "string"
        },
        "minItems": 1,
        "uniqueItems": True
    },
    "data": {
        "type": "null"
    }
}

# Found a transaction for the query entered.
TRANSACTION_OBJ = {
    "title": "Transaction",
    "type": "object",
    "properties": {
        "blockhash": {
            "type": "string"
        },
        "blocktime": {
            "type": "integer"
        },
        "locktime": {
            "type": "integer"
        },
        "time": {
            "type": "integer"
        },
        "txid": {
            "type": "string"
        },
        "version": {
            "type": "integer"
        },
        "vin": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sequence": {
                        "type": "integer"
                    },
                    "txid": {
                        "type": "string"
                    },
                    "vout": {
                        "type": "integer",
                        "minimum": 0
                    }
                },
                "required": ["sequence"]
            }
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
                                "items": {
                                    "type": "string"
                                },
                                "minItems": 1
                            },
                            "reqSigs": {
                                "type": "integer"
                            },
                            "type": {
                                "type": "string"
                            }
                        },
                        "required": ["type"]
                    },  # end scriptPubKey
                    "value": {
                        # "value" is a number in queries, but
                        # always an integer in notifications.
                        "type": "number"
                    }
                },
                "required": ["n", "scriptPubKey", "value"]
            }
        }  # end vout
    },  # end properties
    "required": ["blockhash", "blocktime", "locktime", "time", "txid",
                 "version", "vin", "vout"],
    "additionalProperties": False
}  # end transaction object

QUERY_TRANSACTION = deepcopy(QUERY_EMPTYRESULT)
QUERY_TRANSACTION['properties']['data'] = TRANSACTION_OBJ

# Found a block for the query entered.
QUERY_BLOCK = deepcopy(QUERY_EMPTYRESULT)
QUERY_BLOCK['properties']['data'] = {
    "title": "Block",
    "type": "object",
    "properties": {
        "bits": {
            "type": "string"
        },
        "difficulty": {
            "type": "number"
        },
        "hash": {
            "type": "string"
        },
        "height": {
            "type": "integer",
            "minimum": 0
        },
        "merkleroot": {
            "type": "string"
        },
        "nextblockhash": {
            "type": "string"
        },
        "nonce": {
            "type": "integer"
        },
        "previousblockhash": {
            "type": "string"
        },
        "rawtx": {
            "type": "array",
            "items": TRANSACTION_OBJ
        },
        "size": {
            "type": "integer"
        },
        "version": {
            "type": "integer",
        },
        "time": {
            "type": "integer"
        }
    },
    "required": ["bits", "difficulty", "hash", "height", "merkleroot",
                 "nextblockhash", "nonce", "previousblockhash",
                 "rawtx", "size", "version", "time"],
    "additionalProperties": False
}  # end block object

# Query for an address (currently unsupported).
QUERY_ADDRESS = deepcopy(QUERY_EMPTYRESULT)
QUERY_ADDRESS['properties']['data'] = {
    "title": "Address",
    "type": "object",
    "properties": {
        "note": {
            "type": "string"
        },
        "address": {
            "type": "string"
        }
    },
    "required": ["address"],
    "additionalProperties": False
}

# JSON returned after a call to /watch/cancel
WATCH_CANCEL = {
    "type": "object",
    "properties": {
        "success": {
            "type": "boolean"
        }
    },
    "required": ["success"],
    "additionalProperties": False
}

# JSON returned after a successfull call to /watch/<...>
WATCH_BLOCK = {
    "type": "object",
    "properties": {
        "callback": {
            "type": "string"
        },
        "id": {
            "type": "string"
        },
        "success": {
            "type": "boolean"
        },
        "type": {
            "type": "string"
        }
    },
    "required": ["callback", "id", "success", "type"],
    "additionalProperties": False
}

WATCH_ADDRESS = deepcopy(WATCH_BLOCK)
WATCH_ADDRESS['properties']['address'] = {"type": "string"}
WATCH_ADDRESS['required'].append('address')


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
