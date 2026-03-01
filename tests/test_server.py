"""Tests for MCP server tool registration."""

import asyncio


def test_all_13_tools_registered():
    """Server should register exactly 13 tools."""
    from server import list_tools

    tools = asyncio.run(list_tools())
    assert len(tools) == 13, f"Expected 13 tools, got {len(tools)}: {[t.name for t in tools]}"


def test_tool_names():
    """All expected tool names should be registered."""
    from server import list_tools

    tools = asyncio.run(list_tools())
    names = {t.name for t in tools}

    expected = {
        "memory_search", "memory_write", "memory_delete",
        "file_search", "project_context", "session_bridge",
        "decision_log", "verify_identity", "identity_set",
        "recommend_tech", "memory_link", "memory_chain",
        "session_init",
    }
    assert expected == names, f"Missing: {expected - names}, Extra: {names - expected}"


def test_tools_have_descriptions():
    """Every tool should have a non-empty description."""
    from server import list_tools

    tools = asyncio.run(list_tools())
    for tool in tools:
        assert tool.description, f"Tool {tool.name} has no description"
        assert len(tool.description) > 10, f"Tool {tool.name} description too short"


def test_tools_have_input_schema():
    """Every tool should have an input schema."""
    from server import list_tools

    tools = asyncio.run(list_tools())
    for tool in tools:
        assert tool.inputSchema is not None, f"Tool {tool.name} has no input schema"
        assert "type" in tool.inputSchema, f"Tool {tool.name} schema missing 'type'"
