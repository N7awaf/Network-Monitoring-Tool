from flask import Flask, render_template, request, redirect, url_for
import subprocess
import re
from datetime import datetime
import os


app = Flask(__name__)

DEVICES_FILE = "config/devices.txt"
LOG_FILE = "logs/network_history.log"


# =========================================================
# DEVICE MANAGEMENT
# =========================================================

def load_devices():
    devices = []

    if not os.path.exists(DEVICES_FILE):
        return devices

    with open(DEVICES_FILE, "r") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            parts = line.split(",")

            if len(parts) != 2:
                continue

            name = parts[0].strip()
            ip = parts[1].strip()

            devices.append({
                "name": name,
                "ip": ip
            })

    return devices


def save_devices(devices):

    os.makedirs("config", exist_ok=True)

    with open(DEVICES_FILE, "w") as file:

        for device in devices:
            file.write(
                f"{device['name']},{device['ip']}\n"
            )


# =========================================================
# NETWORK MONITORING
# =========================================================

def ping_device(ip):

    try:

        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", ip],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return "OFFLINE", None

        match = re.search(
            r"time[=<](\d+)ms",
            result.stdout,
            re.IGNORECASE
        )

        if match:

            latency = int(
                match.group(1)
            )

            return "ONLINE", latency

        return "ONLINE", None

    except Exception:
        return "OFFLINE", None


# =========================================================
# LOGGING
# =========================================================

def save_log(device, status, latency):

    os.makedirs("logs", exist_ok=True)

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    if latency is not None:

        line = (
            f"{timestamp} | "
            f"{device['name']} | "
            f"{device['ip']} | "
            f"{status} | "
            f"{latency}ms\n"
        )

    else:

        line = (
            f"{timestamp} | "
            f"{device['name']} | "
            f"{device['ip']} | "
            f"{status}\n"
        )

    with open(LOG_FILE, "a") as file:
        file.write(line)


# =========================================================
# HISTORY
# =========================================================

def load_history():

    history = []

    if not os.path.exists(LOG_FILE):
        return history

    with open(LOG_FILE, "r") as file:

        for line in file:

            line = line.strip()

            if not line:
                continue

            parts = [
                part.strip()
                for part in line.split("|")
            ]

            if len(parts) < 4:
                continue

            timestamp = parts[0]
            name = parts[1]
            ip = parts[2]
            status = parts[3]

            latency = None

            if len(parts) >= 5:

                latency_text = (
                    parts[4]
                    .replace("ms", "")
                    .strip()
                )

                try:
                    latency = int(latency_text)

                except ValueError:
                    latency = None

            history.append({
                "timestamp": timestamp,
                "name": name,
                "ip": ip,
                "status": status,
                "latency": latency
            })

    return history


# =========================================================
# DEVICE STATISTICS
# =========================================================

def calculate_device_statistics(
    devices,
    history
):

    statistics = {}

    for device in devices:

        name = device["name"]

        records = [
            record
            for record in history
            if record["name"] == name
        ]

        checks = len(records)

        online = sum(
            1
            for record in records
            if record["status"] == "ONLINE"
        )

        offline = sum(
            1
            for record in records
            if record["status"] == "OFFLINE"
        )

        latencies = [
            record["latency"]
            for record in records
            if record["latency"] is not None
        ]

        availability = (
            round(
                (online / checks) * 100,
                2
            )
            if checks > 0
            else 0
        )

        average_latency = (
            round(
                sum(latencies)
                / len(latencies),
                1
            )
            if latencies
            else None
        )

        statistics[name] = {

            "checks": checks,

            "online": online,

            "offline": offline,

            "availability": availability,

            "average_latency": average_latency
        }

    return statistics


# =========================================================
# CHART DATA
# =========================================================

def build_chart_data(
    devices,
    history
):

    chart_data = {}

    for device in devices:

        name = device["name"]

        records = [
            record
            for record in history
            if record["name"] == name
            and record["latency"] is not None
        ]

        # Keep graph clean
        records = records[-15:]

        chart_data[name] = {

            "labels": [
                record["timestamp"]
                for record in records
            ],

            "latencies": [
                record["latency"]
                for record in records
            ]
        }

    return chart_data


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
def dashboard():

    devices = load_devices()

    # -----------------------------------------
    # Perform current monitoring check
    # -----------------------------------------

    for device in devices:

        status, latency = ping_device(
            device["ip"]
        )

        device["status"] = status

        device["latency"] = latency

        save_log(
            device,
            status,
            latency
        )

    # -----------------------------------------
    # Historical data
    # -----------------------------------------

    history = load_history()

    device_statistics = calculate_device_statistics(
        devices,
        history
    )

    chart_data = build_chart_data(
        devices,
        history
    )

    # -----------------------------------------
    # Current statistics
    # -----------------------------------------

    total_devices = len(devices)

    online = sum(
        1
        for device in devices
        if device["status"] == "ONLINE"
    )

    offline = sum(
        1
        for device in devices
        if device["status"] == "OFFLINE"
    )

    current_latencies = [
        device["latency"]
        for device in devices
        if device["latency"] is not None
    ]

    average_latency = (
        round(
            sum(current_latencies)
            / len(current_latencies),
            1
        )
        if current_latencies
        else 0
    )

    last_check = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    statistics = {

        "total": total_devices,

        "online": online,

        "offline": offline,

        "average_latency": average_latency,

        "last_check": last_check
    }

    # -----------------------------------------
    # Alerts
    # -----------------------------------------

    alerts = []

    for device in devices:

        if device["status"] == "OFFLINE":

            alerts.append({
                "type": "danger",
                "title": "Device Offline",
                "message": (
                    f"{device['name']} "
                    f"({device['ip']}) is currently offline."
                )
            })

    # -----------------------------------------
    # Recent history
    # -----------------------------------------

    recent_history = history[-20:]

    recent_history.reverse()

    return render_template(

        "dashboard.html",

        devices=devices,

        statistics=statistics,

        device_statistics=device_statistics,

        chart_data=chart_data,

        recent_history=recent_history,

        alerts=alerts
    )


# =========================================================
# ADD DEVICE
# =========================================================

@app.route("/add-device", methods=["POST"])
def add_device():

    name = request.form.get(
        "name",
        ""
    ).strip()

    ip = request.form.get(
        "ip",
        ""
    ).strip()

    if name and ip:

        devices = load_devices()

        # Prevent duplicate IP
        existing_ips = [
            device["ip"]
            for device in devices
        ]

        if ip not in existing_ips:

            devices.append({

                "name": name,

                "ip": ip
            })

            save_devices(devices)

    return redirect(
        url_for("dashboard")
    )


# =========================================================
# DELETE DEVICE
# =========================================================

@app.route("/delete-device/<ip>", methods=["POST"])
def delete_device(ip):

    devices = load_devices()

    devices = [
        device
        for device in devices
        if device["ip"] != ip
    ]

    save_devices(devices)

    return redirect(
        url_for("dashboard")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )
