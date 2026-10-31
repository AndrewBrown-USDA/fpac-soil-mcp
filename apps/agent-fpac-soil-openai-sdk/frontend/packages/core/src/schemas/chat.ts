import { z } from 'zod';

const textPartSchema = z.object({
  type: z.enum(['text']),
  text: z.string().min(1),
});

const filePartSchema = z.object({
  type: z.enum(['file']),
  mediaType: z.enum(['image/jpeg', 'image/png']),
  name: z.string().min(1),
  url: z.string().url(),
});

const partSchema = z.union([textPartSchema, filePartSchema]);

// Schema for previous messages in ephemeral mode
// More permissive to handle various message types (user, assistant, tool calls, etc.)
const previousMessageSchema = z.object({
  // Accept any string ID: user messages have UUIDs, but assistant messages
  // from the AI SDK use nanoid (16-char alphanumeric), not UUIDs.
  id: z.string(),
  role: z.enum(['user', 'assistant', 'system']),
  parts: z.array(z.any()), // Permissive to handle text, tool calls, tool results
});

// Map AOI attached to the conversation (ADR 0016), sent with each turn. Bounded like
// the agent's own check; an invalid value is dropped so the chat turn still runs.
const MAX_ACTIVE_AOI_GEOMETRY_CHARS = 256 * 1024;
const activeAoiSchema = z
  .object({
    aoi_ref: z.string().regex(/^aoi-[0-9a-f]{8}$/),
    geometry: z.object({
      type: z.enum(['Polygon', 'MultiPolygon']),
      coordinates: z.array(z.any()),
    }),
    summary: z.record(z.string(), z.unknown()).nullable().optional(),
  })
  .refine(
    (aoi) => JSON.stringify(aoi.geometry).length <= MAX_ACTIVE_AOI_GEOMETRY_CHARS,
  );

export const postRequestBodySchema = z.object({
  id: z.string().uuid(),
  // Optional for continuation/regeneration scenarios (no new user message)
  message: z
    .object({
      id: z.string().uuid(),
      role: z.enum(['user']),
      parts: z.array(partSchema),
    })
    .optional(),
  selectedChatModel: z.enum(['chat-model', 'chat-model-reasoning']),
  selectedVisibilityType: z.enum(['public', 'private']),
  // Optional field for ephemeral mode: frontend sends previous conversation history
  previousMessages: z.array(previousMessageSchema).optional(),
  activeAoi: activeAoiSchema.optional().catch(undefined),
});

export type PostRequestBody = z.infer<typeof postRequestBodySchema>;
