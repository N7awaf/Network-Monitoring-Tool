import subprocess
import re
import time
from datetime import datetime


def ping_device(ip):
    result = subprocess.run(
        ["ping", "-n", "1", ip],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return False, None

    match = re.search(r"time[=<](\d+)ms", result.stdout)

    if match:
        latency = int(match.group(1))
        return True, latency

    return True, None


def write_log(name, ip, status, latency=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if latency is not None:
        message = (
            f"{timestamp} | {name} | {ip} | "
            f"{status} | {latency}ms\n"
        )
    else:
        message = (
            f"{timestamp} | {name} | {ip} | "
            f"{status}\n"
        )

    with open("logs/network_monitor.log", "a") as log_file:
        log_file.write(message)


def load_devices():
    devices = []

    with open("config/devices.txt", "r") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            parts = line.split(",")

            if len(parts) != 2:
                print(f"Invalid device entry: {line}")
                continue

            name = parts[0].strip()
            ip = parts[1].strip()

            devices.append({
                "name": name,
                "ip": ip
            })

    return devices


# Store overall monitoring results
device_stats = {}

devices = load_devices()

for cycle in range(1, 6):

    print(f"\n--- Monitoring Cycle {cycle} ---")

    online_count = 0
    offline_count = 0
    cycle_latencies = []

    for device in devices:

        name = device["name"]
        ip = device["ip"]

        if ip not in device_stats:
            device_stats[ip] = {
                "name": name,
                "checks": 0,
                "online": 0,
                "offline": 0,
                "latencies": []
            }

        online, latency = ping_device(ip)

        device_stats[ip]["checks"] += 1

        if online:

            online_count += 1
            device_stats[ip]["online"] += 1

            if latency is not None:

                cycle_latencies.append(latency)
                device_stats[ip]["latencies"].append(latency)

                print(
                    f"{name} ({ip}) -> "
                    f"ONLINE | Latency: {latency}ms"
                )

                write_log(
                    name,
                    ip,
                    "ONLINE",
                    latency
                )

            else:

                print(
                    f"{name} ({ip}) -> "
                    f"ONLINE | Latency: Unknown"
                )

                write_log(
                    name,
                    ip,
                    "ONLINE"
                )

        else:

            offline_count += 1
            device_stats[ip]["offline"] += 1

            print(
                f"{name} ({ip}) -> OFFLINE"
            )

            write_log(
                name,
                ip,
                "OFFLINE"
            )

    # Cycle summary

    total_devices = online_count + offline_count

    if cycle_latencies:
        average_latency = round(
            sum(cycle_latencies) / len(cycle_latencies),
            2
        )
    else:
        average_latency = 0

    print("\nCycle Summary")
    print("-------------------------")
    print(f"Total Devices  : {total_devices}")
    print(f"Online         : {online_count}")
    print(f"Offline        : {offline_count}")
    print(f"Average Latency: {average_latency}ms")

    if cycle < 5:
        print("\nWaiting 10 seconds...")
        time.sleep(10)


# Final report

print("\n")
print("========== FINAL REPORT ==========")

total_checks = 0
total_online = 0
total_offline = 0

for ip, stats in device_stats.items():

    total_checks += stats["checks"]
    total_online += stats["online"]
    total_offline += stats["offline"]

    availability = (
        stats["online"] /
        stats["checks"] *
        100
    )

    if stats["latencies"]:
        average_latency = round(
            sum(stats["latencies"]) /
            len(stats["latencies"]),
            2
        )
    else:
        average_latency = 0

    print(f"\nDevice: {stats['name']}")
    print(f"IP Address   : {ip}")
    print(f"Checks       : {stats['checks']}")
    print(f"Online       : {stats['online']}")
    print(f"Offline      : {stats['offline']}")
    print(f"Availability : {availability:.2f}%")
    print(f"Avg Latency  : {average_latency}ms")


print("\n----------------------------------")
print(f"Total Checks : {total_checks}")
print(f"Total Online : {total_online}")
print(f"Total Offline: {total_offline}")
print("==================================")
