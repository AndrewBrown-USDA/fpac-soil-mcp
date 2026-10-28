export type ErrorCode = string;

export class ChatSDKError extends Error {
  code: ErrorCode;

  constructor(code: ErrorCode, cause?: unknown) {
    super(typeof cause === 'string' ? cause : code);
    this.name = 'ChatSDKError';
    this.code = code;
    this.cause = cause;
  }
}
