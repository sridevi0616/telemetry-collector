from fastapi import FastAPI
import pyarrow as pa
from datetime import datetime
import threading
import time
import random
from pathlib import Path

# ConfigMap mount path
CONFIG_PATH = "/config"

# default values
telemetry_interval = 5
max_rows = 1000

app = FastAPI(
    title="APACHE ARROW Telemetry Collector"
)

telemetry_rows = []

lock = threading.Lock()


def load_config():

    global telemetry_interval
    global max_rows
    global telemetry_rows

    try:

        new_interval = int(
            Path(
                f"{CONFIG_PATH}/TELEMETRY_INTERVAL"
            ).read_text().strip()
        )

        new_max_rows = int(
            Path(
                f"{CONFIG_PATH}/MAX_ROWS"
            ).read_text().strip()
        )

        telemetry_interval = new_interval
        max_rows = new_max_rows

        with lock:

            if len(telemetry_rows) > max_rows:

                telemetry_rows = telemetry_rows[-max_rows:]

        print(
            f"CONFIG RELOADED "
            f"interval={telemetry_interval} "
            f"max_rows={max_rows} "
            f"current_rows={len(telemetry_rows)}"
        )

    except Exception as e:

        print(f"config reload error: {e}")
def config_reloader():

    while True:

        load_config()

        time.sleep(10)


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
            "cpu": random.randint(20, 95),
            "memory": random.randint(30, 90)
        }

        with lock:

            telemetry_rows.append(row)

            if len(telemetry_rows) > max_rows:
                telemetry_rows.pop(0)

        time.sleep(telemetry_interval)


def build_arrow_table():

    with lock:

        if not telemetry_rows:

            return pa.table({
                "timestamp": [],
                "node": [],
                "cpu": [],
                "memory": []
            })

        return pa.Table.from_pylist(
            telemetry_rows
        )


@app.on_event("startup")
def startup():

    load_config()

    threading.Thread(
        target=generate_telemetry,
        daemon=True
    ).start()

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
        "schema": str(table.schema),
        "memory_bytes": table.nbytes
    }


@app.get("/data")
def data():

    table = build_arrow_table()

    return table.to_pylist()
