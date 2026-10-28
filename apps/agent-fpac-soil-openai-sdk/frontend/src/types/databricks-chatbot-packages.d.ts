declare module '@databricks/chatbot-auth' {
  export interface ClientSession {
    user?: {
      email: string;
      name: string;
      image?: string | null;
      preferredUsername?: string | null;
      [key: string]: unknown;
    } | null;
    expires?: string | null;
    [key: string]: unknown;
  }
}

declare module '@databricks/chatbot-core' {
  export type VisibilityType = 'private' | 'public';
  export type ErrorCode = string;
  export type Attachment = any;
  export type Feedback = any;
  export type FeedbackMap = Record<string, any>;
  export type CustomUIDataTypes = any;
  export type ChatTools = any;
  export type ChatMessage = any;
  export type ChatPart = any;
}

declare module '@databricks/chatbot-core/errors' {
  export type ErrorCode = string;

  export class ChatSDKError extends Error {
    code: ErrorCode;
    cause?: unknown;
    constructor(code: ErrorCode, cause?: unknown);
  }
}

declare module '@databricks/chatbot-db' {
  export type Chat = any;
  export type DBMessage = any;
}

declare module 'react-syntax-highlighter';
declare module 'react-syntax-highlighter/dist/esm/styles/prism';
