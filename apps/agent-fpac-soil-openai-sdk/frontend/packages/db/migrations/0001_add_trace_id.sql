-- Migration: Add traceId column to Message for MLflow trace linkage
ALTER TABLE "ai_chatbot"."Message" ADD COLUMN IF NOT EXISTS "traceId" text;
