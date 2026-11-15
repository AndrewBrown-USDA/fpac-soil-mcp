/**
 * Exportable subset of a current chat message. Call these serializers only
 * after an explicit user export action: tool inputs and outputs can contain
 * sensitive coordinates or other sensitive data.
 */
export type ChatExportPart =
  | { type: 'text'; text?: string }
  | {
      type: 'tool';
      toolName?: string;
      input?: unknown;
      output?: unknown;
      state?: string;
    };

export type ChatExportMessage = {
  role: 'user' | 'assistant';
  parts?: ChatExportPart[];
};

export type ChatExportRecord = {
  role: 'user' | 'assistant';
  text?: string;
  tools?: Array<{
    name?: string;
    input?: unknown;
    output?: unknown;
    state?: string;
  }>;
};

/** Warning for the UI integration: exports may contain raw tool data and sensitive coordinates. */
export const CHAT_EXPORT_SENSITIVITY_WARNING =
  'Exports may include raw tool data and sensitive coordinates. Review the contents before saving or sharing.';

function stableValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, nested]) => [key, stableValue(nested)]),
    );
  }
  return value;
}

/** Extract only user-visible text and raw tool fields from the supplied chat messages. */
export function getChatExportRecords(
  messages: readonly ChatExportMessage[] = [],
): ChatExportRecord[] {
  return messages.map(({ role, parts }) => {
    const text = (parts ?? [])
      .filter((part): part is Extract<ChatExportPart, { type: 'text' }> => part.type === 'text')
      .map((part) => part.text)
      .filter((value): value is string => typeof value === 'string')
      .join('\n');
    const tools = (parts ?? [])
      .filter((part): part is Extract<ChatExportPart, { type: 'tool' }> => part.type === 'tool')
      .map(({ toolName, input, output, state }) => ({
        ...(toolName === undefined ? {} : { name: toolName }),
        ...(input === undefined ? {} : { input: stableValue(input) }),
        ...(output === undefined ? {} : { output: stableValue(output) }),
        ...(state === undefined ? {} : { state }),
      }));
    return {
      role,
      ...(text ? { text } : {}),
      ...(tools.length ? { tools } : {}),
    };
  });
}

/** Serialize current-chat export records as stable, pretty-printed JSON. */
export function serializeChatExportJson(messages: readonly ChatExportMessage[] = []): string {
  return JSON.stringify(getChatExportRecords(messages), null, 2);
}

/** Serialize current-chat export records as Markdown with stable tool JSON blocks. */
export function serializeChatExportMarkdown(messages: readonly ChatExportMessage[] = []): string {
  return getChatExportRecords(messages)
    .map((message) => {
      const sections = [`## ${message.role === 'user' ? 'User' : 'Assistant'}`];
      if (message.text !== undefined) sections.push(message.text);
      for (const tool of message.tools ?? []) {
        sections.push(`### Tool${tool.name ? `: ${tool.name}` : ''}`);
        if (tool.state !== undefined) sections.push(`State: ${tool.state}`);
        if (tool.input !== undefined) {
          sections.push(`Input:\n\`\`\`json\n${JSON.stringify(tool.input, null, 2)}\n\`\`\``);
        }
        if (tool.output !== undefined) {
          sections.push(`Output:\n\`\`\`json\n${JSON.stringify(tool.output, null, 2)}\n\`\`\``);
        }
      }
      return sections.join('\n\n');
    })
    .join('\n\n');
}
