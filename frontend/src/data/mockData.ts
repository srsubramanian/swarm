import type { Conversation } from '../types';

export const mockConversations: Conversation[] = [
  {
    id: 'wire_cyprus',
    title: 'Outbound Wire — Cyprus',
    clientName: 'Meridian Capital Partners',
    riskLevel: 'critical',
    status: 'awaiting_decision',
    eventType: 'Wire Transfer',
    startedAt: '2026-03-01T14:23:00Z',
    messageCount: 4,
    agents: [
      {
        role: 'compliance',
        name: 'Compliance Agent',
        status: 'complete',
        position: 'HOLD — AML red flags, beneficial ownership concerns',
      },
      {
        role: 'security',
        name: 'Security Agent',
        status: 'complete',
        position: 'HOLD — Authorization anomalies, IP geolocation mismatch',
      },
      {
        role: 'engineering',
        name: 'Engineering Agent',
        status: 'complete',
        position: 'REVIEW — API valid but behavioral anomaly detected',
      },
    ],
    messages: [
      {
        id: 'msg_1',
        agentRole: 'compliance',
        agentName: 'Compliance Agent',
        content:
          '**Flagging AML concerns** on this $2.4M outbound wire to First Mediterranean Bank, Limassol.\n\n• Beneficiary `Aegean Maritime Holdings Ltd` has no prior transaction history with this client\n• Cyprus is a **high-risk jurisdiction** per our enhanced due diligence matrix\n• Beneficial ownership of receiving entity is opaque — corporate registry shows nominee directors\n• Transaction exceeds the client\'s typical wire pattern by 340%\n\n@security Can you confirm the authorization chain? @engineering Any API anomalies on the origination?',
        timestamp: '2026-03-01T14:23:15Z',
      },
      {
        id: 'msg_2',
        agentRole: 'security',
        agentName: 'Security Agent',
        content:
          'Authorization review complete. Several concerns:\n\n• Wire initiated from IP `185.243.xx.xx` — geolocated to **Bucharest, Romania**, not the client\'s usual NYC/London pattern\n• Session was authenticated via SSO at 03:47 UTC — outside normal business hours\n• The session token shows a device fingerprint we haven\'t seen before\n• No MFA challenge was triggered — the auth policy exemption for high-value wires appears misconfigured\n\n@compliance Concur on beneficial ownership red flags. The receiving jurisdiction plus origination anomaly is a significant combined risk.',
        timestamp: '2026-03-01T14:23:42Z',
      },
      {
        id: 'msg_3',
        agentRole: 'engineering',
        agentName: 'Engineering Agent',
        content:
          'Technical analysis of the transaction pipeline:\n\n• API call originated from the client\'s registered application (`app_id: mcp-7291`)\n• Request payload structure matches their standard wire template — no injection or tampering detected\n• However, the `metadata.purpose_code` field is set to `TRADE` which conflicts with the memo field stating \'consulting services\'\n• Transaction velocity: this is the 3rd wire >$1M in 72 hours — previous two went to Malta and BVI respectively\n\nThe API patterns are technically valid but the behavioral anomaly warrants review.',
        timestamp: '2026-03-01T14:24:08Z',
      },
    ],
    moderatorSummary: {
      status: 'All three agents recommend HOLD',
      consensus:
        'Unanimous concern across compliance, security, and engineering. The combination of jurisdictional risk, authorization anomalies, and behavioral deviation creates a compelling case for enhanced scrutiny.',
      keyDecisions: [
        'Compliance: Beneficial ownership verification required before release',
        'Security: Auth policy misconfiguration needs immediate remediation',
        'Engineering: Purpose code mismatch needs client clarification',
      ],
      riskAssessment:
        'Critical — Multiple independent risk signals converging. This is not a single-factor flag.',
      nextSteps: [
        'Place wire on regulatory hold (48-hour window)',
        'Initiate enhanced due diligence on Aegean Maritime Holdings',
        'Request client callback to verify wire intent and clarify purpose code',
        'Remediate MFA exemption policy for high-value transactions',
        'File preliminary SAR if client cannot satisfactorily explain within 24 hours',
      ],
    },
    actionRequired: {
      status: 'pending',
      options: [
        { id: 'hold', label: 'Hold Transfer', variant: 'danger' },
        {
          id: 'approve_conditions',
          label: 'Approve with Conditions',
          variant: 'secondary',
        },
        { id: 'escalate', label: 'Escalate to BSA Officer', variant: 'primary' },
      ],
    },
    clientMemory: {
      clientName: 'Meridian Capital Partners',
      content:
        '## Meridian Capital Partners\n**Relationship since:** 2019 | **Tier:** Institutional | **RM:** Sarah Chen\n\n### Known Patterns\n- Primary corridors: NYC ↔ London, occasional Singapore\n- Typical wire range: $100K–$500K\n- Monthly volume: 12–18 wires averaging $3.2M total\n\n### Risk History\n- **2024-03:** Flagged for $800K wire to Cayman Islands — cleared after documentation review\n- **2024-09:** Enhanced due diligence completed — satisfactory\n- **2025-01:** New signatory added (James Chen, CFO) — verified\n\n### Notes\n- Client is a PE fund focused on maritime logistics\n- Recent expansion into Mediterranean shipping routes may explain new jurisdictional patterns\n- Annual review due in Q2 2026',
      lastUpdated: '2026-02-15T10:00:00Z',
    },
  },
  {
    id: 'velocity_quantum',
    title: 'Velocity Anomaly — Batch Processing',
    clientName: 'Quantum Dynamics LLC',
    riskLevel: 'high',
    status: 'awaiting_decision',
    eventType: 'Velocity Alert',
    startedAt: '2026-03-01T15:07:00Z',
    messageCount: 4,
    agents: [
      {
        role: 'compliance',
        name: 'Compliance Agent',
        status: 'complete',
        position:
          'VERIFY — Pattern matches layering typology on surface',
      },
      {
        role: 'security',
        name: 'Security Agent',
        status: 'complete',
        position: 'CLEAR — Legitimate automated API behavior',
      },
      {
        role: 'engineering',
        name: 'Engineering Agent',
        status: 'complete',
        position: 'CLEAR — SDK v3.0 batch payroll confirmed',
      },
    ],
    messages: [
      {
        id: 'msg_4',
        agentRole: 'compliance',
        agentName: 'Compliance Agent',
        content:
          'Reviewing the velocity anomaly for Quantum Dynamics LLC — 47 transactions totaling $3.2M in a 2-hour window.\n\n• Pattern matches **layering typology** (rapid sequential transfers with incrementing amounts)\n• Individual amounts stay below the $10K CTR threshold — classic structuring indicator\n• However, @engineering notes this client recently upgraded their API integration\n• Previous compliance review (6 months ago) cleared them for batch processing up to 100 tx/day\n\nNeed @engineering to confirm whether this matches their new integration pattern.',
        timestamp: '2026-03-01T15:07:22Z',
      },
      {
        id: 'msg_5',
        agentRole: 'security',
        agentName: 'Security Agent',
        content:
          'Automated behavior analysis:\n\n• All 47 transactions originate from the same authenticated session with consistent device fingerprint\n• API key `qd-prod-8847` matches their registered production credentials\n• Request timing shows **precisely 2.3-second intervals** — clearly automated, not human-initiated\n• TLS certificate chain validates; no MITM indicators\n• Rate limiting was not triggered — their tier allows 60 req/min\n\nThis appears to be legitimate API automation, not credential compromise. The regularity actually makes it **less suspicious** from a security standpoint — attackers typically add jitter.',
        timestamp: '2026-03-01T15:07:51Z',
      },
      {
        id: 'msg_6',
        agentRole: 'engineering',
        agentName: 'Engineering Agent',
        content:
          'Confirmed — Quantum Dynamics pushed a new version of their payment processing service last Tuesday.\n\n• Their SDK was updated from `v2.1` to `v3.0` which includes batch payment support\n• The 2.3-second interval matches the default `batchDelay` config in our SDK v3.0\n• Transaction amounts are payroll disbursements to 47 different employee accounts\n• Their staging environment showed identical patterns during integration testing last week\n• `metadata.batch_id` field is populated correctly, linking all transactions\n\nThis is a **legitimate payroll batch run** using our new SDK. The amounts are below $10K because they\'re individual salary payments, not structuring.',
        timestamp: '2026-03-01T15:08:19Z',
      },
    ],
    moderatorSummary: {
      status: 'Agents split: Engineering clears, Compliance defers to verification',
      consensus:
        'Engineering provides strong evidence this is legitimate payroll automation via the new SDK v3.0. Security concurs the technical indicators are benign. Compliance acknowledges the engineering context but notes the pattern surface-level matches structuring typologies.',
      keyDecisions: [
        'Engineering: Batch processing confirmed via SDK v3.0 upgrade',
        'Security: No credential compromise or anomalous access patterns',
        'Compliance: Recommends one-time verification to update client risk profile',
      ],
      riskAssessment:
        'Medium — Likely legitimate but first occurrence of this pattern. Client memory should be updated once verified.',
      nextSteps: [
        'Request payroll documentation from Quantum Dynamics for this batch',
        'Upon verification, update client memory with approved batch processing pattern',
        'Set velocity alert threshold to 100 tx/2hr for this client (up from default 20)',
        'No SAR filing recommended at this time',
      ],
    },
    actionRequired: {
      status: 'pending',
      options: [
        { id: 'clear', label: 'Clear Activity', variant: 'primary' },
        {
          id: 'request_docs',
          label: 'Request Documentation',
          variant: 'secondary',
        },
        { id: 'restrict', label: 'Restrict API Access', variant: 'danger' },
      ],
    },
    clientMemory: {
      clientName: 'Quantum Dynamics LLC',
      content:
        '## Quantum Dynamics LLC\n**Relationship since:** 2021 | **Tier:** Corporate | **RM:** Michael Torres\n\n### Known Patterns\n- Primarily domestic transfers\n- Payroll processing: bi-weekly, typically 30–40 transactions\n- Monthly volume: $2M–$4M\n\n### Risk History\n- **2025-06:** Velocity alert — cleared as end-of-quarter bonus payments\n- **2025-11:** API integration review — approved for SDK v2.1\n\n### Notes\n- Fast-growing fintech startup, 47 employees as of last count\n- Engineering team actively integrates with our API — frequent SDK updates\n- Expanding to international payments in 2026',
      lastUpdated: '2026-02-20T09:30:00Z',
    },
  },
];
