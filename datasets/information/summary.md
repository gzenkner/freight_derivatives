Baltic Exchange — what it does (plain English)
=============================================

This summary is based on the sources listed in `freight_derivatives/datasets/information/links.txt` plus the PDFs stored in
`freight_derivatives/datasets/information/` (notably `GMB.pdf`, `LNG Whitepaper 2022.pdf`, and ICE contract spec PDFs).


1) What the Baltic Exchange “is”
--------------------------------
- The Baltic Exchange is a membership organisation in the global shipping industry. It is owned by Singapore
  Exchange (SGX). (See `GMB.pdf`.)
- Its “product” is not ships or cargo. Its product is *independent market benchmarks* (rates, indices and
  assessments) that people can reference as a shared, trusted view of “where the freight market is”.
- The publishing/benchmark administration is done via Baltic Exchange Information Services Ltd (“BEISL”), a
  Baltic subsidiary. (See `GMB.pdf` and `LNG Whitepaper 2022.pdf`.)


2) What “market data” Baltic actually publishes (the practical mental model)
----------------------------------------------------------------------------
Think of Baltic as publishing a daily “price tape” for shipping, similar to how exchanges publish prices for
stocks — except shipping is mostly negotiated privately, so Baltic relies on structured input from expert
shipbrokers instead of a central order book.

Core dataset families you’ll hear about:
- Spot route assessments: “What is today’s market rate for route X on ship type Y under standard terms?”
  (Dry bulk routes, tanker routes, gas routes, etc.)
- Composite indices: “Basket” numbers that combine multiple routes into one headline figure:
  - Dry bulk: BCI / BPI / BSI / BHSI and the headline BDI (built from timecharter components). (Baltic FAQs.)
  - Tankers: BITR route set feeding BDTI and BCTI. (Baltic FAQs.)
  - Gas: LNG (BLNG) and LPG (BLPG) routes/assessments. (Baltic FAQs; `LNG Whitepaper 2022.pdf`.)
- Forward assessments / forward curves (Baltic Forward Assessments): the market’s forward view for future
  months/quarters for Baltic-linked freight contracts. (Baltic FAQs; `GMB.pdf`.)
- “Commercial shipping” reference assessments beyond freight:
  - Sale & Purchase (secondhand vessel values), recycling prices, operating expenses (OPEX), etc. (Baltic FAQs.)
- Reports: market reports, fixtures lists, commentary (the “what happened today” layer). (See `GMB.pdf`.)

Why this looks different from stock/FX prices:
- Shipping is illiquid, private, and heterogeneous (ship design, speed/consumption, maintenance, credit terms,
  contract details). There often isn’t a single “last traded price” you can point to publicly. (See `GMB.pdf`.)
- So Baltic uses “panels” of independent shipbrokers as expert submitters, and publishes a methodology that
  explains how input is gathered and governed. (See `GMB.pdf` and Baltic FAQs.)


3) How Baltic produces the numbers (the “panel” system)
-------------------------------------------------------
- Panel members are competitive shipbrokers that meet strict criteria and are selected to reduce conflicts.
  Shipowners and charterers can’t be panellists. (Baltic FAQs.)
- Each route assessment is typically a simple average of panellists’ submitted views for that route (with
  special handling for forward curves). (See `GMB.pdf`.)
- BEISL operates a governance/oversight framework (boards/committees, audit/quality control, conflicts
  policies, methodology reviews). (See `GMB.pdf`.)

Regulatory / trust angle (why big financial players care):
- Baltic describes its benchmarks as regulated and produced under benchmark regulation frameworks (BMR)
  and IOSCO principles; the LNG whitepaper states FCA authorisation/oversight (since March 2020) and
  annual PwC audits for the benchmark process. (See `LNG Whitepaper 2022.pdf`.)


4) Where the indices matter “in real life”
------------------------------------------
Baltic numbers are used in two big ways:

A) Physical shipping contracts (real ships moving real cargo)
- Many freight contracts can reference Baltic assessments/indices as a floating price or benchmark. For
  example, a contract might pay “market rate” based on a Baltic route assessment rather than a fixed rate.
  (Baltic FAQs; see also the “index-linked floating contracts” discussion in `LNG Whitepaper 2022.pdf`.)

B) Freight derivatives (paper contracts used to hedge or trade freight)
- Baltic indices/assessments are widely used as settlement references for freight derivatives (FFAs, futures,
  and options). (Baltic FAQs; `GMB.pdf`.)


5) Freight derivatives in one minute (what an FFA is, and why it exists)
------------------------------------------------------------------------
Shipping companies and cargo owners face freight rate risk:
- A shipowner might worry daily spot rates will fall next quarter (lower revenue).
- A commodity trader/charterer might worry freight will rise (higher transport cost).

Freight derivatives let them lock in or reduce that uncertainty by taking an opposite position financially.
Investopedia’s definition-level view:
- Freight derivatives are financial instruments linked to freight rates and can include futures, swaps, and
  Forward Freight Agreements (FFAs). The Baltic Dry Index is often referenced as a market barometer.
  (Investopedia links in `links.txt`.)


6) “How trading actually happens” (cleared FFA workflow, step-by-step)
----------------------------------------------------------------------
This is the simple, real-world path for a typical market participant:

Step 1 — Decide what you need to hedge (or trade)
- Pick the exposure: ship type, route basket/index, and the future period you care about (e.g., “Capesize
  calendar 2009”, “Panamax Q3”, “Supramax July”, etc.).

Step 2 — Use an FFA broker and agree the trade price OTC
- Most FFA liquidity is historically OTC via specialist FFA brokers (and/or broker arms of larger firms).
- Your broker finds a counterparty and you agree:
  route/index, contract months, volume (in “days”), and the fixed rate ($/day or index points, depending on
  the product). (Baltic “How to trade an FFA” section in `links.txt`.)

Step 3 — Clear it (this is what makes it “operationally real” for institutions)
- In cleared freight derivatives, you don’t rely purely on the other party’s credit.
- You clear the trade via a clearing setup (commonly: you face a clearing member / GCM who faces the
  clearing house).
- Baltic’s clearing page explains the daily mark-to-market: open positions are marked against the Baltic daily
  settlement for the product/expiry, and margin is calculated from that daily move. (Baltic Clearing page.)

Step 4 — Post margin and settle gains/losses daily
- Initial margin: an upfront “good faith” deposit, usually set by the clearing house based on volatility and
  published in contract specs. (Baltic “Types of margin”.)
- Variation margin: the daily profit/loss cash movement based on the difference between your trade price and
  the Baltic settlement price; typically paid/received the next banking day. (Baltic “Types of margin”.)
- Other possible calls: maintenance margin, intraday/unscheduled calls, plus fees (GCM fees, clearing fees,
  broker commission). (Baltic “Types of margin”.)

Step 5 — Close out or reach final settlement
- You can close the position by trading the opposite direction, or hold to expiry.
- Final settlement is typically based on an average of published Baltic assessments over the determination
  period (example from ICE futures specs below). (See `ProductSpec_83048584.pdf` and `ProductSpec_6729757.pdf`.)

Where you can see “real” listed products:
- EEX lists Baltic-linked dry freight futures (e.g., Capesize timecharter averages) and describes contract sizes
  as “1 day” with prices in $/day. (EEX dry freight page in `links.txt`.)
- ICE Futures Europe publishes product specs for Baltic-linked freight futures (examples below).


7) A concrete real example hedge (Star Bulk, January 2009)
----------------------------------------------------------
This is a real press release (not a made-up example) that shows how a shipping company used FFAs:

Who: Star Bulk Carriers Corp (NASDAQ: SBLK)
What they did:
- Sold FFA contracts on the Capesize index for Calendar 2009 for 360 days at ~ $19,900/day.
- Sold additional Capesize index FFAs for Calendar 2010 for 60 days at ~ $25,225/day.
Why (in their own description):
- The trades were intended as an approximate hedge for a Capesize vessel trading spot, “locking in” an
  approximate level of revenue, and they were cleared trades. (See GlobeNewswire link in `links.txt`.)

How to interpret “sold 360 days”:
- Many dry bulk FFAs are quoted in $/day and the contract size is “one day”.
- If you sell 360 “days” at $19,900/day, your notional is 360 × 19,900 = $7.164m of day-rate exposure.
- You don’t deliver a ship. You financially settle vs the Baltic settlement for the same Capesize index period.

Very simplified payoff intuition (ignoring fees/margin financing):
- If the eventual average Capesize settlement for 2009 ends up at $12,000/day, the seller of the FFA makes
  roughly (19,900 − 12,000) × 360 ≈ $2.844m on the hedge, offsetting weaker physical earnings.
- If it ends up at $30,000/day, the seller loses roughly (30,000 − 19,900) × 360 ≈ $3.636m on the hedge,
  but physical earnings are strong — the hedge was insurance, not a bet.


8) What ICE’s Baltic-linked futures specs look like (from the PDFs here)
------------------------------------------------------------------------
These are exchange-listed, cash-settled derivatives tied to Baltic benchmarks:

- `ProductSpec_83048584.pdf` (ICE Futures Europe, dated April 11, 2026):
  - “Baltic Dry Index (BDI) Future”
  - Contract size: $10 × BDI
  - Final settlement: average of the published BDI index points over the determination period.

- `ProductSpec_6729757.pdf` (ICE Futures Europe, dated April 11, 2026):
  - “Handysize Timecharter (Baltic) Freight Future”
  - Contract symbol: TCH
  - Contract size: 1 day of time charter
  - Final settlement: average of the published Handysize Timecharter Index spot assessments.


9) Where public data you can “touch” often comes from (and why terms matter)
----------------------------------------------------------------------------
- Baltic’s own data is commercial/licensed; many “free” charts you see are typically redistributed by vendors
  under their own terms.
- Example places in `links.txt` that publish charts/series:
  - TradingView shows BDI charting.
  - SeeCapitalMarkets provides downloadable shipping index series (including Baltic indices).
Always check terms/permissions before downloading or redistributing.


10) A quick cheat sheet (when you’re building data products)
------------------------------------------------------------
If you’re building analytics internally at a shipping/derivatives shop, the core things you generally want are:
- A clean reference master: routes, vessel classes, index families, units and publish calendars.
- Daily spot assessments and index values with stable identifiers and clear units ($/day, Worldscale, index pts).
- Forward curve assessments (by index/route, expiry/tenor), plus (optionally) implied volatilities and volumes.
- A “derivatives view”: contract specs, settlement conventions, clearing venues/members, and margin concepts.

All of those map directly to how the real market works: assess → publish → settle/benchmark → risk manage.


Sources used (links + local PDFs)
--------------------------------
- Links: see `freight_derivatives/datasets/information/links.txt`
- PDFs:
  - `freight_derivatives/datasets/information/GMB.pdf`
  - `freight_derivatives/datasets/information/LNG Whitepaper 2022.pdf`
  - `freight_derivatives/datasets/information/ProductSpec_83048584.pdf`
  - `freight_derivatives/datasets/information/ProductSpec_6729757.pdf`
