# DevOps Diagnostics MCP Server (with RAG Knowledge Base)

An MCP (Model Context Protocol) server that connects Jenkins, Docker, and Kubernetes to an AI agent (Claude), enabling natural-language infrastructure diagnostics — combining **live system data** with a **RAG-based knowledge base** of past troubleshooting patterns.

## What it does

Instead of separately opening Jenkins to check a build, running `kubectl describe pod` for a crash, and digging through Docker logs, this project exposes all three as callable tools to an AI agent. On top of that, it also searches a local knowledge base of documented issue/fix patterns — so the agent can answer not just "what's happening now" but also "have we seen this before, and how was it fixed."

**Example:**
> "My pod keeps restarting with CrashLoopBackOff — have we seen this before? Also check its current status."

The agent calls `search_knowledge_base` (historical knowledge) **and** `describe_pod` / `get_pod_status` (live cluster data), then combines both into one grounded answer — instead of guessing or checking multiple dashboards by hand.

## Architecture

```
                Dev pushes code to GitHub
                        │
      Jenkins ──build──▶ Docker ──image──▶ Kubernetes pod
      (this pipeline runs completely independently)

  ─────────────────────────────────────────────────────
              MCP layer (read-only, parallel)
  ─────────────────────────────────────────────────────

   MCP server (server.py) knows how to READ from:
     • Jenkins    — via REST API
     • Docker     — via local Docker CLI
     • Kubernetes — via kubectl
     • Knowledge base — via a local vector database (RAG)

   AI agent (Claude Desktop) connects to the MCP server
   over stdio, and calls these tools on request:

     "why did the last build fail?"
     "is the new pod healthy?"
     "have we seen this error before, and how was it solved?"
```

**Important design note:** MCP does not modify the CI/CD pipeline in any way. It's a strictly read-only observability layer that sits *beside* the pipeline — Jenkins, Docker, and Kubernetes configs are untouched. The MCP server independently queries each system's existing API, the same way a tool like Grafana or Datadog would.

## Tools exposed

| Tool | System | What it returns |
|---|---|---|
| `get_jenkins_build_status` | Jenkins | Last build result (SUCCESS/FAILURE) |
| `get_jenkins_console_log` | Jenkins | Full console output of a build, to find the actual error |
| `list_docker_containers` | Docker | All containers and their status |
| `get_docker_container_logs` | Docker | Recent logs from a specific container |
| `inspect_docker_container` | Docker | Exit code and error reason for a crashed container |
| `get_pod_status` | Kubernetes | Status of all pods in a namespace |
| `get_pod_logs` | Kubernetes | Recent logs from a specific pod |
| `describe_pod` | Kubernetes | Full pod detail — reveals `ImagePullBackOff`, `CrashLoopBackOff`, `OOMKilled`, etc. |
| `get_recent_k8s_events` | Kubernetes | Cluster-wide events — scheduling failures, image pull errors |
| `search_knowledge_base` | RAG (local vector DB) | Semantically matches the question against documented past issues/fixes |

## Knowledge Base (RAG)

In addition to live diagnostics, the server includes a `search_knowledge_base` tool backed by a local vector database. It works like this:

1. **Source data** — a small hand-written knowledge base (`knowledge.py`) documenting common failure patterns (`CrashLoopBackOff`, `OOMKilled`, `ImagePullBackOff`, Jenkins dependency errors, Docker exit issues) and their fixes
2. **Embedding** — each entry is converted into a vector (a numeric representation of its meaning) using `sentence-transformers` (`all-MiniLM-L6-v2`)
3. **Storage** — vectors are stored in a local **ChromaDB** vector database, built once when the server starts
4. **Retrieval** — when a question comes in, it's embedded the same way, and the most semantically similar entries are retrieved — so a question like *"have we seen this crash before?"* correctly matches a note about `CrashLoopBackOff`, even without exact keyword overlap

This is real retrieval-augmented generation, not just an "upload files to chat" feature — the embedding, storage, and retrieval logic is built and understood end-to-end.

## Tech stack

- **Python 3.11** + [MCP SDK](https://github.com/modelcontextprotocol) (`FastMCP`)
- **Transport:** stdio (local) — Claude Desktop launches the server as a subprocess and communicates over stdin/stdout using JSON-RPC
- **Jenkins:** REST API (`requests`)
- **Docker:** local CLI via `subprocess`
- **Kubernetes:** `kubectl` via `subprocess`, using the existing local `~/.kube/config`
- **RAG:** `sentence-transformers` for embeddings + `chromadb` for local vector storage/search

## Setup

**1. Install dependencies**
```bash
pip install mcp requests chromadb sentence-transformers
```

**2. Set environment variables (never hardcode credentials)**
```bash
export JENKINS_URL="http://your-jenkins-host:8080"
export JENKINS_USER="your-username"
export JENKINS_TOKEN="your-api-token"
```

**3. Register the server in Claude Desktop's config**

Location:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "devops-diagnostics": {
      "command": "python",
      "args": ["/full/path/to/server.py"],
      "env": {
        "JENKINS_URL": "http://your-jenkins-host:8080",
        "JENKINS_USER": "your-username",
        "JENKINS_TOKEN": "your-api-token"
      }
    }
  }
}
```

**4. Restart Claude Desktop completely** (quit from system tray, not just close the window)

**5. Verify connection**

Claude Desktop → Developer settings → Local MCP servers. You should see `devops-diagnostics` with status **running**.

## Usage examples

```
"List all my docker containers"
"Check pod status in the default namespace"
"Why is my pod crashing? describe it"
"Get the last Jenkins build status for my-app"
"Show recent cluster events"
"Have we seen an OOMKilled issue before? What fixed it?"
"My pod is stuck in ImagePullBackOff — check the live status and any past notes on this"
```

## Design decisions

**Why read-only, not auto-remediation?**
This project intentionally exposes only *read* operations (get status, get logs, describe, list events, search knowledge) — not *write* operations (restart pod, rollback deployment, scale service). Auto-remediation is a meaningfully bigger step that requires permission scoping, approval gates, and audit logging before it's safe to hand to an AI agent. This project focuses on cutting diagnosis time, with remediation left as a deliberate human decision.

**Why stdio instead of remote/HTTP?**
For local development and personal use, stdio requires no networking, ports, or authentication — Claude Desktop and the server communicate directly as parent/child processes. A remote deployment (HTTP/SSE transport) would require its own hosting, authentication layer, and TLS setup — a natural next step, not implemented here yet.

**Why build custom RAG instead of just uploading files to a chat?**
Off-the-shelf "upload files" features (e.g., Claude Projects) hide the retrieval logic entirely. Building the embedding → storage → retrieval pipeline manually demonstrates actual understanding of how semantic search works, and keeps the knowledge base callable as a tool alongside live diagnostics — not just a static reference.

## Possible extensions

- [ ] Deploy over HTTP/SSE transport for remote/multi-user access
- [ ] Add a GitHub MCP tool for commit/PR context
- [ ] Add an alert-triggered flow (Prometheus/Datadog webhook → agent auto-investigates) instead of manual queries
- [ ] Add authentication/authorization for remote deployment
- [ ] Add write-capable tools behind an approval gate (e.g., restart a known-flaky pod)
- [ ] Grow the knowledge base from real incident history instead of hand-written entries
- [ ] Move from a standalone Claude Desktop client to a custom agent built on the Claude API, with a programmatic reasoning loop

## What this project demonstrates

- Understanding of the MCP client-server architecture (stdio transport, JSON-RPC messaging)
- Integrating multiple real systems (Jenkins REST API, Docker CLI, Kubernetes API) behind a unified tool interface
- Building a working RAG pipeline from scratch (embeddings, vector storage, semantic retrieval) — not just consuming a pre-built feature
- Secure credential handling via environment variables
- Clear reasoning about read-only vs. write-capable AI tool design and its safety implications
