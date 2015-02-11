# yablo

Prerequisites: redis server and btcd synced with testnet or mainnet

For yablo itself:

```
pip install -r requirements.txt -U
python setup_yablo.py
supervisord
```

You may want to adjust `supervisord.conf` and `yablo.cfg` for your environment.
