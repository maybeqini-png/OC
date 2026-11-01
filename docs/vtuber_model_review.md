# VTuber model review: composition and eyebrows (2026-11-01)

Owner feedback on the 15-frame expression sheet (`art/generated/vtuber2/final/`): the design is fine, but the
composition and the eyebrows have problems; reference Japanese sources on drawing cute, young, cheeky
(生意気) girls with smaller eyebrows, then analyse the sheet frame by frame.

**Limits of this review.** Direct visits to Japanese sites are blocked by this session's network policy (pixiv,
pixivision, CLIP STUDIO TIPS, いちあっぷ, MediBang, お絵かき図鑑, note.com; dic.pixiv.net and dic.nicovideo.jp answer
403). The findings below come from Japanese web-search extracts of those articles (text only); **no reference
illustrations were viewed**. Scope is kept strictly non-sexual (drawing guides for children's faces and for
smug / ジト目 / ドヤ顔 expressions), in line with the README's hard line.

## 1. What the Japanese guides say (text extracts)
Young faces (子供・童顔の描き方):
- Eyebrows **thin and short** read young and cute; **long, upswept brows read adult / cool** (お絵かき図鑑,
  nigaoe.graphics.vc). Spacing the brows **wider apart** reads more childlike (お絵かき図鑑).
- Eyes slightly **below the face's centre line**, set a little wider apart; **short eye-to-nose distance**; round,
  soft contour, no pointed chin; full cheeks (Esolab, お絵かき図鑑, quirkydrawingclassroom).
- **Short chin and short neck**; broad forehead; lowering all facial parts alone makes a face read younger
  (note.com/nigaoe1, art-watage.com).
- Children are about 4-5 heads tall vs 6-7 for adults (お絵かき図鑑).

Expressions and eyebrows (表情の描き分け):
- Cool-smug (すましたドヤ顔): narrowed eyes, an **arched brow placed a little higher**, and **one mouth corner up**;
  energetic ドヤ顔: a smile with the **brows raised** (MediBang Paint).
- ジト目: parallel lid lines, half-round iris, few highlights (manga.jpn.org, chiba-satoko.com).
- Angry: **inner brow ends down, outer ends up** (眉頭下げ・眉尻上げ), tension between the brows
  (manga.jpn.org, お絵かき図鑑). Troubled / flustered: **ハの字 (困り眉)**, inner ends raised and close
  (Adobe). Raising the outer brow ends reads strong emotion; lowering reads weak emotion (enjoy-start).
- Anime often shows the brows **through the bangs** (透け眉) (アタムアカデミー).

VTuber expression sets (表情差分):
- Expressions are designed from **eye shape, brow angle, mouth opening, cheek blush and pupil / highlight**
  together; brows and eyes are separate parts so they can change per expression (copainter, Live2D notes).
- A standard Live2D standing picture is front-facing with arms at the sides (copainter); the cute look comes from
  the face and parts, not from an action pose.
- Bust-up = from under the chest to the head; face-part placement and shoulder width decide the impression
  (note.com/shikatuno_clock). Slight downward face with eyes up (上目遣い) reads cute; avoid tilting the face up
  too far or small irises, which read as glaring (MediBang, esinote).

## 2. Whole-sheet findings
Measured on the 2048 px base (`final/base.png`): crown y 190, eyes 800, chin 1030, collar 1190, bottom edge at
the shorts waistband.
- **Eyebrows never change.** All 15 frames keep the sheet's brows because only eyes / mouth were pasted. The
  guides above make brows the main carrier of emotion, so angry / flustered / shocked / smug all read weak.
- **The brows themselves read older.** They are long, thin outline arcs set high under the bangs, plus a heavy
  eyeliner-like flick at the outer corner of her left eye (viewer's right). The guides call for short, thin,
  softer brows spaced wide for a young look.
- **Composition is a cropped reference sheet, not a bust-up illustration.** The head (crown to chin) fills only
  41% of the frame height; the navy sweater fills the bottom 42% as one dark block; the frame cuts at the shorts
  waistband (the button shows at the bottom edge); a long stretch of neck is visible (160 px, about a fifth of
  the face height); shoulders square to the camera, no hands, symmetric "ID photo" stance.
- **Two eye styles are mixed.** Frames that keep her sheet eyes have narrow, half-lidded eyes; frames with an
  N5-drawn open eye (wink, flustered, frustrated) have a rounder, bigger, sparkly eye. Side by side they look
  like two artists.
- **Redundant frames.** cheer / laugh / sing and blink / honest, and flustered / frustrated read almost the same.

## 3. Frame by frame
| # | Frame | Reads now | Eyebrows | Composition / other | Fix |
|---|---|---|---|---|---|
| 1 | base | cool, slightly sleepy smirk | long high arcs; outer-corner flick reads mature | crop at waistband, small head, long neck | short thin brows; drop the eyeliner flick; bust-up crop |
| 2 | blink | smiling closed eyes (^^) | unchanged | - | a neutral blink is a flat lid line; ^^ is a smile and flashes "happy" mid-sentence |
| 3 | talk | talking, same sleepy eyes | unchanged | mouth opening slightly large for her face | smaller mouth shapes (a / i / o) |
| 4 | smug | cat mouth :3 with fang | unchanged (no arch) | - | one brow arched up, lids lowered (ジト目), one mouth corner up |
| 5 | wink | wink | unchanged | open eye is the rounder N5 style (mismatch) | keep the sheet's eye for the open one |
| 6 | cheer | happy, closed eyes, open mouth | unchanged; joy needs raised brows | near-duplicate of laugh | raised brows; keep one of cheer / laugh |
| 7 | honest | same as blink plus a smile | unchanged | duplicate of blink | open, softened eyes and slightly raised inner brows |
| 8 | sing | singing, closed eyes | unchanged | near-duplicate of cheer | fine with raised brows |
| 9 | laugh | laughing with a tear | unchanged | duplicate of cheer | merge with cheer |
| 10 | shocked | mild surprise / pout | unchanged; shock needs brows high | eyes still half-lidded | wide eyes, small pupils, brows raised high |
| 11 | angry | smug pout | unchanged; anger needs inner ends down | - | 眉頭下げ・眉尻上げ, puffed cheek, glare |
| 12 | hmph | closed-eye pout | unchanged | - | brows raised / furrowed, face turned slightly away |
| 13 | flustered | teary wink, wavy mouth, blush | unchanged; needs ハの字 | open eye is the rounder N5 style | 困り眉, both eyes in her style, blush |
| 14 | frustrated | same as flustered with a pout | unchanged | duplicate of flustered | merge, or make it a teary glare (困り眉 + pout) |
| 15 | pain | >< wince with a tear | unchanged | - | brows pinched together |

## 4. Proposed fix (needs the owner's decisions)
1. A **new bust-up drawing** of the model with N5: framed from mid-chest up, head larger in the frame (about a
   third of the height for the face), short neck, slight head tilt, sleeves visible, short thin brows shown
   through the bangs, no eyeliner flick; drawn from her sheet so the design stays.
2. **Expressions with brows**: each expression redraws the brow area together with the eyes and mouth (tags such
   as `raised eyebrow`, `v-shaped eyebrows`, `worried eyebrows`, `short eyebrows`, `thin eyebrows`), and every
   open eye keeps one eye style.
3. A tighter set without duplicates: neutral, blink, talk (a / o), smug, wink, happy, sing, shocked, angry,
   pout / hmph, flustered, pain.
4. N5 settings: so far only the Opus-included generations were used (normal size, 28 steps, 0 Anlas). Keeping
   her design across new poses works best with **Precise Reference**, which cost 5 Anlas per image here before;
   larger canvases and more steps also cost Anlas. The balance is 8 Anlas, and buying Anlas is the owner's call.

## Sources
- [イラストで意外と難しい子供の描き方 - お絵かき図鑑](https://oekaki-zukan.com/articles/1448)
- [【童顔・子供の描き方】目の位置が重要！ - Esolab](https://esolab.co.jp/design/1441/)
- [年齢による顔の描き分け方 - quirkydrawingclassroom](https://quirkydrawingclassroom.com/child_and_adult_face)
- [似顔絵の描き方【子供の描き方】 - note (いぬづかてつや)](https://note.com/nigaoe1/n/n81172176a337)
- [似顔絵で子供を描きたい！ - nigaoe.graphics.vc](https://nigaoe.graphics.vc/magazine-blog/nigaoe_kids/)
- [【似顔絵の書き方】子供の顔のコツと描き方 - どこでも絵画教室](https://art-watage.com/online/lesson/1394.html)
- [異なる年齢層の人々を描く方法 - CLIP STUDIO TIPS](https://tips.clip-studio.com/ja-jp/articles/7068)
- [かわいいドヤ顔の女の子を描いてみよう - MediBang Paint](https://medibangpaint.com/use/2023/12/illust-research-easy-qute-doya-face-girl-draw/)
- [ジト目の描き方とキャラクターの表情表現のコツ - manga.jpn.org](https://manga.jpn.org/jitomenoegakihoyoujouhyougennokotsu.html)
- [ジト目の書き方を完全解説 - chiba-satoko.com](https://www.chiba-satoko.com/how-to-write-a-dirty-look/)
- [初心者も簡単！眉毛のイラストの描き方 - アタムアカデミー](https://atam-academy.com/blog/42987/)
- [豊かな表情、感情表現の描き方 - Adobe](https://www.adobe.com/jp/creativecloud/illustration/discover/how-to-draw-expressions.html)
- [怒りを表す漫画の表情の描き方 - manga.jpn.org](https://manga.jpn.org/ikariwoarawasumkinahyougentekunikku.html)
- [表情の描き方をイラスト解説 - お絵かき図鑑](https://oekaki-zukan.com/articles/44434)
- [感情や本心は眉に現れる？ - enjoy-start](https://enjoy-start.com/illustration-face-7/)
- [VTuber・Live2D向けの立ち絵と差分の作り方 - copainter](https://blog.copainter.ai/vtuber-standing-character-guide/)
- [上目遣いしている女の子を描いてみよう - MediBang Paint](https://medibangpaint.com/use/2023/11/illust-research-upturned-eyes-girl-drawing/)
- [上目遣いの描き方 - esinote](https://esinote.com/guide/body/upward-gaze)
- [バストアップのイラスト - note (鹿角時計)](https://note.com/shikatuno_clock/n/n4065cea07b7f)
- NovelAI pricing: [NovelAI Documentation: Subscription](https://docs.novelai.net/en/subscription/),
  [NovelAI V5, Opus free generation has a limit - note (イツキ)](https://note.com/itsuki_ailab/n/nc7a9c09e6096?hl=en),
  [NovelAI V5 on Opus: usage limits - DEV Community](https://dev.to/ilan_kim/novelai-v5-on-opus-usage-limits-the-2026-09-21-subscription-anlas-reset-and-the-apinovelainet-567l)
