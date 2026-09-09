"""
SECS/GEM MCP Server
Wraps go-factory-io REST API for Claude Code integration.
Lets engineers control semiconductor equipment using natural language.
"""

import os
import httpx
from fastmcp import FastMCP

BASE_URL = os.environ.get("SECSGEM_API_URL", "http://localhost:8080")

# go-factory-io 的 REST API 用 bearer token，讀與寫分開，而且沒設 token 時
# 只肯在 loopback 位址提供服務（pkg/security/apitoken.go 的 RequireTokenForListen）。
# 這支伺服器原本完全不送憑證，所以只對關掉授權的實例有用。
#
# 給哪一把鑰匙就決定這台 MCP server 能做什麼：
#   讀取 token → 監控類工具可用，寫入類工具會被上游擋下（403）
#   寫入 token → 全部可用（上游的寫入 token 同時涵蓋讀取）
# 沒設就不送 Authorization，維持原本對本機無授權實例的行為。
API_TOKEN = os.environ.get("SECSGEM_API_TOKEN", "").strip()


def _headers() -> dict:
    return {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}

mcp = FastMCP(
    "secsgem",
    # FastMCP 在 2.x 期間把這個參數從 description 改名為 instructions。
    # pyproject 原本寫 fastmcp>=2.0.0 沒有上界，所以新裝的環境會拿到
    # 不收 description 的版本，伺服器在匯入時就 TypeError。
    instructions="Control semiconductor equipment via SECS/GEM protocols. "
    "Connects to go-factory-io for equipment monitoring, parameter adjustment, "
    "carrier management, and process job control.",
)


def _client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, timeout=10.0, headers=_headers())


def _get(path: str) -> dict:
    with _client() as c:
        r = c.get(path)
        r.raise_for_status()
        return r.json()


def _put(path: str, json: dict) -> dict:
    with _client() as c:
        r = c.put(path, json=json)
        r.raise_for_status()
        return r.json()


def _post(path: str, json: dict) -> dict:
    with _client() as c:
        r = c.post(path, json=json)
        r.raise_for_status()
        return r.json()


# --- Monitoring Tools ---


@mcp.tool()
def get_equipment_status() -> dict:
    """Get current equipment status including communication state, control state,
    and transport state. Use this to check if equipment is online and communicating."""
    return _get("/api/status")


@mcp.tool()
def list_status_variables() -> dict:
    """List all Status Variables (SV) with their current values, names, and units.
    SVs are read-only equipment data like temperatures, pressures, and counters."""
    return _get("/api/sv")


@mcp.tool()
def get_status_variable(svid: int) -> dict:
    """Get a specific Status Variable value by its SVID number.

    Args:
        svid: Status Variable ID (e.g., 1001 for wafer count)
    """
    return _get(f"/api/sv/{svid}")


@mcp.tool()
def list_alarms(active_only: bool = False) -> dict:
    """List equipment alarms. Can filter to show only active alarms.

    Args:
        active_only: If True, only return currently active (SET) alarms
    """
    path = "/api/alarms/active" if active_only else "/api/alarms"
    return _get(path)


@mcp.tool()
def list_equipment_constants() -> dict:
    """List all Equipment Constants (EC) with their current values, names, and units.
    ECs are configurable parameters like temperature setpoints and time limits."""
    return _get("/api/ec")


# --- Control Tools ---


@mcp.tool()
def set_equipment_constant(ecid: int, value: float | int | str) -> dict:
    """Update an Equipment Constant value. Use this to change equipment parameters
    like temperature setpoints, pressure limits, or timing values.

    Args:
        ecid: Equipment Constant ID
        value: New value to set
    """
    return _put(f"/api/ec/{ecid}", {"value": value})


@mcp.tool()
def execute_command(command: str, params: dict | None = None) -> dict:
    """Execute a Remote Command (RCMD) on the equipment.
    Common commands: ONLINE, OFFLINE, START, STOP, ABORT, PP-SELECT.

    Args:
        command: Command name (e.g., "START", "STOP", "PP-SELECT")
        params: Optional command parameters as key-value pairs
    """
    body = {"command": command}
    if params:
        body["params"] = params
    return _post("/api/command", body)


@mcp.tool()
def manage_process_job(
    action: str,
    job_id: str,
    recipe: str | None = None,
    carrier_id: str | None = None,
    slots: list[int] | None = None,
) -> dict:
    """Manage process jobs on the equipment.

    Args:
        action: One of "create", "start", "stop", "abort", "status"
        job_id: Process Job ID (e.g., "PJ-001")
        recipe: Recipe ID, required for "create" action
        carrier_id: Carrier/FOUP ID, required for "create" action
        slots: Slot numbers to process, required for "create" action
    """
    if action == "status":
        return _get("/api/status")

    body = {"action": action, "jobId": job_id}
    if recipe:
        body["recipe"] = recipe
    if carrier_id:
        body["carrierId"] = carrier_id
    if slots:
        body["slots"] = slots
    return _post("/api/command", {"command": f"PJ-{action.upper()}", "params": body})


@mcp.tool()
def manage_carrier(
    action: str,
    carrier_id: str,
    port: int | None = None,
) -> dict:
    """Manage FOUP carriers on load ports.

    Args:
        action: One of "bind", "unbind", "proceed", "complete", "unload"
        carrier_id: Carrier/FOUP ID (e.g., "FOUP-001")
        port: Load port number, required for "bind" action
    """
    body = {"action": action, "carrierId": carrier_id}
    if port is not None:
        body["port"] = port
    return _post(
        "/api/command",
        {"command": f"CARRIER-{action.upper()}", "params": body},
    )


# --- Security Tool ---


@mcp.tool()
def get_security_status() -> dict:
    """Get SEMI E191 cybersecurity status report. Shows security posture
    including TLS state, RBAC policies, and audit configuration."""
    return _get("/api/security/status")


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
