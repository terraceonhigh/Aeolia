# The Culture Engine

*On how the simulation's 2D culture space moves, and why divergent cultures stop talking.*

---

The crop-to-culture seed table establishes where polities start in the two-dimensional culture space. It does not establish where they end up. The culture drift mechanics determine the trajectory: how far polities move from their starting positions, in what direction, and at what speed.

The CI axis (Collective to Individual) and IO axis (Inward to Outward) move independently. Each tick, each polity's culture position is updated by a sum of drift terms:

- **Prosperity → Individual**: high energy ratio pushes CI toward +1. Affluent populations develop individualist orientations (Norris-Inglehart: existential security enables post-materialist values; Maslow: material security frees attention from collective survival to individual expression).
- **Crisis → Collective**: energy ratio below the crisis threshold pushes CI toward −1. Resource stress forces collective action on collective problems.
- **Trade exposure → Outward**: participation in the relay trade network (contact count above threshold) pushes IO toward +1. Commercial contact diversifies reference groups and reduces parochialism.
- **Resource stress → Inward**: approaching the Malthusian ceiling, or desperation cascade conditions, pushes IO toward −1. Inward-looking cultures are responses to threat perception from outside.
- **Piety feedback**: high piety (above 0.5) mildly reinforces Collective and mildly Inward orientation — religious institutional life is both communal and tradition-oriented.

The net drift in each tick is the sum of these terms, multiplied by the base `culture_drift_rate` parameter. The culture position moves toward wherever the sum points, bounded between −1 and +1 on each axis.

---

## What This Produces

The drift dynamics create three characteristic trajectories that repeat across simulation runs.

**Temperate, commercially active polities** with good agricultural surplus (emmer/nori crop base, low malaria, positive energy ratio) drift consistently toward the Individual/Outward quadrant. High prosperity (→ Individual) and high trade exposure (→ Outward) reinforce their initial crop-culture seed. After 5,000 years, these polities tend to be more strongly Individualist/Outward than where they started. The commercial civic culture associated with historical thalassocracies — Venice, Carthage, the Hanseatic League, pre-colonial Japan — is what this quadrant looks like at full development.

**Wet-rice and tropical crop polities** face the opposite: low energy surplus relative to population (Malthusian ceiling, higher maintenance costs), periodic crisis conditions (→ Collective), and historically lower trade exposure in relay-dominated networks (→ Inward). Their initial Collectivist/Inward seed is reinforced rather than eroded. After 5,000 years, these polities tend to be more strongly Collectivist/Inward than where they started. The administrative imperial culture of historically hydraulic civilizations — Han China, the Mughal Empire, classical Mesoamerica — is what this quadrant looks like at full development.

**Foraging and marginal polities** start at the center and drift based on local conditions. They are the most sensitive to simulation-specific geography: a foraging polity at a relay chokepoint develops commercial (Outward) culture quickly; a foraging polity on an isolated island away from trade routes develops Inward culture from sheer absence of contact. The center-start is not stability; it is susceptibility.

---

## The Axelrod Freezing Threshold

Robert Axelrod's 1997 agent-based model of cultural diffusion identified a structural property that the simulation replicates: when two adjacent cultures are maximally different, they stop influencing each other entirely.

In Axelrod's model, cultural influence between agents requires at least some shared features. Completely different agents cannot influence each other because there is no basis for interaction. This produces a polarization dynamic: moderately different cultures converge (they have enough shared features to influence each other); maximally different cultures freeze into permanent separation.

The simulation implements this as the cultural distance threshold for trade and contact: when `culture_dist >= 0.85`, the commercial trade complement between two polities is set to zero. Not reduced — eliminated. Polities at cultural extremes stop trading with each other.

The formula: `culture_dist = sqrt((ci_a - ci_b)² + (io_a - io_b)²) / sqrt(8)`. Normalized to [0, 1], where 1 is maximum possible distance (opposite corners of the 2D space). At 0.85, two polities are in different cultural universes — one at the Collective/Inward extreme, one at the Individual/Outward extreme — and the simulation treats them as commercially incompatible.

This freezing threshold is consequential late in the simulation. As the culture drift dynamics push polities toward their respective extremes — the temperate/commercial polities toward I/O, the tropical/agricultural polities toward C/I — the cultural distance between these blocs increases. Eventually some cross-bloc trade pairs hit the freezing threshold and commercial contact ceases. This is not embargo (the player mechanic); it is organic cultural incompatibility.

The pattern matches Axelrod's prediction: cultural polarization is not driven by explicit conflict but by the structural logic of cultural diffusion. Polities become incompatible by moving steadily toward their local cultural equilibria, not by actively choosing to separate.

---

## What the Model Does Not Capture

Axelrod's model, despite being foundational in cultural diffusion studies, has well-known limitations. The most important for the simulation:

**Axelrod's model is neighbor-limited**: agents influence only adjacent agents. This made sense in a land-based model where geographic proximity determines contact. In an ocean world with relay trade networks, contact is not proximity-determined. High-relay polities influence and are influenced by non-adjacent partners. The simulation implements this partially through the contact_mult in tech growth (more contacts → more influence), but the culture drift formula uses direct polity-to-polity blending on absorption, not a full relay-network diffusion model.

**Axelrod's model does not have economic drivers**: in Axelrod's model, cultural diffusion is driven purely by similarity. In the simulation, it is driven primarily by material conditions (prosperity, crisis, trade exposure, resource stress). This is a more materialist model than Axelrod's, and probably a better fit for a civilization simulation, but it means the simulation does not fully capture the mechanisms Axelrod documented — specifically, the role of cultural content (what cultures value) in determining which cultural features spread.

**The drift terms are symmetric**: prosperity → Individual applies equally to all polities at high energy ratios. This means a Collectivist polity that becomes prosperous will drift toward Individual even if its institutional arrangements resist that drift. Real cultures have institutional inertia — collective institutions persist even when material conditions have changed, partly because the people who built those institutions benefit from them. The simulation does not model institutional inertia as a brake on culture drift; drift happens at the same rate regardless of how entrenched the current culture position is.

The culture engine is therefore accurate in its macro-level prediction (temperate → Individual/Outward, tropical → Collective/Inward) without being accurate in its micro-level mechanism (Axelrod diffusion vs. material-condition drift vs. institutional entrenchment). The macro accuracy is what matters for the simulation's calibration targets; the micro-level mechanism is where the most interesting future work lies.

---

*See also: the_crop_culture_seed.md (initial conditions for the culture engine); the_piety_dynamics.md (piety's feedback into culture)*

*Axelrod, R. (1997). "The Dissemination of Culture: A Model with Local Convergence and Global Polarization."* Journal of Conflict Resolution *41(2).*
*Boyd, R. & Richerson, P. (1985).* Culture and the Evolutionary Process. *University of Chicago Press.*
*Norris, P. & Inglehart, R. (2004).* Sacred and Secular: Religion and Politics Worldwide. *Cambridge University Press.*
