# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Trenes-tool** is a learning project focused on building Spanish train ticket optimization tools. The project follows a progressive learning path:

1. **Tool Development**: Create core functionality to find optimal train ticket purchase timing
2. **Agent Creation**: Wrap the tool in an intelligent agent for automated decision-making
3. **MCP Standardization**: Package as a Model Context Protocol (MCP) server for integration with Claude Code

### Project Goals
- Learn the tool → agent → MCP development progression
- Build Spanish train ticket price optimization system
- Integrate with Spanish train providers (Renfe, AVE, regional services)
- Create reusable MCP server for Claude Code integration
- Document the entire learning journey for others

### Target Market
- Spanish train travel (Renfe, AVE, regional providers)
- Spanish timezone and scheduling
- Price optimization and timing recommendations

## Configuration Files

### Core Claude Settings
- `.credentials.json` - Contains Claude AI OAuth tokens and subscription information
- `settings.json` - Main permission settings for Claude Code operations
- `.claude/settings.local.json` - Local permission overrides
- `mcp_settings.json` - MCP (Model Context Protocol) server configurations

### MCP Servers
- **Playwright Server**: Configured for browser automation tasks using `@executeautomation/playwright-mcp-server`

## Available Commands

Based on the permission settings, the following commands are pre-approved:

### Development Commands
- `npm install` and variants
- `npm run dev` and variants
- `npm run build` and variants
- `npm run lint` and variants
- `npm run test:run` and variants
- `npx tsc` for TypeScript compilation

### File Operations
- `find` commands for file searching
- `mkdir` for directory creation
- `rm` for file removal
- `del nul` (Windows)

### Git Operations
- `git status`, `git add`, `git commit`
- `git pull`, `git push`, `git checkout`
- `gh pr view` and `gh pr diff` for GitHub PR operations

### Restrictions
- Force pushes to main/dev branches are blocked
- Destructive file system operations are blocked
- System-level commands (shutdown, reboot) are blocked

## Usage Notes

This configuration directory appears to be set up for working with Node.js/TypeScript projects, with particular emphasis on development workflow automation and browser testing capabilities through Playwright.