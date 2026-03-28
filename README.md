# SECS/GEM MCP Server

An MCP (Model Context Protocol) server that lets you control semiconductor equipment through natural language in Claude Code.

Wraps the [go-factory-io](https://github.com/seikaikyo/go-factory-io) REST API with 10 tools covering equipment monitoring, parameter control, carrier management, and process job operations.

## What you can do

Talk to Claude Code like this:

```
"What's the current equipment status?"
"Show me all active alarms"
"Set the chamber temperature to 350 degrees" (EC update)
"Start process job PJ-001 with recipe OXIDE-A on FOUP-001 slots 1-5"
"What's the current OEE?"
"Run the ONLINE command"
"Check the security status"
```

Claude picks the right tool, sends the SECS/GEM command, and returns the result.

## Tools

| Tool | Description |
|------|-------------|
| `get_equipment_status` | Communication state, control state, transport state |
| `list_status_variables` | All SVs with values, names, units |
| `get_status_variable` | Specific SV by ID |
| `list_alarms` | All or active-only alarms |
| `list_equipment_constants` | All ECs with values |
| `set_equipment_constant` | Update an EC value (temperature, pressure, etc.) |
| `execute_command` | Run RCMD (START, STOP, ABORT, PP-SELECT, etc.) |
| `manage_process_job` | Create, start, stop, abort process jobs |
| `manage_carrier` | FOUP operations (bind, unbind, proceed, complete) |
| `get_security_status` | SEMI E191 cybersecurity report |

## Setup

### 1. Install

```bash
git clone https://github.com/seikaikyo/secsgem-mcp-server.git
cd secsgem-mcp-server
pip install -e .
```

### 2. Start go-factory-io simulator

```bash
# In the go-factory-io directory
./secsgem simulate -api :8080
```

### 3. Add to Claude Code

```bash
claude mcp add secsgem -- python /path/to/secsgem-mcp-server/server.py
```

Or add manually to `~/.claude.json`:

```json
{
  "mcpServers": {
    "secsgem": {
      "command": "python",
      "args": ["/path/to/secsgem-mcp-server/server.py"],
      "env": {
        "SECSGEM_API_URL": "http://localhost:8080"
      }
    }
  }
}
```

### 4. Restart Claude Code

The tools will appear when you ask equipment-related questions.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `SECSGEM_API_URL` | `http://localhost:8080` | go-factory-io REST API base URL |

## SEMI Standards Coverage

This server exposes operations from these SEMI standards (implemented by go-factory-io):

- **E30** GEM: status variables, equipment constants, alarms, collection events, remote commands
- **E87** Carrier Management: FOUP lifecycle, load port control
- **E40** Process Job Management: recipe execution, job lifecycle
- **E116** Equipment Performance Tracking: OEE calculation
- **E191** Cybersecurity Status Reporting

## Requirements

- Python 3.11+
- [go-factory-io](https://github.com/seikaikyo/go-factory-io) running with REST API enabled
- Claude Code

## License

MIT

---

Validated against go-factory-io software simulator. Built with AI-assisted development using Claude Code.
