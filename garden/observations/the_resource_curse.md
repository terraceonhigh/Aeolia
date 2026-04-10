# The Resource Curse

*On why naphtha makes polities worse at the things that matter, and why pyra does the same thing more quietly.*

---

The resource curse is the empirical observation — robust across multiple methodologies, contested in its mechanism — that countries with large endowments of extractable natural resources tend to grow more slowly, develop weaker institutions, and experience more political violence than comparable countries without those endowments. The finding is counterintuitive: being given something valuable should make you richer, not poorer. The explanation runs through institutions.

Jeffrey Sachs and Andrew Warner (1995) documented the negative correlation between resource abundance and economic growth in a large cross-country sample. Michael Ross (2012) spent two decades studying specifically the "oil curse": why oil-rich states tend toward authoritarianism, weak civilian institutions, and development paths that don't generalize to non-oil sectors. The mechanism that both identify is rent-seeking: when the resource generates income that flows primarily to the state (or to a small extractive elite), the state has reduced need to build the tax-based relationships with productive citizens that historically drove institutional development. A government that does not need to extract taxes from productive citizens does not need to be accountable to them.

The simulation encodes this through the naphtha curse penalty on TFP growth.

---

## The Naphtha Curse

When a polity controls more than approximately 13% of the world's initial carbon stock, and its tech level is between 6 and 9.5, the naphtha resource curse fires:

`curse = clamp(polityFrac × 3.0 − 0.4, 0, 0.5)`
`A₀ *= (1 − curse × resource_curse_strength)`

At the maximum curse intensity (polityFrac = 0.30, resource_curse_strength = 0.8), the curse reduces the base TFP growth factor by 24%. This is a significant penalty — it means a naphtha-dominant polity grows its tech approximately one-quarter slower than it would at equivalent energy budget and institutional conditions without the naphtha endowment.

The curse applies at the peak of the naphtha economy (tech 6–9.5) and phases out as polities approach the nuclear threshold. This reflects the historical pattern: the oil curse is strongest in the middle-income transition period, when the state is large enough to capture resource rents but the economy is not yet sophisticated enough to generate non-extractive alternatives. Before extractive capacity is built (tech < 6) and after nuclear development supersedes fossil fuel competition (tech > 9.5), the curse is not active.

The tech ceiling for the curse (9.5) is also significant: it means naphtha-cursed polities can still reach nuclear capability, but they do so more slowly than non-cursed polities. This contributes to the strategic disadvantage of high-naphtha polities in the scramble for nuclear capability. A polity that won the naphtha scramble — acquiring disproportionate naphtha control — may lose the nuclear race precisely because the naphtha winnings compromised the institutional quality needed for the final tech push.

---

## The Pyra Curse

Pyra is the simulation's analogue for the next generation of strategic industrial material — the resource that drives the tech 8–9.5 era the way naphtha drives tech 5–8. At tech ≥ 8.5, the pyra resource curse fires at 60% of the naphtha curse strength.

The pyra curse is weaker than the naphtha curse by design: the industrial era's institutions are already more developed at tech 8.5 than at tech 6, meaning the same resource rents are somewhat less able to distort institutional quality because there is more institutional depth to absorb and resist the distortion. The historical analog is the debate over whether the "silicon curse" from technology monopolies is as damaging to democratic institutions as the oil curse was — the tentative consensus being that it is damaging but not to the same degree, partly because the institutional environment in which tech monopolies emerged was already more developed.

The pyra curse also has shorter duration: it phases out at tech 9.5, the same ceiling as the naphtha curse, but it starts later (8.5 vs. 6.0). This means the window of active pyra curse is narrower than the naphtha curse window, which is consistent with the expectation that later-era resource scrambles have less total impact than the formative naphtha scramble.

---

## What the Curse Does Not Model

Sachs and Warner's paper was influential partly because of its simplicity: it documented a negative correlation between resource abundance and growth without specifying the mechanism. The mechanism has been debated for thirty years. The main candidates are:

**Dutch Disease**: resource exports appreciate the currency, making non-resource exports uncompetitive and hollowing out the tradable goods sector that develops institutional capacity. The simulation does not model exchange rates or sector-specific production; the curse is applied directly to TFP without specifying whether the channel is Dutch Disease, rent-seeking, or something else.

**Patronage politics**: resource rents are distributed through patronage networks that entrench incumbents and distort labor market incentives. The simulation models this as reduced institutional inclusiveness (the culture-space mechanism: resource-rich polities drift toward extractive cultural orientation) but does not model patronage specifically.

**Conflict attraction**: resource-rich territories attract conflict from external actors and internal factions, which damages institutions and growth. The simulation has conflict mechanics (expansion targeting gives a resource bonus) but does not model the conflict premium specifically as a curse mechanism.

Robert Vitalis (2018) raised a different critique: the oil curse narrative overstates the degree to which oil is special, as opposed to being one instance of the general principle that extractive institutions under concentrated ownership damage growth regardless of what is being extracted. On this reading, the oil curse is a special case of the AR extractiveness penalty, not a distinct mechanism. The simulation has both penalties (AR extractiveness from colonial extraction, naphtha curse from resource endowment) as separate mechanics, which implicitly treats them as separate mechanisms. Whether they are empirically distinct is a genuine question the simulation does not resolve.

---

*See also: the_lock_in_mechanics.md (AR extractiveness as the broader institutional penalty); the_three_layer_trade_system.md (administered trade as the extraction mechanism)*

*Sachs, J. & Warner, A. (1995). "Natural Resource Abundance and Economic Growth." NBER Working Paper 5398.*
*Ross, M.L. (2012).* The Oil Curse: How Petroleum Wealth Shapes the Development of Nations. *Princeton University Press.*
*Vitalis, R. (2018). "The Myth of the Authoritarian Oil State."* Perspectives on Politics *16(2).*
