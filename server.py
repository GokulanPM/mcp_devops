from mcp.server.fastmcp import FastMCP
import subprocess
import requests
import os

mcp = FastMCP("devops-diagnostics")

JENKINS_URL = os.environ.get("JENKINS_URL", "http://localhost:8080")
JENKINS_USER = os.environ.get("JENKINS_USER")
JENKINS_TOKEN = os.environ.get("JENKINS_TOKEN")

def run_cmd(cmd, timeout=10):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
    except Exception as e:
        return f"Command failed: {str(e)}"

# ───────────── JENKINS ─────────────

@mcp.tool()
def get_jenkins_build_status(job_name: str) -> str:
    """Get last build status (SUCCESS/FAILURE) for a Jenkins job"""
    try:
        r = requests.get(
            f"{JENKINS_URL}/job/{job_name}/lastBuild/api/json",
            auth=(JENKINS_USER, JENKINS_TOKEN), timeout=10
        )
        return r.text
    except Exception as e:
        return f"Failed to reach Jenkins: {str(e)}"

@mcp.tool()
def get_jenkins_console_log(job_name: str, build_number: str = "lastBuild") -> str:
    """Get console output/log of a specific Jenkins build to see WHY it failed"""
    try:
        r = requests.get(
            f"{JENKINS_URL}/job/{job_name}/{build_number}/consoleText",
            auth=(JENKINS_USER, JENKINS_TOKEN), timeout=10
        )
        return r.text[-3000:]
    except Exception as e:
        return f"Failed to fetch console log: {str(e)}"

# ───────────── DOCKER ─────────────

@mcp.tool()
def list_docker_containers() -> str:
    """List all containers and their status (running/exited/crashed)"""
    return run_cmd(["docker", "ps", "-a"])

@mcp.tool()
def get_docker_container_logs(container_name: str) -> str:
    """Get recent logs of a specific Docker container"""
    return run_cmd(["docker", "logs", "--tail", "50", container_name])

@mcp.tool()
def inspect_docker_container(container_name: str) -> str:
    """Get detailed info on why a container might have exited"""
    return run_cmd(["docker", "inspect", "--format",
                     "{{.State.Status}} | ExitCode: {{.State.ExitCode}} | Error: {{.State.Error}}",
                     container_name])

# ───────────── KUBERNETES ─────────────

@mcp.tool()
def get_pod_status(namespace: str = "default") -> str:
    """List all pods and their status in a namespace"""
    return run_cmd(["kubectl", "get", "pods", "-n", namespace])

@mcp.tool()
def get_pod_logs(pod_name: str, namespace: str = "default") -> str:
    """Get recent logs from a specific pod"""
    return run_cmd(["kubectl", "logs", pod_name, "-n", namespace, "--tail=50"])

@mcp.tool()
def describe_pod(pod_name: str, namespace: str = "default") -> str:
    """Get full pod details - shows WHY a pod is failing"""
    return run_cmd(["kubectl", "describe", "pod", pod_name, "-n", namespace])

@mcp.tool()
def get_recent_k8s_events(namespace: str = "default") -> str:
    """Get recent cluster events"""
    return run_cmd(["kubectl", "get", "events", "-n", namespace,
                     "--sort-by=.lastTimestamp"])

if __name__ == "__main__":
    mcp.run()