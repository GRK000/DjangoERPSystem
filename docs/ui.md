# Aurora Ops UI

## Modes

- Night Ops: dark cockpit-style command center.
- Day Ops: light operational command center with strong contrast and Aurora accents.
- Command: richer dashboard density.
- Operator: compact operational density for repeated work.

Theme and density are independent:

```text
aurora-theme = dark | light
aurora-density-mode = command | operator
```

Both are stored in `localStorage` and applied to `document.documentElement.dataset`.

## Day Ops Tokens

Main tokens:

- Background: `#F5F8FC`, `#EEF4FA`
- Surface: `#FFFFFF`, `#F8FAFC`
- Border: `#CBD5E1`, `#94A3B8`
- Text: `#0B1220`, `#1E293B`, `#475569`
- Primary: `#0E7490`
- Secondary: `#7C3AED`
- Success: `#166534` on `#F0FDF4`
- Warning: `#B45309` on `#FFFBEB`
- Danger: `#BE123C` on `#FFF1F2`
- Info: `#0369A1` on `#EFF6FF`

## Visual Capture Checklist

Capture these screens before publishing the portfolio:

- Night Ops + Command: dashboard.
- Night Ops + Operator: preparation or stock table.
- Day Ops + Command: dashboard.
- Day Ops + Operator: compact table view.
- Consulta / Aurora Operator conversation.
- Agent Runs staff traceability panel.

Suggested asset paths:

- `docs/assets/night-ops-dashboard.png`
- `docs/assets/day-ops-dashboard.png`
- `docs/assets/aurora-operator.png`
- `docs/assets/agent-runs.png`

## Review Checklist

- Text contrast is readable in both themes.
- Chips and badges remain visible in Day Ops.
- Search placeholder and input borders are visible.
- Focus states are visible by keyboard.
- Sidebar active item is clear.
- Primary and secondary buttons are distinguishable.
- Tables remain legible in Operator mode.
- User and Aurora Operator messages are visually distinct.
- Evidence/tools panels are not shown empty.
- Mock-mode warnings are readable.
- Day Ops does not use bright cyan as small text on white.

## Accessibility Notes

- Normal text avoids bright cyan on white.
- Inputs have visible borders and focus rings.
- Badges keep text labels, not color-only status.
- Agent messages, evidence boxes and warning states use strong text contrast.
- Day Ops avoids full-screen pure white backgrounds.
