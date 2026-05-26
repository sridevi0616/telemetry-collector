from fastapi import FastAPI
import pyarrow as pa
from datetime import datetime
import threading
import time
import random
from pathlib import Path
import os

CONFIG_PATH="/config"

telemetry_interval = 5
max_rows = 1000

app = FastAPI(title="APACHE ARROW Telemetry Collector")

max_rows = 1000

telemetry_rows = []

lock = threading.Lock()

def generate_telemetry():

    global telemetry_rows

    nodes = [
        "worker-1",
        "worker-2",
        "worker-3"
    ]

    while True:

        row = {
            "timestamp": datetime.utcnow().isoformat(),
            "node": random.choice(nodes),
            "cpu": random.randint(20,95),
            "memory": random.randint(30,90)
        }

        with lock:

            telemetry_rows.append(row)

            if len(telemetry_rows) > max_rows:
                telemetry_rows.pop(0)

        time.sleep(telemetry_interval)

def load_config():

    global telemetry_interval
    global max_rows

    try:

        telemetry_interval = int(
            Path(
                f"{CONFIG_PATH}/TELEMETRY_INTERVAL"
            ).read_text().strip()
        )

        max_rows = int(
            Path(
                f"{CONFIG_PATH}/max_rows"
            ).read_text().strip()
        )

    except Exception as e:

        print(f"config reload error {e}")

def config_reloader():

    while True:

        load_config()

        time.sleep(10)
        
def build_arrow_table():

    with lock:

        if not telemetry_rows:
            return pa.table({
                "timestamp": [],
                "node": [],
                "cpu": [],
                "memory": []
            })

        return pa.Table.from_pylist(telemetry_rows)

@app.on_event("startup")
def startup():

    thread = threading.Thread(
        target=generate_telemetry,
        daemon=True
    )

     threading.Thread(
        target=config_reloader,
        daemon=True
    ).start()

@app.get("/health")
def health():

    return {
        "status": "UP"
    }
@app.get("/config")
def config():

    return {
        "telemetry_interval": telemetry_interval,
        "max_rows": max_rows
    }

@app.get("/stats")
def stats():

    table = build_arrow_table()

    return {
        "rows": table.num_rows,
        "columns": table.num_columns,
        "schema": str(table.schema)
    }

@app.get("/data")
def data():

    table = build_arrow_table()

    return table.to_pylist()
