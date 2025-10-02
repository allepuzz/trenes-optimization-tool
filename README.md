# Trenes Optimization Tool 🚄

A learning project to master the tool → agent → MCP development progression through Spanish train ticket optimization.

## Project Overview

This project builds a comprehensive system to find the optimal timing for purchasing Spanish train tickets, progressing through three development phases:

1. **🛠️ Tool Development**: Core web scraping and price optimization
2. **🤖 Agent Creation**: LangGraph-powered intelligent agent
3. **🔌 MCP Standardization**: Model Context Protocol server for Claude Code

## Target Market
- Spanish train providers (Renfe, AVE, regional services)
- Spanish timezone and scheduling optimization
- Price tracking and purchase timing recommendations

## Tech Stack
- **Framework**: LangGraph + LangChain
- **Language**: Python 3.11+
- **Web Scraping**: Playwright + BeautifulSoup
- **Database**: SQLite → PostgreSQL
- **API**: FastAPI (MCP server)
- **Testing**: pytest + playwright

## Project Structure
```
trenes-optimization-tool/
├── src/
│   ├── trenes_tool/           # Core scraping and optimization
│   ├── trenes_agent/          # LangGraph agent implementation
│   └── trenes_mcp/            # MCP server for Claude Code
├── tests/                     # Test suite
├── docs/                      # Documentation
├── examples/                  # Usage examples
└── blog_posts/               # Learning journey documentation
```

## Development Phases

### Phase 1: Foundation & Core Tool (Current)
- [x] Repository setup
- [ ] Web scraping infrastructure
- [ ] Price tracking system
- [ ] Basic optimization logic

### Phase 2: Agent Development
- [ ] LangGraph workflow design
- [ ] Natural language interface
- [ ] Advanced optimization features

### Phase 3: MCP Server
- [ ] MCP protocol implementation
- [ ] Claude Code integration
- [ ] Documentation and examples

## Quick Start

```bash
# Clone and setup
git clone [repository-url]
cd trenes-optimization-tool
pip install -e .

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start development server
python -m trenes_tool.main
```

## Learning Journey

This project serves as a comprehensive learning experience, documenting the entire development process from initial concept to published MCP server. Follow along in the `blog_posts/` directory for detailed insights and lessons learned.

## Contributing

This is primarily a learning project, but contributions and suggestions are welcome! Please see our development roadmap and feel free to open issues or discussions.

## License

MIT License - see LICENSE file for details.