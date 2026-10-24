"""Copy to 01_connect_to_mysql.py and configure credentials in the environment."""

import os

from sqlalchemy import URL, create_engine

required = ("PRACTICEHUB_DB_USER", "PRACTICEHUB_DB_PASSWORD")
missing = [name for name in required if name not in os.environ]
if missing:
    raise RuntimeError("Set these environment variables: " + ", ".join(missing))

url = URL.create(
    "mysql+pymysql",
    username=os.environ["PRACTICEHUB_DB_USER"],
    password=os.environ["PRACTICEHUB_DB_PASSWORD"],
    host=os.environ.get("PRACTICEHUB_DB_HOST", "127.0.0.1"),
    port=int(os.environ.get("PRACTICEHUB_DB_PORT", "3306")),
    database=os.environ.get("PRACTICEHUB_DB_NAME", "practicehub"),
)
engine = create_engine(url, pool_pre_ping=True)
