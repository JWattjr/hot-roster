---
name: Hot Roster
description: A music league score sheet with inspectable judgment.
colors:
  ink: "#17191c"
  stage: "#101214"
  paper: "#f5f3ed"
  white: "#fffdf8"
  muted: "#686961"
  line: "#dcdcd3"
  broadcast: "#dd4b30"
  acid: "#e6f777"
  green: "#2b633e"
typography:
  display:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "clamp(38px,3.6vw,58px)"
    fontWeight: 700
    lineHeight: 1.05
    letterSpacing: "-0.02em"
  body:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.55
rounded:
  control: "8px"
  surface: "12px"
  status: "4px"
spacing:
  compact: "8px"
  row: "16px"
  section: "28px"
  desktop-gutter: "40px"
components:
  button-accent:
    backgroundColor: "{colors.acid}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
  score-sheet:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "23px 24px"
---

# Design System: Hot Roster

## Overview

**Creative North Star: "After-hours league score sheet"**

The built interface combines a dark broadcast frame with warm score sheets. Condensed numerals make position and score the first things to scan; ordinary body text carries names, rule clauses and evidence. The user pinned the music-chart and sports-broadcast world with trading-card rosters and weekly scoreboards. This operates a league: standings, roster selection and weekly evidence precede promotional copy. Pending data remains unscored; recorded and live proof have separate labels.

**Key Characteristics:**

- Condensed chart numerals beside readable explanations.
- Paper score rows inside a charcoal broadcast frame.
- Acid selection accents and small vermilion signals.
- Trading-card rosters with six-week point strips.
- Evidence and transaction links adjacent to outcomes.

## Colors

The frontmatter records the actual CSS custom-property palette. Acid marks active navigation and affirmative controls; broadcast vermilion identifies signals and keyboard focus. Ink and stage form the dark frame; paper and white separate page from score sheet. Muted carries supporting text and line divides rows. Green reinforces success.

**The State Truth Rule.** Color reinforces a written state; green alone never proves finality, evidence sufficiency or payment.

## Typography

Barlow Condensed is self-hosted at 600 and 700; DM Sans at 400, 500 and 700. Page headings use the observed clamp; desktop section headings are 29px. Scores and positions enlarge the condensed face. Body is 14px/1.55; mobile fields are 13px and corrected compact actions, roster selects and fine print are 12px. Smaller decorative metadata exists but is not a reusable readability target.

**The Number First Rule.** Positions and points use the condensed face; evidence, rules and field values use body text.

## Layout

Desktop uses a sticky 230px navigation rail, fluid workspace, 77px top bar, 40px main gutters and 1540px maximum main width. Wide score rows align team, record and points. Observed breakpoints are 1150px, 900px and 650px, plus a 700px compact-label override. Phones stack score sheet and pool, put navigation above the page and use two roster-card columns. Phone navigation scrolls horizontally; Create is its final link and may initially be offscreen. The six-week selector scrolls as needed.

## Elevation & Depth

Flat fills, contrast and light borders distinguish regions. There is no reusable shadow vocabulary. The dark broadcast banner gets its weight from fill and condensed type.

## Shapes

Controls and navigation use 8px corners, containers and trading cards 12px, and status badges 4px. Card initials and simple disc geometry are code-rendered; no raster cover art ships.

## Components

Buttons use ink or acid fill, familiar labels, a minimum mobile height of 42px and reduced opacity when disabled. An unmet settlement condition is written beside its disabled control. Keyboard focus is a 3px vermilion outline with 4px offset.

Ranked score rows select a team and update the roster. Trading cards contain initials, song, primary artist, score and six-week strip. Empty rosters explain the stage and link to the draft. Selection uses a visible-default 180ms ease-out transition; reduced motion disables it.

Native date fields, text inputs, selects and checkboxes have explicit labels and focus. Errors are written alerts. Evidence decisions pair literal quotes, explanation and permanent links. The transaction tracker distinguishes accepted from final results and tracks children. Pending payouts expose claim-parent and native-child hash fields for independent verification.

## Do's and Don'ts

- **Do** preserve paper score sheets, the dark frame and condensed numerals.
- **Do** keep native labelled controls and disabled-state explanations.
- **Do** distinguish recorded proof, live reads and pending transactions.
- **Do** keep evidence links and literal quotations near results.
- **Don't** replace actual outcomes with mocked completed scores.
- **Don't** republish full charts in the app; show roster positions and link to Billboard.
- **Don't** inherit tiny decorative captions as action or form text.

Scope: source and valid 1440/390 captures. The reviewer cleared six listed corrections at that scope; empty states, offscreen mobile Create and motion were source reviewed. Concept-roll provenance was not produced. The documenter agent hit a usage limit; this documentation was completed inline using the skill fallback. Live proof is a separate unfinished requirement.
