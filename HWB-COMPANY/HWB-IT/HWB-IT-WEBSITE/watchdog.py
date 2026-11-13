"""SigmaFidelity Container-Native HTTP Health Watchdog (HWB-QMS-9.2).

Replaces legacy /mnt/c OneDrive 9P log-tailing loops with a zero-subprocess,
container-native HTTP readiness monitor and 3-strike circuit-breaker telemetry.
"""

import os
import signal
import time
from datetime import datetime
from types import FrameType
from typing import Optional, Tuple

import requests

DEFAULT_HEALTH_URL: str = "http://hwb_web_app:5000/login"
POLL_INTERVAL_SECONDS: int = 60
REQUEST_TIMEOUT_SECONDS: int = 5
MAX_CONSECUTIVE_STRIKES: int = 3

_STOP_REQUESTED: bool = False


def _handle_shutdown(signum: int, _frame: Optional[FrameType]) -> None:
    """Marks watchdog loop for clean termination on SIGINT/SIGTERM."""
    global _STOP_REQUESTED
    _STOP_REQUESTED = True
    log_event(f"SHUTDOWN_SIGNAL_RECEIVED signum={signum}")


def log_event(message: str) -> None:
    """Writes structured timestamped watchdog telemetry to container stdout."""
    ts = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    print(f"[{ts}] [WATCHDOG] {message}", flush=True)


def check_server_health(health_url: str) -> Tuple[bool, int, float, str]:
    """Executes bounded HTTP probe against the internal web container."""
    started = time.monotonic()
    try:
        resp = requests.get(
            health_url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
        latency_ms = round((time.monotonic() - started) * 1000.0, 2)
        is_ok = 200 <= resp.status_code < 400
        detail = f"HTTP_{resp.status_code}"
        return is_ok, resp.status_code, latency_ms, detail
    except requests.RequestException as exc:
        latency_ms = round((time.monotonic() - started) * 1000.0, 2)
        return False, 0, latency_ms, exc.__class__.__name__


def monitor_health_loop() -> None:
    """Polls HWB web endpoint every 60s with 3-strike failure alerting."""
    health_url = os.environ.get(
        "HWB_WATCHDOG_HEALTH_URL", DEFAULT_HEALTH_URL
    ).strip() or DEFAULT_HEALTH_URL
    raw_interval = os.environ.get(
        "HWB_WATCHDOG_INTERVAL_SEC", str(POLL_INTERVAL_SECONDS)
    )
    interval_sec = max(15, int(raw_interval))

    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    consecutive_failures: int = 0
    log_event(
        f"ONLINE mode=HTTP_PASSIVE target={health_url} "
        f"interval={interval_sec}s timeout={REQUEST_TIMEOUT_SECONDS}s"
    )

    while not _STOP_REQUESTED:
        healthy, status_code, latency_ms, detail = check_server_health(
            health_url
        )
        if healthy:
            if consecutive_failures > 0:
                log_event(
                    f"RECOVERED target={health_url} status={status_code} "
                    f"latency_ms={latency_ms} prior_strikes={consecutive_failures}"
                )
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_STRIKES:
                log_event(
                    f"ALERT_3_STRIKE_BREACH strikes={consecutive_failures}/"
                    f"{MAX_CONSECUTIVE_STRIKES} target={health_url} "
                    f"detail={detail} latency_ms={latency_ms}"
                )
            else:
                log_event(
                    f"PROBE_WARN strike={consecutive_failures}/"
                    f"{MAX_CONSECUTIVE_STRIKES} target={health_url} "
                    f"detail={detail} latency_ms={latency_ms}"
                )

        slept = 0
        while slept < interval_sec and not _STOP_REQUESTED:
            time.sleep(1)
            slept += 1

    log_event("WATCHDOG_STOPPED_CLEANLY")


if __name__ == "__main__":
    monitor_health_loop()
