# Aeolian Fisheries Reference

## Species Roster

Six species, each filling an ecological and economic niche. Names are drawn from First Nations, Ainu, and historical non-English fishing cultures.

### 1. Sthaq (salmon analog)
- **Etymology**: From Halkomelem *sθ'áqʷi*, the generic Coast Salish word for salmon/fish. "Sockeye" itself comes from Halkomelem *suk-kegh* (red fish); "coho" is also Halkomelem. In Ainu, salmon is *shipe* — literally "the real thing we eat." The fish so important it *is* the word for food.
- **Ecology**: Anadromous (river-spawning, ocean-dwelling). Cold-water, seasonal runs. Massively abundant for a short window, then gone.
- **Economic role**: Calorie backbone of northern/cold-water archipelagos. Dried sthaq is the primary bulk trade protein in the relay trade layer.
- **Trade layer**: Bulk commodity, subsistence and relay layers (tech 0+). Dried sthaq travels 1-3 hops.
- **Culture-space drift**: Pushes **Collective**. Seasonal runs reward communal mobilization — the whole polity processes and stores the catch together. Pacific Northwest potlatch cultures are the real-world evidence: surplus from salmon runs funded elaborate redistribution systems.

### 2. Saak (eulachon/oil fish analog)
- **Etymology**: From Nisga'a *saak*. Eulachon grease was so valuable it created the "grease trails" — entire trade route networks named after this one rendered product. Also known as *sputc* (Nuxalk), *halimotkw* ("savior fish" — arriving at winter's end when food stores run low).
- **Ecology**: Small, incredibly oil-rich, seasonal. Runs up coastal rivers.
- **Economic role**: Saak oil is the marine oil commodity — used for lamps, waterproofing, food preservation, and eventually industrial lubricant. Partially displaced by naphtha at tech 7+, creating an economic transition parallel.
- **Trade layer**: Saak oil is the high-value-density trade good. Relay layer (tech 2+), travels 4-6 hops as rendered oil. The grease trail parallel gives a ready-made trade route origin story.
- **Culture-space drift**: Pushes **Outward** regardless of Collective-Individual axis. Saak oil is only valuable if you trade it. A saak-producing polity is structurally oriented toward exchange.

### 3. Tunnu (tuna analog)
- **Etymology**: From Sicilian/Arabic *tunnu*, origin of English "tuna" via Spanish *atún* ← Arabic *tūn* ← Greek *thynnos*. No strong First Nations equivalent — tuna is a warm-water pelagic species outside the PNW fishery. Mediterranean/Pacific Island etymology fits the ecological niche.
- **Ecology**: Pelagic, migratory, warm-water. Large, fast. Schools follow predictable currents between archipelagos.
- **Economic role**: Premium protein. Fresh tunnu is a luxury good; dried tunnu is bulk. Requires deeper-water boats (tech-gated ~2-3). Tunnu schools following inter-archipelago currents historically establish the first inter-archipelago fishing routes — and thus the first relay trade paths.
- **Trade layer**: Luxury fresh (high markup, 1 hop) and bulk dried (low markup, 2-3 hops). Tech 2+ for open-ocean fishing.
- **Culture-space drift**: Pushes **Individual-Outward**. Requires specialized, high-risk small crews operating far from shore. Mediterranean tonnara operations were run by wealthy owners with hired labor.

### 4. Sardai (sardine/anchovy analog)
- **Etymology**: From Latin *sardīnā*, named for Sardinia.
- **Ecology**: Small, schooling, coastal. Enormous biomass, available everywhere there's coastline.
- **Economic role**: The subsistence fish — every coastal settlement has sardai. Available at tech 0 with the simplest nets. Dried and salted sardai is the cheapest trade protein. Sardai paste (fermented) is the Aeolian garum equivalent.
- **Trade layer**: Subsistence layer (tech 0+). Dried/salted sardai travels 1-2 hops at minimal markup. Sardai paste is a minor relay trade good.
- **Culture-space drift**: **Neutral**. Available everywhere, low-skill, low-surplus. No political implications, just calories. The baseline fish.

### 5. Bakala (cod analog)
- **Etymology**: From Portuguese *bacalhau* / Spanish *bacalao*, ultimately from a Basque or Dutch root for dried cod. The word already sounds like it belongs in an Aeolian trade language.
- **Ecology**: Cold-water, demersal (bottom-dwelling). Dries exceptionally well without salt (stockfish equivalent).
- **Economic role**: The fish that enables long-distance trade — bakala keeps for years. Northern archipelago economies built on bakala export. The "fish that built empires," paralleling Newfoundland cod's role in Atlantic trade.
- **Trade layer**: Bulk relay commodity (tech 2+). Travels 4-8 hops as dried stockfish. The highest-range fish trade good.
- **Culture-space drift**: Pushes **Individual-Inward**. Creates enormous stored wealth concentrated in whoever controls the drying grounds and trade routes. Rewards merchant oligarchy. Hanseatic League is the analog.

### 6. Kauri (shellfish/crab analog)
- **Etymology**: From Hindi/Urdu *kauṛī* (cowrie). Cowrie shells were actual currency across the Indian Ocean and West Africa for centuries.
- **Ecology**: Coastal, sedentary. Nearshore gathering — not fishing per se.
- **Economic role**: Shell has non-food uses (currency, decoration, lime for construction). Meat is subsistence protein. Kauri beds mark valuable coastal tiles. Ties into the Q4 detection-before-exploitation threshold — kauri beds are visible and gathered long before anyone "fishes."
- **Trade layer**: Subsistence gathering (tech 0+). Kauri shell as currency/decoration enters relay trade (tech 2+).
- **Culture-space drift**: Slight **Collective** push. Gathered, not fished — the most egalitarian resource. Resists hierarchy. Keeps a polity at low political complexity longer.

## Integration with Energy Budget

Fish calories enter the energy budget as a second caloric stream alongside crop yield:

```
total_calories = crop_y × land_factor + fish_y × coast_factor
```

Each species carries a culture-drift vector scaled by its share of total caloric intake. The drift per tick is the weighted sum of all food source vectors. No new axes — fish vectors operate in the same two-dimensional continuous culture space (Collective↔Individual × Inward↔Outward) as crop vectors.

### Compounding and conflict

When crop and fishery vectors align (e.g., irrigated grain + sthaq runs → both Collective), they compound. When they conflict (e.g., rice paddies pushing Collective + tunnu pushing Individual-Outward), the polity's culture-space position lands between the two pulls. This is not a bug — it's texture. Coastal China, Japan, and Southeast Asia all exhibit this exact dynamic: communal agricultural cores with outward-facing maritime peripheries.

### Economic transitions

Saak oil's partial displacement by naphtha at tech 7+ creates a structural economic transition for oil-exporting polities. A polity whose trade wealth depends on saak oil faces the same pressures as a petroleum economy facing energy transition — diversify or decline.

## Tech Gating

| Species | Available | Open-ocean variant | Notes |
|---------|-----------|-------------------|-------|
| Sardai  | Tech 0+   | —                 | Simple nets, shore seining |
| Kauri   | Tech 0+   | —                 | Gathering, no gear needed |
| Sthaq   | Tech 0+   | —                 | River-mouth harvesting during runs |
| Saak    | Tech 1+   | —                 | River runs, but rendering requires fire/vessels |
| Bakala  | Tech 2+   | Tech 3+           | Bottom-fishing requires line/hook technology |
| Tunnu   | Tech 2+   | Tech 3+           | Deep-water boats, pelagic pursuit |

## Trade Properties

| Species | Commodity form | Markup/hop | Max hops | Commodity class |
|---------|---------------|------------|----------|-----------------|
| Sardai (dried/salted) | Bulk protein | 5-10% | 1-2 | Bulk |
| Sardai paste | Condiment | 15-25% | 2-4 | Intermediate |
| Sthaq (dried) | Bulk protein | 5-15% | 1-3 | Bulk |
| Bakala (stockfish) | Preserved protein | 10-20% | 4-8 | Bulk (long-range) |
| Tunnu (fresh) | Luxury protein | 35-50% | 1 | Luxury |
| Tunnu (dried) | Quality protein | 10-20% | 2-3 | Bulk |
| Saak oil | Rendered oil | 25-40% | 4-6 | Intermediate |
| Kauri shell | Currency/material | 20-35% | 3-6 | Luxury |
