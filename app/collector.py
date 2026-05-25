from fastapi import FastAPI
import pyarrow as pa
from datetime import datetime
import threading
import time
import random

app = FastAPI(title="Arrow Telemetry Collector")

MAX_ROWS = 1000

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

            if len(telemetry_rows) > MAX_ROWS:
                telemetry_rows.pop(0)

        time.sleep(5)

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

    thread.start()

@app.get("/health")
def health():

    return {
        "status": "UP"
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
