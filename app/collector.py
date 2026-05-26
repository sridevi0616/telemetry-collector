from fastapi import FastAPI
from datetime import datetime
import threading
import time
import random
from pathlib import Path

CONFIG_PATH = "/config"

telemetry_interval = 5
max_rows = 1000

app = FastAPI(
    title="Telemetry Collector WITHOUT Arrow"
)

telemetry_rows = []

lock = threading.Lock()


def load_config():

    global telemetry_interval
    global max_rows
    global telemetry_rows

    try:

        telemetry_interval = int(
            Path(
                f"{CONFIG_PATH}/TELEMETRY_INTERVAL"
            ).read_text().strip()
        )

        max_rows = int(
            Path(
                f"{CONFIG_PATH}/MAX_ROWS"
            ).read_text().strip()
        )

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
            "cpu": random.randint(20,95),
            "memory": random.randint(30,90)
        }

        with lock:

            telemetry_rows.append(row)

            if len(telemetry_rows) > max_rows:

                telemetry_rows.pop(0)

        time.sleep(telemetry_interval)


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
        "status":"UP"
    }


@app.get("/config")
def config():

    return {
        "telemetry_interval": telemetry_interval,
        "max_rows": max_rows
    }


@app.get("/stats")
def stats():

    with lock:

        return {
            "rows": len(telemetry_rows),
            "memory_type": "python_list"
        }


@app.get("/data")
def data():

    with lock:

        return telemetry_rows
