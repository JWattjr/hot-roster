# Verification scope

The release is **not yet submission ready**. `deploy/proof.json` records current finalized progress. The live replay is still running; six scored weeks, both moment decisions, both dispute verdicts and winner credit must be verified before completion is claimed.

Checks already run: 39 passing direct contract tests with mocked cross-contract reads, web and model responses; six passing app tests (four domain checks and two decodes of real SDK receipts); strict TypeScript typecheck; local production build; all five contracts passed GenVM lint. The linter warns that a newer runner exists; this project deliberately uses the runner requested in the brief.

Browser verification inspected the running application at desktop and 390×844 mobile. The live finalized-state read returned the actual draft and funded pool. All six routes rendered at 1440×960 and 390×844 without page overflow. Native date controls rejected a Sunday before signing at both sizes; a valid Saturday produced the expected missing-wallet explanation. Saved evidence is in browser-routes.json and browser-forms.json. Browser checks cannot establish wallet signing or adjudication outcomes. Live release receipts establish those separately.

The four 10-wei entry deposits finalized. `deploy/funding.json` records native funding; `deploy/receipts/entry-*.json` records contract entry receipts. Owner approval is bounded to 42 wei total: entries plus two one-wei dispute bonds. No additional deposit is authorized by these scripts.

The read-only `npm run verify:proof` checks raw final execution, source SHA-256, full chart digests and recorded state equality. It requires real AWARDED, NOT_AWARDED, UPHELD and OVERTURNED outcomes and an exact winner credit. It intentionally fails while any requirement is incomplete. The release scripts neither inject an expected live verdict nor silently substitute a mock when a validator disagrees.

Final deployment URLs, final check counts, browser evidence and remaining limitations are added here when those checks actually finish.

The finish reviewer marked the six listed UI corrections resolved, at that scope only. The documenter agent hit a usage limit; the design documentation was completed inline from the source under the skill's fallback instructions. Concept-roll provenance was not produced and is disclosed in docs/design-brief.md.

The published app is https://hot-roster-genlayer.vercel.app, with public source at https://github.com/JWattjr/hot-roster. A deployed API check verified a finalized draft receipt and the real current league. After updating viem to 2.57.4, the production dependency audit reports zero vulnerabilities; TypeScript, the six app tests and the production build passed again. The six-week live replay is still in progress.

Closed chart reads retain their original archive URL, digest and roster-only rows during live refresh. Immutable chart judgments and final transaction outcomes are cached; league background refresh runs once per minute while transaction polling remains ten seconds. The RPC budget is per server process, so independent serverless instances do not share a global counter.

The production routes were also checked at both sizes after deployment; see browser-production-routes.json. The app wallet adapter made a real signed zero-value call through genlayer-js 1.1.8 and viem 2.57.4, and it finalized successfully. deploy/wallet-adapter-check.json preserves that receipt. This check used a local Node signer through EIP-1193, not a browser extension popup.

Five additional release-resume tests pass: a pending hash is retained, a terminal zero-value judgment keeps its failed receipt under a separate label, and a deposit, mismatched hash or emitted child prevents resubmission. The first local run was blocked by temporary-directory permissions; the same tests passed with normal filesystem access. `failedTransactions` preserves terminal disagreement receipts separately from successful replay calls; the independent verifier checks both ledgers.

The deployed receipt API decodes the pinned SDK’s actual creation return and expected rejection message. Importing the real creation hash in the public tracker opened the draft room; success and error states survived a reload. See browser-tracker-check.json and deployed-receipt-decoder-check.json. Re-importing a tracked hash explicitly refreshes its receipt. This covers receipt rendering and navigation; it does not claim a browser wallet-extension signature was exercised.
