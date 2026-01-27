.PHONY: auth install register unregister

auth:          ## Run initial OAuth flow (opens browser)
	uv run python server.py --auth

install:       ## Install/sync dependencies
	uv sync

register:      ## Register MCP server with Claude Code (user scope)
	claude mcp add --scope user gcal-mcp -- uv run --directory $(CURDIR) python server.py

unregister:    ## Remove MCP server from Claude Code
	claude mcp remove --scope user gcal-mcp
