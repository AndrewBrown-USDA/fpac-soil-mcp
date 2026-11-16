import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { RESULT_CARD } from './map/ScreeningResults';

type SiteAssessmentBand = {
  id: string;
  label: string;
  points: number | null;
  min?: number;
  max?: number;
};

export type SiteAssessmentAnswer = {
  type: 'site_assessment_answer';
  criterion_number: number;
  answer_state: 'answered' | 'unknown' | 'skipped';
  answer: string | number | null;
  selected_band: SiteAssessmentBand | null;
  points: number | null;
  evidence: string;
  comment: string;
  provenance: 'user' | 'agent' | 'tool';
  is_verified?: boolean;
  source_provenance?: string[];
  justification?: string;
};

export type SiteAssessmentQuestion = {
  criterion_number: number;
  name: string;
  question: string;
  citation: string;
  answer_type: string;
  choices: SiteAssessmentBand[];
  max_points: number;
  requires_rationale?: boolean;
  requires_verification?: boolean;
  range_convention?: string;
  evaluation_context?: string;
};

export type SiteAssessmentConfirmedSummary = {
  type: 'site_assessment_confirmed_summary';
  confirmed: true;
  answers: SiteAssessmentAnswer[];
  assumptions?: string[];
  [key: string]: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

export function parseStructuredValue(value: unknown): unknown {
  let candidate = value;
  if (typeof candidate === 'string') {
    const text = candidate.trim().replace(/^```(?:json)?\s*|\s*```$/g, '');
    try {
      candidate = JSON.parse(text);
    } catch (error) {
      if (error instanceof SyntaxError) return null;
      throw error;
    }
  }
  if (
    isRecord(candidate) &&
    typeof candidate.text === 'string' &&
    Object.keys(candidate).every((key) => key === 'text' || key === 'type')
  ) {
    return parseStructuredValue(candidate.text);
  }
  return candidate;
}

export function parseSiteAssessmentQuestion(value: unknown): SiteAssessmentQuestion | null {
  const parsed = parseStructuredValue(value);
  if (
    !isRecord(parsed) ||
    !Number.isInteger(parsed.criterion_number) ||
    typeof parsed.name !== 'string' ||
    typeof parsed.question !== 'string' ||
    typeof parsed.citation !== 'string' ||
    typeof parsed.answer_type !== 'string' ||
    !Array.isArray(parsed.choices) ||
    typeof parsed.max_points !== 'number'
  ) {
    return null;
  }
  const choices = parsed.choices.filter(
    (choice): choice is SiteAssessmentBand =>
      isRecord(choice) &&
      typeof choice.id === 'string' &&
      typeof choice.label === 'string' &&
      (typeof choice.points === 'number' || choice.points === null),
  );
  if (choices.length !== parsed.choices.length) return null;
  return { ...parsed, choices } as SiteAssessmentQuestion;
}

export function parseSiteAssessmentSummary(value: unknown): SiteAssessmentConfirmedSummary | null {
  const parsed = parseStructuredValue(value);
  if (
    !isRecord(parsed) ||
    parsed.type !== 'site_assessment_confirmed_summary' ||
    !Array.isArray(parsed.answers) ||
    !parsed.answers.every(
      (answer) => isRecord(answer) && answer.type === 'site_assessment_answer',
    )
  ) {
    return null;
  }
  return { ...parsed, confirmed: true } as SiteAssessmentConfirmedSummary;
}

export function SiteAssessmentQuestionCard({
  question,
  onRecord,
}: {
  question: SiteAssessmentQuestion;
  onRecord: (record: SiteAssessmentAnswer) => void;
}) {
  const [evidence, setEvidence] = useState('');
  const [comment, setComment] = useState('');
  const [provenance, setProvenance] = useState<SiteAssessmentAnswer['provenance']>('user');
  const [isVerified, setIsVerified] = useState(false);
  const [sourceProvenance, setSourceProvenance] = useState('');
  const [justification, setJustification] = useState('');
  const unknownBand = question.choices.find((choice) => choice.id === 'unknown') ?? null;

  const record = (
    answerState: SiteAssessmentAnswer['answer_state'],
    band: SiteAssessmentBand | null,
  ) => {
    onRecord({
      type: 'site_assessment_answer',
      criterion_number: question.criterion_number,
      answer_state: answerState,
      answer: answerState === 'answered' ? band?.id ?? null : null,
      selected_band: band,
      points: answerState === 'answered' ? band?.points ?? null : null,
      evidence,
      comment,
      provenance,
      is_verified: isVerified,
      source_provenance: sourceProvenance.split('\n').map((source) => source.trim()).filter(Boolean),
      justification,
    });
  };

  return (
    <section className={`${RESULT_CARD} grid gap-3`} data-testid="site-assessment-question">
      <header>
        <p className="text-muted-foreground text-xs">
          Criterion {question.criterion_number} · {question.answer_type} · up to {question.max_points} points
        </p>
        <h3 className="font-semibold text-base">{question.name}</h3>
        <p className="mt-1 text-sm">{question.question}</p>
        <p className="mt-1 text-muted-foreground text-xs">{question.citation}</p>
      </header>
      {(question.range_convention || question.evaluation_context) && (
        <p className="text-muted-foreground text-xs">
          {question.evaluation_context ?? question.range_convention}
        </p>
      )}
      {question.requires_rationale && (
        <p className="text-muted-foreground text-xs">A rationale is requested for this criterion.</p>
      )}
      {question.requires_verification && (
        <p className="text-muted-foreground text-xs">Verification is requested for this criterion.</p>
      )}
      <fieldset className="grid gap-2">
        <legend className="font-medium text-sm">Choose a resource-defined band</legend>
        {question.choices
          .filter((choice) => choice.id !== 'unknown')
          .map((choice) => (
            <Button
              key={choice.id}
              type="button"
              variant="outline"
              className="h-auto justify-between whitespace-normal py-2 text-left"
              onClick={() => record('answered', choice)}
              data-testid={`site-assessment-band-${choice.id}`}
            >
              <span>{choice.label}</span>
              <span className="shrink-0 text-muted-foreground">
                {choice.points === null ? 'No points assigned' : `${choice.points} points`}
              </span>
            </Button>
          ))}
      </fieldset>
      <div className="grid gap-2 sm:grid-cols-2">
        <label className="grid gap-1 text-xs">
          Evidence (optional)
          <textarea
            className="min-h-16 rounded-md border border-input bg-background p-2 text-sm"
            value={evidence}
            onChange={(event) => setEvidence(event.target.value)}
            data-testid="site-assessment-evidence"
          />
        </label>
        <label className="grid gap-1 text-xs">
          Comment (optional)
          <textarea
            className="min-h-16 rounded-md border border-input bg-background p-2 text-sm"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            data-testid="site-assessment-comment"
          />
        </label>
      </div>
      <label className="grid max-w-xs gap-1 text-xs">
        Provenance
        <select
          className="h-8 rounded-md border border-input bg-background px-2 text-sm"
          value={provenance}
          onChange={(event) => setProvenance(event.target.value as SiteAssessmentAnswer['provenance'])}
          data-testid="site-assessment-provenance"
        >
          <option value="user">User-provided</option>
          <option value="agent">Agent-provided</option>
          <option value="tool">Tool-provided</option>
        </select>
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={isVerified}
          onChange={(event) => setIsVerified(event.target.checked)}
          data-testid="site-assessment-verified"
        />
        Verified against the cited source
      </label>
      <label className="grid gap-1 text-xs">
        Source provenance (one source per line)
        <textarea
          className="min-h-16 rounded-md border border-input bg-background p-2 text-sm"
          value={sourceProvenance}
          onChange={(event) => setSourceProvenance(event.target.value)}
          data-testid="site-assessment-source-provenance"
        />
      </label>
      <label className="grid gap-1 text-xs">
        Justification
        <textarea
          className="min-h-16 rounded-md border border-input bg-background p-2 text-sm"
          value={justification}
          onChange={(event) => setJustification(event.target.value)}
          data-testid="site-assessment-justification"
        />
      </label>
      <div className="flex flex-wrap gap-2 border-t border-border pt-3">
        <Button type="button" variant="outline" onClick={() => record('unknown', unknownBand)}>
          Unknown / unavailable
        </Button>
        <Button type="button" variant="outline" onClick={() => record('skipped', null)}>
          Skip this criterion
        </Button>
      </div>
      <p className="text-muted-foreground text-xs">
        Preliminary screening only; this is not an official FPPA determination or completed federal form.
      </p>
    </section>
  );
}

export function SiteAssessmentSummaryCard({
  summary,
  onConfirm,
  onEdit,
}: {
  summary: SiteAssessmentConfirmedSummary;
  onConfirm: (record: SiteAssessmentConfirmedSummary) => void;
  onEdit: () => void;
}) {
  return (
    <section className={`${RESULT_CARD} grid gap-3`} data-testid="site-assessment-summary">
      <div>
        <h3 className="font-semibold text-base">Review Site Assessment answers</h3>
        <p className="text-muted-foreground text-xs">
          Confirm these preliminary interview records before they are used.
        </p>
      </div>
      {summary.answers.map((answer, index) => (
        <article className="border-b border-border pb-2 last:border-b-0" key={`${answer.criterion_number}-${index}`}>
          <h4 className="font-medium text-sm">Criterion {answer.criterion_number}</h4>
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
            <dt className="text-muted-foreground">Response</dt>
            <dd>{answer.answer_state === 'answered' ? answer.selected_band?.label ?? String(answer.answer) : answer.answer_state}</dd>
            <dt className="text-muted-foreground">Points</dt>
            <dd>{answer.points === null ? 'Not assigned' : answer.points}</dd>
            <dt className="text-muted-foreground">Evidence</dt>
            <dd>{answer.evidence || 'None provided'}</dd>
            <dt className="text-muted-foreground">Comment</dt>
            <dd>{answer.comment || 'None provided'}</dd>
            <dt className="text-muted-foreground">Provenance</dt>
            <dd>{answer.provenance}</dd>
          </dl>
        </article>
      ))}
      {summary.assumptions && summary.assumptions.length > 0 && (
        <div data-testid="site-assessment-assumptions">
          <h4 className="font-medium text-sm">Assumptions</h4>
          <ul className="list-disc pl-5 text-xs">
            {summary.assumptions.map((assumption, index) => (
              <li key={`${index}-${assumption}`}>{assumption}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex gap-2 border-t border-border pt-3">
        <Button type="button" onClick={() => onConfirm({ ...summary, confirmed: true })}>
          Confirm
        </Button>
        <Button type="button" variant="outline" onClick={onEdit}>Edit</Button>
      </div>
      <p className="text-muted-foreground text-xs">
        Preliminary information only; this confirmation is not an official FPPA determination.
      </p>
    </section>
  );
}
