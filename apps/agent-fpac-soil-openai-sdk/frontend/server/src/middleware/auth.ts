import type { Request, Response, NextFunction } from 'express';
import { getAuthSession, type AuthSession } from '@databricks/chatbot-auth';
import { checkChatAccess } from '@databricks/chatbot-core';
import { ChatSDKError } from '@databricks/chatbot-core/errors';

// Extend Express Request type to include session
declare global {
  namespace Express {
    interface Request {
      session?: AuthSession;
    }
  }
}

export function localDevSession(
  enabled: boolean,
  remoteAddress: string | undefined,
): AuthSession | undefined {
  if (
    !enabled ||
    !['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(remoteAddress ?? '')
  ) {
    return undefined;
  }
  return {
    user: {
      id: 'local-dev-user',
      email: 'local-dev@localhost',
      name: 'Local Development User',
      preferredUsername: 'local-dev',
      type: 'regular',
    },
  };
}

/**
 * Middleware to authenticate requests and attach session to request object
 */
export async function authMiddleware(
  req: Request,
  _res: Response,
  next: NextFunction,
) {
  const session = localDevSession(
    process.env.FPAC_LOCAL_DEV === '1',
    req.socket.remoteAddress,
  );
  if (session) {
    req.session = session;
    return next();
  }

  try {
    const session = await getAuthSession({
      getRequestHeader: (name: string) =>
        req.headers[name.toLowerCase()] as string | null,
    });
    req.session = session || undefined;
    next();
  } catch (error) {
    console.error('Auth middleware error:', error);
    next(error);
  }
}

/**
 * Middleware to require authentication - returns 401 if no session
 */
export function requireAuth(req: Request, res: Response, next: NextFunction) {
  if (!req.session?.user) {
    const response = new ChatSDKError('unauthorized:chat').toResponse();
    return res.status(response.status).json(response.json);
  }
  next();
}

export async function requireChatAccess(
  req: Request,
  res: Response,
  next: NextFunction,
) {
  const id = getIdFromRequest(req);
  if (!id) {
    console.error(
      'Chat access middleware error: no chat ID provided',
      req.params,
    );
    const error = new ChatSDKError('bad_request:api');
    const response = error.toResponse();
    return res.status(response.status).json(response.json);
  }
  const { allowed, reason } = await checkChatAccess(id, req.session?.user.id);
  if (!allowed) {
    console.error(
      'Chat access middleware error: user does not have access to chat',
      reason,
    );
    const error = new ChatSDKError('forbidden:chat', reason);
    const response = error.toResponse();
    return res.status(response.status).json(response.json);
  }
  next();
}

export const getIdFromRequest = (req: Request): string | undefined => {
  const { id } = req.params;
  if (!id) return undefined;
  return typeof id === 'string' ? id : id[0];
};
