# The Growth Machine

*On how the simulation encodes technology growth and why energy is in the formula.*

---

The simulation's technology growth formula is:

`delta_tech = A₀ × crop_exp × share_mult × accel_rate × contact_mult × energy_mult`

Each term is doing something specific. Together they encode three decades of debate in growth economics, compressed into a formula that has to run 200 times per simulation.

---

## The Solow Core

Robert Solow's 1956 growth model established the canonical framework that all subsequent growth theory has been arguing with. In Solow's model, output is a function of capital, labor, and total factor productivity (TFP): Y = A × f(K, L). TFP — the A term — captures everything that makes the same capital and labor produce more output: technology, institutions, knowledge, organizational efficiency. Solow's model treats TFP as growing exogenously, at a rate determined outside the model. The model tells you what happens given TFP growth; it does not explain where TFP growth comes from.

In the simulation, `delta_tech` is the tech growth rate — the simulation's proxy for TFP growth. The `A₀` term is the base productivity factor, roughly corresponding to Solow's exogenous TFP growth rate. `crop_exp` is the production function exponent for the dominant crop type — a rough encoding of the Cobb-Douglas capital-labor substitution parameter that Solow fit to post-war US data. For wet-rice (paddi) polities, `crop_exp` is lower, encoding the diminishing-returns-to-intensification finding in tropical agriculture; for temperate grain polities, it is higher.

This part of the formula is straightforward Solow. What made the formula harder to build was the energy term.

---

## Energy as a Factor

Solow's original model had a well-known residual problem: even after accounting for capital accumulation and labor growth, approximately half of post-war US economic growth came from the residual TFP term that the model could not explain. This residual is where all the interesting theoretical work happened in the decades after 1956.

Robert Ayres and Benjamin Warr (2005) proposed a partial resolution: energy — specifically, the physical work that energy enables — was being omitted from the standard production function. When you add energy use as an input alongside capital and labor, the residual shrinks substantially. The growth that appeared to come from unexplained TFP turned out to come partly from growing energy consumption enabling growing physical work output.

This finding has a direct implication for a simulation of civilizational development. A polity's capacity for technological progress is not independent of its energy budget. Polities with abundant energy surplus — good harvests, healthy fisheries, favorable terms of trade — can invest that surplus in the R&D-equivalent activities that produce tech growth. Polities at energy margin cannot. The energy_mult term encodes this: `energy_mult = er × energy_to_tfp`, where `er` is the energy ratio (current surplus / subsistence floor) and `energy_to_tfp` is the coupling coefficient calibrated at 0.51.

The calibration value of 0.51 was reached empirically during the Dark Forest tuning. At lower values (e.g., 0.3), polities reached tech 9 too slowly — the Dark Forest fired centuries later than the historical-analog period suggested. At higher values (e.g., 0.7), polities reached tech 9 in ways that did not preserve the inter-polity tech variance that makes the simulation's outcome distribution interesting. 0.51 was the value at which, on seed 216089, nuclear capability emerged around year -400 and the Dark Forest fired around year -250.

This is the Grade-B limitation: the coupling value is calibrated to produce the right macro pattern, not derived from an estimate of how energy-TFP coupling actually works in civilizational development. Ayres and Warr's empirical estimates used 20th century industrial economies. The simulation applies the same coupling to pre-industrial, colonial, and post-industrial polities in the same formula. The coupling coefficient probably should not be constant across these regimes; it was left constant because varying it would require additional calibration work.

---

## Endogenous Growth: The Contact Term

Paul Romer's 1990 model of endogenous technological change addressed the question that Solow left open: where does TFP growth come from? Romer's answer: from deliberate investment in knowledge production, subject to positive spillovers. Knowledge is non-rival (one polity using an idea does not deprive another of it) and partially non-excludable. This creates network externalities in innovation: the more entities participating in knowledge-generating activities, the faster knowledge grows for all of them, because ideas recombine and build on each other.

The simulation's `contact_mult` term is the Romer encoding: `contact_mult = 1.0 + contact_count × tech_contact_bonus`. Polities with more trade and diplomatic contacts grow faster because they have access to more knowledge recombination opportunities. A polity in a dense relay network accelerates relative to an isolated polity even with identical domestic resources, because it can learn from and build on its contacts' innovations.

This is a compressed version of Romer's mechanism. The full Romer model distinguishes between the stock of knowledge (which grows with investment) and the rate at which existing knowledge enables new knowledge (which increases with the knowledge stock). The simulation collapses both into a linear contact bonus, which is computationally tractable but loses the accelerating-returns property that makes endogenous growth theory interesting. In principle, knowledge-rich late-game polities in dense networks should be accelerating faster than knowledge-poor early-game polities in sparse networks by more than the linear formula produces. This is a known approximation.

---

## The Acceleration Table

The `accel_rate` parameter takes different values in different tech regimes:

| Tech range | accel_rate | Historical analog |
|------------|------------|-------------------|
| < 3.0 | Lowest | Pre-agricultural / early agricultural |
| 3.0–5.0 | Low | Classical and medieval |
| 5.0–7.0 | Medium | Early modern (printing, navigation, proto-industry) |
| 7.0–9.0 | High | Industrial revolution |
| ≥ 9.0 | Highest | Post-industrial / nuclear era |

The acceleration table encodes the historically observed pattern that tech growth rates have not been constant across human history. The rate of innovation increased substantially with the printing press and the emergence of commercial scientific culture in the 16th–17th centuries; it increased again dramatically with the industrial revolution; it continues to accelerate in the contemporary period.

The Simon Kuznets and Moses Abramovitz empirical work on long-run growth rates underlies this table, but the specific breakpoints and multipliers were calibrated to produce the correct tech level distribution at the time of the Dark Forest event. The table is a judgement call encoding of a complex empirical finding, not a direct translation of growth accounting results.

---

## The share_mult Term

The `share_mult` term scales tech growth by the fraction of the polity's energy budget allocated to expansion vs. innovation vs. consolidation. At full innovation allocation, `share_mult = 1.0`. When allocation overrides force spending toward expansion (the desperation cascade), `share_mult` falls.

This encodes a basic finding across several traditions: technological progress is investment-dependent. The Dutch Golden Age coincided with exceptional investment in commercial infrastructure and scientific institutions. The British industrial revolution coincided with capital accumulation from colonial surplus. Polities that are spending their surplus on military expansion and territorial consolidation are not spending it on the productive activities that generate tech growth.

The allocation mechanics (the player's National Focus decision in the strategy game) are therefore directly coupled to tech growth through `share_mult`. This is where the player's decisions have the most durable long-term effect: choosing Expand consistently over Innovate compounds into a tech disadvantage that is difficult to close later.

---

## What the Formula Does Not Model

The growth formula omits institutional quality as a direct input. In the actual growth literature, institutions are among the strongest correlates of long-run growth — more robust than energy availability, more robust than geography, more robust than trade access. The AR extractiveness penalty captures part of this: extractive institutions reduce TFP through the AR penalty on `A₀`. But this is a damage term (extractiveness reduces growth) rather than a positive institutional contribution term.

The Romer contact term is also missing the quality dimension: contacts with high-tech polities should contribute more to growth than contacts with low-tech polities, because there is more useful knowledge to absorb from more advanced trading partners. The formula counts contacts equally. This is an approximation that understates the growth benefit of being in a high-tech relay network and overstates the benefit of being in a low-tech relay network.

Both gaps could be addressed with additional parameters and calibration work. They are on the list.

---

*See also: the_lock_in_mechanics.md (AR extractiveness penalty on A₀); the_desperation_trap.md (share_mult forced to expansion under energy stress)*

*Solow, R.M. (1956). "A Contribution to the Theory of Economic Growth."* Quarterly Journal of Economics *70(1).*
*Romer, P.M. (1990). "Endogenous Technological Change."* Journal of Political Economy *98(5).*
*Ayres, R. & Warr, B. (2005). "Accounting for Growth: The Role of Physical Work."* Structural Change and Economic Dynamics *16.*
