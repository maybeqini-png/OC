# Anime-style roguelikes: visual study for the next PV (2026-11-03)

Owner: "You must look into and learn about roguelike anime-style games. This will likely be the design direction for
the next PV." Also asked for mini-boss / main-boss scenes, screen shake and "spatial dimension shifts".

## Sources (viewed for analysis only; kept in the session scratchpad, never fed to the image model)
Official Steam store data and screenshots (store.steampowered.com API): BlazBlue Entropy Effect (2273430), Towa and
the Guardians of the Sacred Tree (1910090), HoloCure (2420510), Sephiria (2436940), Touhou Dystopian (3265060),
Hades II (1145350). Rankings: Steam250 action-roguelike / roguelite / anime tags. Reviews and guides on Rift of the
NecroDancer, Hi-Fi Rush, Honkai: Star Rail (Simulated Universe), Zenless Zone Zero (Hollow Zero) via web search.
Muse Dash boss / transition frames from its official trailer (docs/rhythm_game_style_reference.md).

## What these games share (observed on the official screenshots)
- **Run structure on screen.** A branching node map between fights (Sephiria: floating islands joined by dashed
  lines, icons for reward type); "choose 1 of 3-4" reward cards after a room (Towa "Receive a Grace": tall cards with
  a rarity colour band - Common grey, Rare blue, Epic green, Divine gold - art, name, one-line effect, stat delta;
  HoloCure "LEVEL UP!": a list with NEW! tags, reroll / eliminate buttons); a build inventory grid (Sephiria).
- **Flashy hit language on dark stages.** BlazBlue EE and Touhou Dystopian: dark, desaturated backgrounds so the
  attacks glow - huge crescent slashes in rainbow or hot orange, light streaks that cross the whole screen, shards
  and geometric panels flying out (BlazBlue's giant blue chevrons = a "dimension shift" moment), damage numbers.
- **Boss presentation.** Boss name + title bar across the top centre (Touhou Dystopian: "Remilia Scarlet / The
  Scarlet Devil" with a long thin HP bar); arena-wide attacks (red orb rings, pillars of light); a finishing screen
  with big calligraphic kanji ("完美決着") over a radial-blur explosion; result stamp ("CLEAR", time, "PERFECT").
- **Character presence.** Large anime portrait busts with a name plate in dialogue (Towa, Hades II) between runs;
  in combat the character is small and the effects are big.
- **Rhythm bosses (Rift of the NecroDancer, Hi-Fi Rush, Muse Dash).** One-on-one duels where the boss attacks on the
  beat and you counter; each boss adds one new mechanic; the boss stays on the right edge and throws projectiles
  into the lanes (Muse Dash); a boss "mash" phase.
- **Screen / space shifts (Muse Dash trailer).** The playfield becomes a tilted card with a neon double frame that
  rocks between angles at section changes; a section ends by shattering the card into shards, cutting to a manga
  starburst + close-up character splash panel, then a white flash; bubble wipes; polka-dot / zigzag panel slides.

## How this maps onto the XIYIN PV (proposal)
- Song sections = "floors" of a run: a node-map card between sections shows the next stop (normal / elite = mini
  boss / boss), and after each section a 1-of-3 "blessing" card pick (cat-themed buffs) flashes by on the beat.
- Mini-boss at the end of the second verse, main boss for the final chorus: name + title bar and long HP bar at the
  top, boss fixed at the right edge firing its family's projectiles into both lanes on the beat, a mash phase, and a
  "完美決着"-style kanji finisher before STAGE CLEAR.
- Dimension shifts: playfield as a tilted neon card rocking at section boundaries; shatter -> manga splash panel of
  XIYIN -> white flash; beat-locked screen shake on boss hits (stronger than on normal hits); dark-stage glow attacks.
- Keep the owner's rules: flat cute style, no cyber / neon-city aesthetic in backgrounds (neon only for UI frames),
  original designs only, no images from these games used as image-model inputs.
