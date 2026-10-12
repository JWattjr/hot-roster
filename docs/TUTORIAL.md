# Build and play a league with Hot Roster

Hot Roster turns a music chart into a fantasy league. Players draft songs rather than performers or albums. Every chart week, the songs earn deterministic position points. Validators also judge evidence for bonuses and interpret disputes against the league's frozen rulebook. The distinction matters: a model can decide whether a chart entry represents your song, but it cannot decide that a song should receive an arbitrary number of points or an arbitrary payout.

Start by opening the app without connecting a wallet. The season page reads the recorded proof shipped with the application. It shows the replay's current standings, each team's roster, week-by-week scores, moment decisions, disputes and pool. A label distinguishes recorded proof from live finalized-state reads. Use **Read live state** to request current on-chain state. If the RPC is unavailable, the recorded proof remains available and an error explains what happened. An incomplete live replay remains visibly incomplete; it is never filled with mocked outcomes.

## Create and join

Choose **Create a league**. Enter a name, the first chart Saturday, four to eight consecutive weeks and a capacity between four and eight players. Rosters always contain five songs. Choose the catalog cards and read their definitions. The default rulebook explains featured credits, chart scoring, event eligibility, disputes and settlement. Edit it before creating the league; creation records its SHA-256 hash and freezes the text. Optional entry fees are denominated in wei of simulated StudioNet GEN. A fee of zero creates a points league.

Connect an EIP-1193 wallet such as MetaMask. The app requests StudioNet, chain 61999, using the Studio RPC and explorer. Signing happens in the wallet. No demo private key is delivered to the browser. A newly submitted transaction appears in the transaction tracker with its hash. The tracker persists across reloads and distinguishes submitted, pending, accepted, finalized success and finalized error. Accepted transactions may still be appealed; the displayed native appeal window is separate from the league's dispute window.

Share the league ID with friends. They can enter that ID through **Open league**, join with a team name, and pay the exact frozen fee if the league has a pool. The creator starts the draft after at least four players have joined and every pooled entrant has paid. Joining and drafting have fixed deadlines; a league that cannot complete before settlement has a refund path.

## Draft five songs

The draft room displays join order and the team whose turn it is. The first round runs forward, the second backward, and subsequent rounds alternate. Search the starter catalog by title or primary artist. Already drafted entries appear taken. You can also enter another canonical title and primary artist. The contract checks turn order and uniqueness; disabling a browser button is only an additional convenience. The visible ninety-second clock is advisory and does not enforce an on-chain timeout.

After twenty to forty valid picks, the league becomes active. Before a week is locked, each player may replace one roster slot with an undrafted song. In current seasons swaps also close at the chart Saturday. Historical replay seasons use the week lock as their cutoff. The frozen weekly roster preserves the owner of each song even if it is swapped later.

## Read and score a week

Open **This week** and select a chart date. Lock the current week, then request a chart read. ChartReader looks for an exact successful CDX archive capture of that dated Billboard URL. Only when CDX reports no capture does it use the live dated page. Python extracts the hundred chart rows, last-week positions and debut flags before a model sees anything. The model receives these compact rows and the roster and resolves featured credits, collaborators and versions. Each validator fetches and extracts independently; agreement requires the same digest and the same position vector.

The app displays only the roster's matched rows. Open the Billboard or evidence link to review the source. Code gives 25 points for No. 1, 15 for positions 2–10, eight for 11–40, three for 41–100 and zero for absence. A genuine debut adds five and a climb of ten places adds three. Extraction failure produces insufficient evidence and remains retryable until the deadline; an unavailable chart then contributes zero rather than keeping the league locked forever.

## Claim a moment and review a ruling

Any player can claim a card for any rostered song. Select the song, a frozen card and one permanent evidence URL. Use the preview to inspect the document, then open its actual link. Evidence must be an exact archive `id_` capture inside that week with an allowlisted original domain and CDX verification, or an allowlisted Wikipedia `oldid` revision. Each card can be claimed once per song per week and each player can submit at most three claims that week.

Adjudication is a separate transaction after claim registration finalizes. MomentJudge checks the event against the definition and date interval. Awarded and rejected decisions include a verbatim quote and an explanation. Each validator must find the leader's quote in its own fetch and return the same verdict. A tour rumour, nomination, or merely announced future remix does not satisfy a card requiring an official event or release.

To challenge a finalized opponent result, open **The rulings**, choose a chart match or moment and explain the disputed interpretation. RulebookCourt re-reads the same source and the exact frozen rulebook. It returns upheld, overturned or insufficient evidence, quotes a rule clause and passage, and supplies a bounded correction. League code applies an overturned correction when scoring. A losing challenger forfeits the three-point bond to the opponent; pooled leagues additionally require a one-wei bond. One item gets one dispute. Judgment requests cannot predetermine a desired outcome.

## Close, settle and verify

Players mark themselves ready once claims are complete. Closing waits for the frozen chart and moment dispute windows and resolved disputes, or their deterministic deadlines. The contract scores the week, updates head-to-head records and advances to the next date. The final week emits a finality callback before the season becomes completed.

Anyone can request pool settlement. Code allocates 60/30/10 to the first three ranks when at least four players participate. Tied players share the weights for the ranks they occupy; the integer remainder goes to the creator. A winner signs a pull claim. It stays pending until the claim parent and native transfer child have finalized. **Verify native credit** checks their origin, recipient, amount, relationship and claim attempt on-chain. Paste hashes if you used another browser. A verified failed transfer permits the next attempt. An unknown pending receipt is not evidence of payment or permission to send again.

For reviewers, run `npm run verify:proof`. The verifier signs nothing, compares deployed source hashes and finalized raw receipts, checks all six extraction digests and recorded outcomes, and verifies actual winner credit. It deliberately fails until the required live outcomes exist. Read `docs/VERIFICATION.md` to distinguish contract mocks, browser checks and live proofs before submitting.
