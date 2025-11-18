# Keycloak MCP Server - Student Internship Reference

This project is a reference implementation for a student internship trial task. It demonstrates how to build an MCP (Model Context Protocol) server that integrates with Keycloak's Admin REST API.

## Learning Objectives

By studying this codebase, students will learn:

- **API Integration**: How to work with OAuth2/OIDC authentication
- **MCP Server Development**: Building tools that AI assistants can use
- **Python Best Practices**: Type hints, error handling, documentation, and project structure
- **Security**: Proper handling of credentials and tokens
- **Testing**: Writing tests for API clients

## Project Structure

```
.
README.md                        # This file
pyproject.toml                   # Project configuration and dependencies
.env.example                     # Template for environment variables
.env                             # Your actual credentials (never commit!)

test_keycloak_connectivity.py    # Exploration script showing API discovery
exceptions.py                    # Custom exception classes
types.py                         # Type definitions for API responses
client.py                        # Keycloak API client implementation
client_expectation.py            # Keycloak API client implementation that I expected you to produce today
server.py                        # MCP server implementation
server_expectation.py            # MCP server implementation that I expected you to produce today

tests/                           # Test files (to be created)
    test_client.py
```

## Requirements

- Python 3.13 or higher
- A running Keycloak instance (local or remote)
- A Keycloak client with appropriate permissions

## Setup Instructions

### 1. Install Dependencies

This project uses [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
# Install runtime dependencies
uv pip install -e .

# Or install with development dependencies (recommended)
uv pip install -e ".[dev]"
```

### 2. Configure Keycloak Access

Create a `.env` file in the project root (use `.env.example` as a template):

```bash
KEYCLOAK_URL=http://localhost:8080
CLIENT_ID=admin-cli
CLIENT_SECRET=your-secret-here
```

**Important**: Never commit the `.env` file! It's already in `.gitignore`.

#### How to Get Keycloak Credentials

1. Log in to your Keycloak Admin Console
2. Select the realm you want to work with (usually "master")
3. Go to "Clients" in the left menu
4. Create a new client or use an existing one (e.g., "admin-cli")
5. Under "Credentials" tab, copy the client secret
6. Ensure the client has "Service Account Enabled" turned on
7. Under "Service Account Roles", assign appropriate admin roles

### 3. Test Connectivity

Before running the full MCP server, verify your Keycloak connection works:

```bash
python test_keycloak_connectivity.py
```

This script demonstrates:
- How to discover OIDC endpoints
- How to authenticate using client credentials
- How to make authenticated API requests

**Expected output**:
```
[{'id': 'master', 'realm': 'master', ...}, ...]
Found 2 realms
```

## Running the MCP Server

### Start the server

```bash
# Using the defined entry point
uv run keycloak-mcp

# Or directly with Python
python server.py
```

The server runs in `stdio` mode, which means it communicates via standard input/output. This is the standard MCP transport mechanism.

### Using with an MCP Client

To use this server with an MCP-compatible client (like Claude Desktop), add it to your MCP configuration:

```json
{
  "mcpServers": {
    "keycloak": {
      "command": "uv",
      "args": ["run", "keycloak-mcp"],
      "env": {
        "KEYCLOAK_URL": "http://localhost:8080",
        "CLIENT_ID": "admin-cli",
        "CLIENT_SECRET": "your-secret-here"
      }
    }
  }
}
```

## Available MCP Tools

### 1. `get_realms()`

Get a list of all realms in the Keycloak server.

**Example**:
```python
realms = get_realms()
# Returns: [{'id': 'master', 'realm': 'master', ...}, ...]
```

### 2. `get_users(realm, max_users=100)`

Get users from a specific realm.

**Parameters**:
- `realm` (str): The realm name (e.g., "master")
- `max_users` (int): Maximum number of users to return (default: 100)

**Example**:
```python
users = get_users("master", 50)
# Returns: [{'id': '...', 'username': 'john.doe', ...}, ...]
```

### 3. `get_user_info(realm, user_id)`

Get detailed information about a specific user.

**Parameters**:
- `realm` (str): The realm name
- `user_id` (str): The user's UUID (not the username!)

**Example**:
```python
user = get_user_info("master", "8a9b1c2d-3e4f-5a6b-7c8d-9e0f1a2b3c4d")
# Returns: {'id': '...', 'username': 'john.doe', 'email': '...', ...}
```

## Code Architecture

### `test_keycloak_connectivity.py`

This file is intentionally written in a REPL-style to show the thought process of exploring an unknown API. It demonstrates:

- Using `.well-known/openid-configuration` to discover endpoints
- Implementing OAuth2 client credentials flow
- Making authenticated API requests

**Note**: This file doesn't include error handling by design - it's meant for exploration and learning.

### `exceptions.py`

Defines custom exception classes:

- `KeycloakError`: Base exception for all Keycloak errors
- `KeycloakAuthError`: Authentication failures
- `KeycloakAPIError`: API request failures
- `KeycloakConfigError`: Configuration errors

**Why custom exceptions?** They make error handling more specific and provide better debugging information.

### `keycloak_models.py`

Contains Pydantic Models for API responses:

- `RealmRepresentation`: Structure of a realm object
- `UserRepresentation`: Structure of a user object
- `TokenResponse`: Structure of an OAuth2 token response

**Why Pydantic?** Provides type hints and validation for API responses, improving IDE autocomplete and type checking.

### `client.py`

The core API client implementation. Key features:

- **Input validation**: Fails fast with clear errors
- **Token management**: Automatically obtains and refreshes tokens
- **Error handling**: Converts HTTP errors to custom exceptions
- **Retry logic**: Automatically retries on token expiration
- **Type hints**: Full type annotations for better IDE support

### `server.py`

The MCP server implementation. Key features:

- **Environment validation**: Checks config at startup
- **Tool definitions**: Exposes Keycloak operations as MCP tools
- **Error propagation**: Proper error messages for MCP clients
- **Comprehensive documentation**: Clear docstrings for all tools

## Common Issues and Troubleshooting

### "Missing required environment variables"

**Problem**: The `.env` file is missing or incomplete.

**Solution**: Create a `.env` file with all required variables (see `.env.example`).

### "Authentication failed"

**Problem**: Invalid client credentials or Keycloak is unreachable.

**Solutions**:
1. Verify `KEYCLOAK_URL` is correct and Keycloak is running
2. Check that `CLIENT_ID` and `CLIENT_SECRET` are correct
3. Ensure the client has "Service Account Enabled"
4. Verify the client has necessary permissions

### "Realm doesn't exist" (404 error)

**Problem**: Trying to access a non-existent realm.

**Solution**: Use `get_realms()` first to see available realms, then use the exact realm name.

### Import errors for custom modules

**Problem**: Python can't find `exceptions.py`, `types.py`, or `client.py`.

**Solution**: Make sure you're running from the project root directory.

## Extension Ideas for Students

Once you understand the basic implementation, try these challenges:

1. **Add more tools**:
   - Get roles for a realm
   - Create/update/delete users
   - Manage realm settings

2. **Improve error handling**:
   - Add retry logic with exponential backoff
   - Better error messages with suggestions

3. **Add caching**:
   - Cache realm list for X minutes
   - Cache user lookups

4. **Add async support**:
   - Convert the client to use `httpx` instead of `requests`
   - Make all methods async

5. **Add more tests**:
   - Unit tests for the client
   - Integration tests with a test Keycloak instance
   - Mock tests using `responses` library

## Resources

- [Keycloak Admin REST API Documentation](https://www.keycloak.org/docs-api/latest/rest-api/)
- [OAuth2 Client Credentials Flow](https://oauth.net/2/grant-types/client-credentials/)
- [OpenID Connect Discovery](https://openid.net/specs/openid-connect-discovery-1_0.html)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)

## License

This is educational material for student internship trials. Use freely for learning purposes.

## Questions?

If you have questions about this implementation, consider:

1. Reading the inline code comments
2. Checking the Keycloak documentation
3. Experimenting with `test_keycloak_connectivity.py`
4. Running the code with debug logging enabled
