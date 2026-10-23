export interface McpToolResult {
  content?: Array<{ type: string; text?: string }>;
  isError?: boolean;
  structuredContent?: unknown;
}

interface JsonRpcResponse<T> {
  jsonrpc: '2.0';
  id?: number;
  result?: T;
  error?: { code: number; message: string; data?: unknown };
}

interface McpTool {
  name: string;
}

const MCP_ENDPOINT = '/mcp';
const ACCEPT_HEADER = 'application/json, text/event-stream';

async function readResponse<T>(response: Response): Promise<JsonRpcResponse<T> | null> {
  if (response.status === 202 || response.status === 204) return null;

  const body = await response.text();
  if (!response.ok) {
    throw new Error(`MCP endpoint returned HTTP ${response.status}: ${body.slice(0, 300)}`);
  }
  if (!body.trim()) return null;

  const contentType = response.headers.get('content-type') ?? '';
  if (contentType.includes('text/event-stream')) {
    const messages = body
      .split(/\r?\n\r?\n/)
      .flatMap((event) =>
        event
          .split(/\r?\n/)
          .filter((line) => line.startsWith('data:'))
          .map((line) => line.slice(5).trim()),
      )
      .filter((data) => data && data !== '[DONE]')
      .map((data) => JSON.parse(data) as JsonRpcResponse<T>);
    return messages.length ? messages[messages.length - 1] : null;
  }

  return JSON.parse(body) as JsonRpcResponse<T>;
}

export async function callMcpTool(
  toolName: string,
  args: Record<string, unknown>,
): Promise<McpToolResult> {
  let sessionId: string | null = null;
  let protocolVersion = '';
  let requestId = 0;

  const post = async <T>(
    method: string,
    params?: Record<string, unknown>,
    expectsResponse = true,
  ): Promise<JsonRpcResponse<T> | null> => {
    requestId += 1;
    const headers: Record<string, string> = {
      Accept: ACCEPT_HEADER,
      'Content-Type': 'application/json',
    };
    if (sessionId) headers['Mcp-Session-Id'] = sessionId;
    if (protocolVersion) headers['Mcp-Protocol-Version'] = protocolVersion;

    const response = await fetch(MCP_ENDPOINT, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        jsonrpc: '2.0',
        ...(expectsResponse ? { id: requestId } : {}),
        method,
        ...(params ? { params } : {}),
      }),
    });
    sessionId = response.headers.get('mcp-session-id') ?? sessionId;

    const message = await readResponse<T>(response);
    if (message?.error) {
      throw new Error(`MCP ${method} failed: ${message.error.message}`);
    }
    return message;
  };

  try {
    const initialized = await post<{
      protocolVersion: string;
      capabilities: Record<string, unknown>;
      serverInfo: { name: string; version: string };
    }>('initialize', {
      protocolVersion: '2025-11-25',
      capabilities: {},
      clientInfo: { name: 'greencode-dashboard', version: '2.0.1' },
    });

    const negotiatedVersion = initialized?.result?.protocolVersion;
    if (!negotiatedVersion) {
      throw new Error('MCP server did not negotiate a protocol version.');
    }
    protocolVersion = negotiatedVersion;

    await post('notifications/initialized', undefined, false);

    const listedTools = await post<{ tools: McpTool[] }>('tools/list');
    const availableTools = listedTools?.result?.tools ?? [];
    if (!availableTools.some((tool) => tool.name === toolName)) {
      throw new Error(`MCP server does not expose the "${toolName}" tool.`);
    }

    const called = await post<McpToolResult>('tools/call', {
      name: toolName,
      arguments: args,
    });
    const result = called?.result;
    if (!result) throw new Error(`MCP server returned no result for "${toolName}".`);
    if (result.isError) {
      const detail = result.content?.map((item) => item.text).filter(Boolean).join('\n');
      throw new Error(detail || `MCP tool "${toolName}" reported an error.`);
    }
    return result;
  } finally {
    if (sessionId) {
      const headers: Record<string, string> = {};
      headers['Mcp-Session-Id'] = sessionId;
      if (protocolVersion) headers['Mcp-Protocol-Version'] = protocolVersion;
      const response = await fetch(MCP_ENDPOINT, { method: 'DELETE', headers });
      if (!response.ok && response.status !== 404 && response.status !== 405) {
        const detail = await response.text();
        throw new Error(
          `MCP tool call finished, but closing its session failed with HTTP ${response.status}: ${detail.slice(0, 200)}`,
        );
      }
    }
  }
}
