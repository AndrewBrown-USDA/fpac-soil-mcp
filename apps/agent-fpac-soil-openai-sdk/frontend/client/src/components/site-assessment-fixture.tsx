import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  SiteAssessmentQuestionCard,
  SiteAssessmentSummaryCard,
} from './site-assessment-cards';
import type {
  SiteAssessmentAnswer,
  SiteAssessmentConfirmedSummary,
  SiteAssessmentQuestion,
} from './site-assessment-cards';
import { ActiveAoiProvider, useActiveAoi } from './map/ActiveAoiContext';
import type { PolygonGeometry } from './map/geojson';
import { MapResultProvider, useMapResult } from './map/MapResultContext';
import { ShowOnMapButton } from './map/ShowOnMapButton';

const question: SiteAssessmentQuestion = {
  criterion_number: 1,
  name: 'Nonurban land within one mile',
  question: 'What percentage of land within a one-mile radius is in nonurban use?',
  citation: '7 CFR § 658.5(b)(1)',
  answer_type: 'percentage',
  max_points: 15,
  requires_verification: true,
  range_convention: 'Resource-defined representative intervals.',
  choices: [
    { id: 'unknown', label: 'Unknown or unavailable', points: null },
    { id: 'range_20_90_1', label: '20% to 25% representative interval', min: 20, max: 25, points: 1 },
  ],
};

const answer: SiteAssessmentAnswer = {
  type: 'site_assessment_answer',
  criterion_number: 1,
  answer_state: 'answered',
  answer: 'range_20_90_1',
  selected_band: question.choices[1],
  points: 1,
  evidence: 'Sample evidence',
  comment: 'Sample comment',
  provenance: 'user',
  is_verified: true,
  source_provenance: ['Sample source'],
  justification: 'Sample justification',
};

const summary: SiteAssessmentConfirmedSummary = {
  type: 'site_assessment_confirmed_summary',
  confirmed: true,
  answers: [answer],
  assumptions: ['Criterion 2: assumed (no evidence)'],
};

const cdlOutput = {
  status: 'ok',
  product_vintage: '2025',
  vintage_verified: true,
  aoi: null,
  one_mile_ring: null,
  thirty_meter_band: null,
  limitations: ['Preliminary land-cover context only.'],
  error_message: null,
};

const firstGeometry: PolygonGeometry = {
  type: 'Polygon',
  coordinates: [[[-98, 39], [-97.99, 39], [-97.99, 39.01], [-98, 39.01], [-98, 39]]],
};
const replacementGeometry: PolygonGeometry = {
  type: 'Polygon',
  coordinates: [[[-97, 38], [-96.99, 38], [-96.99, 38.01], [-97, 38.01], [-97, 38]]],
};

function MapFixture() {
  const { activeAoi, setGeometry, detach } = useActiveAoi();
  const { shown, clear } = useMapResult();
  const [resultAoiRef, setResultAoiRef] = useState<string | null>(null);
  useEffect(() => {
    if (activeAoi && !resultAoiRef) setResultAoiRef(activeAoi.aoi_ref);
  }, [activeAoi, resultAoiRef]);
  return (
    <section>
      <button type="button" onClick={() => setGeometry(firstGeometry)}>Attach AOI</button>
      <button type="button" onClick={() => setGeometry(replacementGeometry)}>Replace AOI</button>
      <button type="button" onClick={detach}>Detach AOI</button>
      <button type="button" onClick={clear}>Clear map result</button>
      {resultAoiRef && (
        <ShowOnMapButton
          tool="analyze_cdl_context"
          toolCallId="fixture-cdl-call"
          input={{ aoi_ref: resultAoiRef }}
          output={cdlOutput}
        />
      )}
      <pre data-testid="map-result">{shown ? JSON.stringify(shown) : 'empty'}</pre>
    </section>
  );
}

function Fixture() {
  const [emitted, setEmitted] = useState<unknown>(null);
  const [editing, setEditing] = useState(false);
  return (
    <main>
      <SiteAssessmentQuestionCard question={question} onRecord={setEmitted} />
      <SiteAssessmentSummaryCard
        summary={summary}
        onConfirm={setEmitted}
        onEdit={() => setEditing(true)}
      />
      <output data-testid="emitted-record">{emitted ? JSON.stringify(emitted) : ''}</output>
      {editing && <p data-testid="editing">Editing answers</p>}
      <ActiveAoiProvider>
        <MapResultProvider>
          <MapFixture />
        </MapResultProvider>
      </ActiveAoiProvider>
    </main>
  );
}

const root = document.getElementById('root');
if (!root) throw new Error('Fixture root element is missing.');
createRoot(root).render(<Fixture />);
