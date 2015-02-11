import os
import errno

from yablo.storage.sql_db import setup_engine, setup_storage, Base


# Paths required to store logs and pids from supervisord.
for path in ("mon/run", "mon/log"):
    try:
        os.makedirs(path)
    except OSError, err:
        if err.errno != errno.EEXIST:
            raise

engine = setup_engine()
storage = setup_storage(engine=engine)
Base.metadata.create_all(engine)
