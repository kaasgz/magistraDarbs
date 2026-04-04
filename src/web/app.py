"""Run a small local web dashboard for the thesis project."""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import threading
import webbrowser
from collections.abc import Sequence
from functools import partial
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src.web.dashboard import DashboardService


LOGGER = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).with_name("static")


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for the local web app."""

    parser = argparse.ArgumentParser(
        description="Run the local sports scheduling dashboard.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    parser.add_argument(
        "--instance-count",
        type=int,
        default=6,
        help="Default number of generated demo instances.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Default random seed used for demo generation.",
    )
    parser.add_argument(
        "--time-limit-seconds",
        type=int,
        default=1,
        help="Per-solver time limit used by the demo pipeline.",
    )
    parser.add_argument(
        "--bootstrap-demo",
        action="store_true",
        help="Generate demo data and run the full pipeline on startup.",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open the dashboard in the default browser after startup.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Start the local dashboard server."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    service = DashboardService(
        workspace_root=Path.cwd(),
        default_instance_count=args.instance_count,
        default_random_seed=args.random_seed,
        default_time_limit_seconds=args.time_limit_seconds,
    )

    if args.bootstrap_demo:
        LOGGER.info("Bootstrapping demo data before starting the dashboard.")
        service.bootstrap_demo_pipeline(
            instance_count=args.instance_count,
            random_seed=args.random_seed,
            time_limit_seconds=args.time_limit_seconds,
        )

    server = ThreadingHTTPServer(
        (args.host, args.port),
        partial(DashboardRequestHandler, service=service),
    )
    url = f"http://{args.host}:{args.port}/"

    if args.open_browser:
        threading.Thread(target=lambda: webbrowser.open_new_tab(url), daemon=True).start()

    LOGGER.info("Dashboard running at %s", url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Stopping dashboard server.")
    finally:
        server.server_close()
    return 0


class DashboardRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler serving the dashboard and JSON API."""

    def __init__(self, *args: object, service: DashboardService, **kwargs: object) -> None:
        self.service = service
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        """Serve static files and dashboard state."""

        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._serve_static("index.html")
            return
        if parsed.path == "/app.css":
            self._serve_static("app.css")
            return
        if parsed.path == "/app.js":
            self._serve_static("app.js")
            return
        if parsed.path == "/api/state":
            self._send_json(HTTPStatus.OK, self.service.build_dashboard_state())
            return
        if parsed.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return

        self._send_json(
            HTTPStatus.NOT_FOUND,
            {"error": f"Unknown route: {parsed.path}"},
        )

    def do_POST(self) -> None:  # noqa: N802
        """Handle dashboard actions."""

        parsed = urlparse(self.path)
        payload = self._read_json_body()
        try:
            if parsed.path == "/api/bootstrap-demo":
                state = self.service.bootstrap_demo_pipeline(
                    instance_count=_safe_int(payload.get("instance_count"), self.service.default_instance_count),
                    random_seed=_safe_int(payload.get("random_seed"), self.service.default_random_seed),
                    time_limit_seconds=_safe_int(
                        payload.get("time_limit_seconds"),
                        self.service.default_time_limit_seconds,
                    ),
                )
            elif parsed.path == "/api/load-real-instance":
                state = self.service.load_real_instance(str(payload.get("relative_path", "")))
            elif parsed.path == "/api/generate-synthetic-instance":
                state = self.service.generate_synthetic_preview(
                    difficulty_level=_safe_string(
                        payload.get("difficulty_level"),
                        self.service.default_synthetic_difficulty,
                    ),
                    random_seed=_safe_int(payload.get("random_seed"), self.service.default_random_seed),
                )
            else:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"error": f"Unknown route: {parsed.path}"},
                )
                return
        except RuntimeError as exc:
            self._send_json(HTTPStatus.CONFLICT, {"error": str(exc)})
            return
        except (FileNotFoundError, ValueError) as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        except Exception as exc:  # pragma: no cover - defensive HTTP boundary
            LOGGER.exception("Dashboard request failed for %s.", parsed.path)
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
            return

        self._send_json(HTTPStatus.OK, state)

    def log_message(self, format: str, *args: object) -> None:
        """Route HTTP logs through the project logger."""

        LOGGER.info("%s - %s", self.address_string(), format % args)

    def _serve_static(self, file_name: str) -> None:
        """Serve one static dashboard asset."""

        file_path = STATIC_DIR / file_name
        if not file_path.exists():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Missing static asset: {file_name}"})
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        payload = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self) -> dict[str, object]:
        """Read a JSON request body, returning an empty object when missing."""

        content_length = self.headers.get("Content-Length")
        if not content_length:
            return {}

        raw_payload = self.rfile.read(int(content_length))
        if not raw_payload:
            return {}
        try:
            decoded = json.loads(raw_payload.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}

    def _send_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        """Send one JSON response."""

        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _safe_int(value: object, default: int) -> int:
    """Convert a scalar value to int, falling back to a default."""

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _safe_string(value: object, default: str) -> str:
    """Convert a scalar value to a non-empty string, falling back to a default."""

    text = str(value or "").strip()
    return text or default


if __name__ == "__main__":
    raise SystemExit(main())
