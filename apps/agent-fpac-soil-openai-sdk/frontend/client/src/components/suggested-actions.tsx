import { motion } from 'framer-motion';
import { memo } from 'react';
import type { UseChatHelpers } from '@ai-sdk/react';
import type { VisibilityType } from './visibility-selector';
import type { ChatMessage } from '@databricks/chatbot-core';
import { Suggestion } from './elements/suggestion';
import { LightbulbIcon } from '@/components/icons';
import { softNavigateToChatId } from '@/lib/navigation';
import { useAppConfig } from '@/contexts/AppConfigContext';

interface SuggestedActionsProps {
  chatId: string;
  sendMessage: UseChatHelpers<ChatMessage>['sendMessage'];
  selectedVisibilityType: VisibilityType;
}

// Starter prompts for the common FPPA workflows. Each `caseId` names the case in
// eval/prompt_test_cases.json whose user_prompt it reuses (verbatim unless noted),
// so a click reproduces an eval case by hand. Coordinates are the cases' synthetic
// Iowa examples. Prompts do not name MCP tools (system prompt rule).
const SUGGESTED_PROMPTS: ReadonlyArray<{ label: string; prompt: string; caseId?: string }> = [
  {
    label: 'Check one location',
    caseId: 'POINT-01',
    prompt:
      'What is the USDA soil map unit, farmland classification, and FPPA status at latitude 41.8781, longitude -93.0977 (Marshall County, IA)?',
  },
  {
    label: 'Screen my map AOI',
    // Map workflow (ADR 0016): uses the AOI attached from the map panel.
    prompt:
      'Screen the AOI attached from the map for FPPA farmland and give me the acreage by farmland class.',
  },
  {
    label: 'Analyze a parcel',
    caseId: 'POLY-01',
    prompt:
      'Analyze the farmland classification and acreage breakdown for this proposed solar farm parcel in Story County, IA: {"type": "Polygon", "coordinates": [[[-93.65, 42.02], [-93.63, 42.02], [-93.63, 42.04], [-93.65, 42.04], [-93.65, 42.02]]]}. Please include NCCPI crop productivity index ratings and check for Census 2020 urban area overlap.',
  },
  {
    label: 'Urban area exemption',
    caseId: 'URBAN-01',
    prompt:
      'Screen this commercial project site in Des Moines, IA against Census 2020 Urban Area boundaries (Layer 0) to check if it qualifies for an FPPA statutory exemption under 7 CFR § 658.2(a): POLYGON((-93.62 41.58, -93.60 41.58, -93.60 41.60, -93.62 41.60, -93.62 41.58))',
  },
  {
    label: 'Preliminary LESA (AD-1006)',
    caseId: 'LESA-02',
    prompt:
      'Perform a complete preliminary Form AD-1006 LESA calculation for a proposed 45-acre regional medical clinic in Story County, IA: POLYGON((-93.58 42.01, -93.57555 42.01, -93.57555 42.01445, -93.58 42.01445, -93.58 42.01)). Use national NCCPI as the productivity index and evaluate whether comprehensive site assessment scoring requires consideration of alternative non-farmland sites.',
  },
  {
    label: 'Transmission line corridor',
    caseId: 'CORR-01',
    prompt:
      'Perform a complete FPPA corridor screening and Form NRCS-CPA-106 LESA evaluation for a proposed 230kV transmission line: Centerline: LINESTRING(-93.62 42.02, -93.55 42.08, -93.45 42.15), Corridor Width: Buffer 75 feet on each side (150-ft total right-of-way), Indirect Staging Yard: POLYGON((-93.56 42.07, -93.54 42.07, -93.54 42.09, -93.56 42.09, -93.56 42.07)), Site Assessment Inputs: Project farm tract size is 350 acres. Please partition by county, query NASS agricultural statistics, apply 7 CFR § 658.5(c) corridor rules, and evaluate whether the total LESA score exceeds 160 points.',
  },
  {
    label: 'Crop productivity by map unit',
    caseId: 'INTERP-01',
    prompt:
      'Retrieve the component-weighted National Commodity Crop Productivity Index (NCCPI v3) ratings for SSURGO map unit keys 412850, 412851, and 413100.',
  },
  {
    label: 'Screening vs. LESA',
    // DISC-01 without the tool name.
    caseId: 'DISC-01',
    prompt:
      'Explain the difference between preliminary SDA soil screening under 7 CFR Part 657 and a formal FPPA LESA determination or Form AD-1006 / NRCS-CPA-106 under 7 CFR Part 658.',
  },
];

function PureSuggestedActions({ chatId, sendMessage }: SuggestedActionsProps) {
  const { chatHistoryEnabled } = useAppConfig();

  return (
    <div
      data-testid="suggested-actions"
      className="grid w-full gap-x-4 sm:grid-cols-2"
    >
      {SUGGESTED_PROMPTS.map(({ label, prompt, caseId }, index) => (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 20 }}
          transition={{ delay: 0.05 * index }}
          key={label}
          className="border-b border-border"
        >
          <Suggestion
            suggestion={prompt}
            title={prompt}
            data-case-id={caseId}
            variant="tertiary"
            onClick={(suggestion) => {
              softNavigateToChatId(chatId, chatHistoryEnabled);
              sendMessage({
                role: 'user',
                parts: [{ type: 'text', text: suggestion }],
              });
            }}
            className="h-auto w-full items-start justify-start gap-2 whitespace-normal rounded-none border-0 bg-transparent py-2 pl-0 text-left text-sm font-normal text-muted-foreground hover:bg-transparent hover:text-foreground"
          >
            <LightbulbIcon size={16} className="mt-0.5 shrink-0 text-muted-foreground" aria-hidden />
            <span className="flex min-w-0 flex-col">
              <span className="font-medium text-foreground">{label}</span>
              <span className="line-clamp-2 text-xs">{prompt}</span>
            </span>
          </Suggestion>
        </motion.div>
      ))}
    </div>
  );
}

export const SuggestedActions = memo(
  PureSuggestedActions,
  (prevProps, nextProps) => {
    if (prevProps.chatId !== nextProps.chatId) return false;
    if (prevProps.selectedVisibilityType !== nextProps.selectedVisibilityType)
      return false;

    return true;
  },
);