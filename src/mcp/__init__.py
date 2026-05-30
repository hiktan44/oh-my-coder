"""
MCP (Model Context Protocol) modul

oh-my-coder yapicin MCP Server, yondisindakisimistemci (Claude Desktop / Cursor / Dify vb.) 
aciga cikar Agent yetenek. 

protokol: JSON-RPC 2.0 over stdio
- oku stdin, hersatirbir JSON-RPC istek
- cikti stdout, hersatirbir JSON-RPC yanit

MCP SDK icinde Python 3.10+ zamanotomatikbaslatkullan (pip install mcp) , 
Python 3.9 kullanasilyaratmanueluygula (yokdisindakisimbagimlilik) . 
"""

__version__ = "0.2.0"

# Try importing MCP SDK (Python 3.10+), falls back to native impl
try:
    from mcp.types import Resource, TextContent, Tool  # noqa: F401

    from mcp.server import Server  # noqa: F401

    MCP_SDK_AVAILABLE = True
except Exception:
    MCP_SDK_AVAILABLE = False

from .resources import MCP_RESOURCES, get_mcp_resources
from .server import McpServer
from .tools import MCP_TOOLS, get_mcp_tools

__all__ = [
    "MCP_RESOURCES",
    "MCP_SDK_AVAILABLE",
    "MCP_TOOLS",
    "McpServer",
    "get_mcp_resources",
    "get_mcp_tools",
]
