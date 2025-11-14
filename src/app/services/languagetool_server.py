"""
Manage LanguageTool server as subprocess within FastAPI container.

This module handles starting/stopping LanguageTool server as a background
process when using local server mode.
"""
import subprocess
import logging
import time
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_languagetool_process: Optional[subprocess.Popen] = None
_languagetool_port: int = 8010


def find_languagetool_jar() -> Optional[Path]:
    """Find LanguageTool server JAR file."""
    lt_base = Path("/opt/languagetool")
    
    if not lt_base.exists():
        logger.warning("LanguageTool directory not found at /opt/languagetool")
        return None
    
    # Look for LanguageTool-*/languagetool-server.jar
    jar_files = list(lt_base.glob("LanguageTool-*/languagetool-server.jar"))
    
    if not jar_files:
        logger.warning("LanguageTool server JAR not found")
        return None
    
    return jar_files[0]


def is_server_ready(port: int, timeout: float = 2.0) -> bool:
    """Check if LanguageTool server is ready."""
    try:
        import requests
        response = requests.get(
            f"http://localhost:{port}/v2/languages",
            timeout=timeout
        )
        return response.status_code == 200
    except Exception:
        return False


def start_languagetool_server(port: int = 8010) -> bool:
    """
    Start LanguageTool server as background subprocess.
    
    Args:
        port: Port to run LanguageTool server on (default: 8010)
        
    Returns:
        True if server started successfully, False otherwise
    """
    global _languagetool_process, _languagetool_port
    
    if _languagetool_process is not None:
        # Check if process is still alive
        if _languagetool_process.poll() is None:
            logger.info("LanguageTool server already running")
            return True
        else:
            logger.warning("LanguageTool server process died, restarting...")
            _languagetool_process = None
    
    jar_path = find_languagetool_jar()
    if jar_path is None:
        logger.error("Cannot start LanguageTool server: JAR not found")
        return False
    
    jar_dir = jar_path.parent
    
    try:
        logger.info(f"Starting LanguageTool server on port {port}...")
        
        # Start LanguageTool server as subprocess
        process = subprocess.Popen(
            [
                "java",
                "-Xmx300m",  # Max heap: 300MB (leave room for FastAPI)
                "-Xms100m",  # Initial heap: 100MB
                "-XX:+UseG1GC",  # Use G1 garbage collector (better for small heaps)
                "-cp", str(jar_path),
                "org.languagetool.server.HTTPServer",
                "--port", str(port),
                "--public",
                "--allow-origin", "*"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(jar_dir),
            env=os.environ.copy()
        )
        
        # Wait for server to be ready (max 30 seconds)
        logger.info("Waiting for LanguageTool server to be ready...")
        for i in range(30):
            if process.poll() is not None:
                # Process died
                stdout, stderr = process.communicate()
                logger.error(f"LanguageTool server failed to start:")
                logger.error(f"STDOUT: {stdout.decode() if stdout else 'None'}")
                logger.error(f"STDERR: {stderr.decode() if stderr else 'None'}")
                return False
            
            if is_server_ready(port):
                logger.info(f"✅ LanguageTool server started successfully on port {port}")
                _languagetool_process = process
                _languagetool_port = port
                return True
            
            time.sleep(1)
        
        # Timeout
        logger.error("LanguageTool server failed to start within 30 seconds")
        process.terminate()
        process.wait(timeout=5)
        return False
        
    except Exception as e:
        logger.exception(f"Failed to start LanguageTool server: {e}")
        return False


def stop_languagetool_server() -> None:
    """Stop LanguageTool server subprocess."""
    global _languagetool_process
    
    if _languagetool_process is None:
        return
    
    try:
        logger.info("Stopping LanguageTool server...")
        _languagetool_process.terminate()
        
        # Wait up to 5 seconds for graceful shutdown
        try:
            _languagetool_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if not responding
            logger.warning("LanguageTool server did not stop gracefully, forcing kill...")
            _languagetool_process.kill()
            _languagetool_process.wait()
        
        logger.info("LanguageTool server stopped")
        _languagetool_process = None
        
    except Exception as e:
        logger.exception(f"Error stopping LanguageTool server: {e}")
        _languagetool_process = None


def get_languagetool_status() -> dict:
    """Get current status of LanguageTool server."""
    global _languagetool_process, _languagetool_port
    
    if _languagetool_process is None:
        return {
            "running": False,
            "port": _languagetool_port,
            "ready": False
        }
    
    is_alive = _languagetool_process.poll() is None
    is_ready = is_alive and is_server_ready(_languagetool_port)
    
    return {
        "running": is_alive,
        "port": _languagetool_port,
        "ready": is_ready
    }

