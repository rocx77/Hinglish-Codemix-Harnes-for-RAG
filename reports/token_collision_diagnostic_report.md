# Short-Token English/Hinglish Collision Diagnostic — PHINC Vocabulary

**Date:** 2026-09-05
**Data:** `Datasets/phinc_cleaned_step1to4.csv`, column `Sentence_clean`, 13,510 rows
**Tooling:** `src/token_router.py` (`classify_token`) — read-only, not modified
**Script:** `scripts/token_collision_diagnostic.py` (seed=42)

## Reason this report exists

The Tier-1/2/3 Hinglish normalization pipeline (next phase of this project) will
route tokens via the Pre-Tier-1 router (`classify_token`). A token classified as
`ENGLISH` will be left untouched; a token classified as `CANDIDATE_HINGLISH`
will be sent to IndicXlit for roman→Devanagari conversion. A misclassification in
either direction corrupts the normalized corpus and propagates into the search
benchmark, so the *size and shape* of the collision problem must be quantified
before the pipeline is built.

Specifically: short lowercase tokens are where Hinglish and English collide most
(e.g. `thi` = थी, `jab` = जब, `ni` = नहीं, `band` = बंद, `ham` = हम). If a large
share of short tokens is routed to ENGLISH, a large share of Hinglish words would
be silently skipped by normalization. This report measures that risk numerically
and produces a random, frequency-sorted sample of the danger zone for manual
review. *(Per project convention, every report includes a reason/purpose
section explaining why it was generated.)*

## Step 1 — Vocabulary

- Rows read: 13,510
- Unique tokens (case-insensitive, after `.split()` and lowercase): **29,579**

## Step 2 — Classification by length bucket

Total unique tokens per length, bucketed by `classify_token` result.

| Len | Total | ENGLISH | NUMERIC/ALNUM | CANDIDATE_HINGLISH |
|----:|------:|--------:|--------------:|-------------------:|
| 1   | 104   | 48      | 10            | 46                 |
| 2   | 523   | 293     | 83            | 147                |
| 3   | 1,792 | 870     | 135           | 787                |
| 4   | 3,394 | 1,172   | 107           | 2,115              |
| 5   | 5,264 | 1,199   | 54            | 4,011              |
| 6   | 5,144 | 1,100   | 58            | 3,986              |
| 7   | 4,015 | 942     | 53            | 3,020              |
| 8+  | 9,343 | 1,618   | 562           | 7,163              |
| **All** | **29,579** | **7,242** | **1,062** | **21,275** |

Danger-zone pools: **1,178** tokens are length ≤ 2 and ENGLISH; **2,383** are
length ≤ 4 and ENGLISH; **1,199** are length 5 and ENGLISH.

English share by length: len1 46.2% · len2 56.0% · len3 48.5% · len4 34.5% ·
len5 22.8% · len6 21.4% · len7 23.5% · len8+ 17.3%.

Observations:

- The collision pressure is concentrated below length 5. Roughly 1 in 2 tokens
  of length 1–3 is classified ENGLISH, falling to ~1 in 5 at length 5+, matching
  the intuition that short Hinglish function words (2–4 letters) are the overlap
  zone with the English wordlist.
- Numeric/alphanumeric tokens are fairly static (~1–4% of each bucket except a
  562-token jump at 8+, e.g. handles/IDs) and are not part of the collision
  problem.
- Note an encoding artifact appears in the sample: `Γ¥ñ∩╕Å` (a cp1252-mojibaked
  emoji) is a 3-char token classified ENGLISH — characters like these should be
  screened at the preprocessing layer, not by the router.

## Step 3 — Sample: length ≤ 4 classified ENGLISH (n=60)

Random sample (seed=42) from the 2,383-token pool, sorted by descending corpus
frequency (FREQ = number of rows containing the token). Example sentence is one
`Sentence_clean` row containing the token. No correctness labels applied — for
human review.

| TOKEN | FREQ | Example `Sentence_clean` |
|------:|-----:|--------------------------|
| thi | 162 | Haan, uske khidki khuli thi jismein se baburao jhaank raha tha. |
| jab | 149 | tere liye maaf, tu jab bhi aaye aur milne ka mood ho toh bata dena. akshaykanitkar MePurplelicious |
| hue | 78 | Miss u msd " aadat ho gayi hai aapko captain dekhte hue .. Dhoni |
| band | 63 | Gott_Partikel aankh band karte hi shruti hassan nazar aati hai :( |
| ni | 61 | unhone pehle pic ni dkhi ti kya tmhari jo milne k baad hi ignore kia tmhe . . . ? |
| come | 37 | someUSER i'm in hawaii at the moment . home next friday night . don't want to come home . |
| hope | 27 | Bhai kuch kal ke liye bhi chhod de.. RT EconomicTimes KejriwalTakesOath: I hope that India wins the World Cup |
| ham | 24 | narendramodi ji ab bhot hogya " ham aapki har baat maan rhe h aap bhi hamari ek baat manlo " ab bullet ki jagah bullet hi khilao 0 MannKiBaat |
| d | 23 | Dhoni should remind Faf abt IPL !! Agar khelna hai toh out ho jaa !! Hussey z back in d team !!! justsaying IndiaVsSouthAfrica |
| bt | 19 | Sir me apka big big fan hu mujy apse call pe bt karni hai ek bar sir mera contact num 03356507139 Skype I.d abdul.rehman6731 plzzzz contact meabdul.rehman.sahabto |
| says | 18 | realpreityzinta mam kabhi kutch me bhi aaya karo shooting ke liye as SrBachchan always says kutch nhi dekha to kuch nahi dekha ! pzchat |
| let | 14 | He cries and cries and cries becoz u wnt let him do it ? Did you say you were seeing a \ " guy\ " ? ;) |
| send | 11 | Hi bomanirani sir Apne kaha tha remind kradana Autograph send karna hai so please send kardo . |
| cool | 10 | haha i have done exactly the same several times . at recess the sweater used to tie around our waist , making we kids a little cool . nostalgia . . :d |
| find | 10 | ye aaiyena naaa wala character you will find in every school and college . har cheej me hoshiyari deta hai ye character :@ :@ :p |
| rana | 6 | ExSecular LOL.. Rana aunty dawai lena bhool gayee RanaAyyub |
| acc | 5 | someUSER stick to college hoops & pandering to 2nd rate acc teams . . . dook's opening game is right around the corner , baybeeee ! ! |
| hog | 5 | hey guys tomorrow is now national ground hog day ,i hope to see you all post about it !!hahahaha |
| nets | 5 | nba the brooklyn nets opener vs . the new york knicks is postponed . it was originally scheduled for thursday evening . |
| cast | 4 | vishalsingh713 agar pre leap ka shoot ho chuka hai ek pic post kar dijiye na with old cast :( |
| wed | 4 | gambled on chocolate day as a successful theme day at work . . turns out chdn do like chocolate . wed . is gross day . hope kids like gross stuff . |
| cid | 3 | BloodyKamina waah CID me bharti ho jaa |
| dada | 3 | jo jaisa dusro k sath krta h uske sath aisa hi hota h ..he cheated dada ... |
| vase | 3 | What the hell!! Roz ka din rape ki news se start ho raha hai. Insan nahi saale bhediye bhare pade hai maar daalo saalo ko.. jahan dikhe thok do koi case vase chalane ki zarurat nahi |
| bass | 3 | hahaha . . . acting tere bass ki baat nhi ! ! |
| deja | 2 | Deja Vu hai. Mark idhar thaa... Pichle saal bhi. |
| arm | 2 | Bhai ek kilo hapus arm ka kitna? ΓÇª |
| eh | 2 | Happy MahaShivratri ... : : Deh Shiva eh bar mohe-i-hai shubh karman the kabhu na taroo Na daroo ar siyoo ... |
| wade | 2 | lol, Matthew Dahi Wade trend horaha hai |
| idol | 2 | Anadita Patel's idol is Rahul Gandhi. |
| wada | 2 | *Somewhere in Delhi* Wife: "Promise karo kabhi mera transfer nahi hone doge" Husband: "Tum bhi wada karo roz mere liye rayta banaogi" |
| moms | 2 | nothing equivalent to moms . |
| feat | 2 | he's my dad but . . hum unhe pura match kabhi nhi dekhne dete . . it's a pretty big feat . . lol |
| kama | 2 | .SRKswarrior1 bas bata raha hu intolerance kya hota hai.. Yaha kama kha rahe hai aaraam se usme bhi chain nahi.. Baki tu samajdaar hai |
| doo | 2 | bhai Mujhe Apna twitter account password de doo pls :p :p :p :p :p :p |
| ooo | 2 | Aray bahi aao ooo na .......?? |
| gu | 2 | There's a hindi saying, shaana kauva gu khaata hai. |
| cba | 2 | cba for work this weekend , wana be a sloth on sunday with someUSER and someUSER |
| kiwi | 1 | Anoushey_a pak out ho chuka hai aus r kiwi se jeetna namomkin |
| dah | 1 | i'm excited to go to the knicks vs . lakers game in december thanks daddy you dah best |
| rama | 1 | On The Eve Of Mahashivratri Divine Satsang Of Shri Rama Bhai Took Place In Varanasi . | Asaramji Bapu |
| aum | 1 | Aum Namah Shivayah ShivaShiva Happy Mahashivratri to all . :) |
| ath | 1 | after today's bet came in i'm feeling confident with tomorrow's bet: ath madrid , juve , napoli , bayern munich , porto comeon |
| ary | 1 | Ary bhai love. Phr jb b awo gy aunga. Ap ko request byjta hun link mel gya. |
| wong | 1 | someUSER are u coming up the 17th .davis is playing hawaii for vball so we will see chris webb and scott wong .ur mom &amp |
| rag | 1 | are bhai tumne hum hostlers ki dukhti rag me haath rakh di . . . . missing famly . . . :( |
| hoy | 1 | friendlii_ghost network to aave chhe, Airtel jevu to nahi ke network ka j na hoy |
| salt | 1 | that means ur menu chart must also include salt n water . . . . hahaha |
| kp | 1 | NotSoSweetGirl_ Matlab KP me garmi hoti thi ? |
| kor | 1 | sadiatistic accha . akhon ghumanor try kor . onk rat hoise . |
| mit | 1 | A historic day in Indian politics Chal Gayee jhaadoo Mit gaya phool Modi pooche shah se Chote kya ho gayee Bhool ??? DelhiDecides |
| oral | 1 | Oral triple talaq is indeed irrational. Ek talaq lene ke liye teen bar "talaq" bolna padta hai. How absurd. |
| crib | 1 | Women can crib on things like bhaiyya ye shakkar bahot zyada meethi hai, koi aur quality dikhao. |
| mps | 1 | almost sabhi MPs ko malum tha ki NoteBandi hogi lekin public ko pta nhi tha to kaise kahe hum aazad hai ? |
| Γ¥ñ∩╕Å | 1 | RT ShraddhaKapoor : Abhi toh humne start kiya hai ! Presenting the BaaghiPoster . iTigerShroff BaaghiOffical ngemovies UTVfilms Γ¥ñ∩╕Å https : ΓÇª |
| hye | 1 | India kewal Pakistan ko dhamki deta hye .. aur ye dekho Trump ko ! |
| lay | 1 | sr ji 2 mnt xtra lay li....ab itne dr apko jyada baat krni.pdegi :* |
| ie | 1 | finna hit the grammys tomorrow then ima finna go thug it with someUSER live in my stomping grounds in the ie !grittygrindn |
| noh | 1 | Dis is how we noh sum ppl are illiterate here . D ignorant ones . Jinhe samajh kuch nahi aata bas bolna aata hai . Γ¼ç∩╕Å |
| flu | 1 | thanks to jesus , cvs , my mom & my mary . . . i was able to kick this flu in 1 week ! now to make it w/out my maryjane until monday ! struggles |

## Step 4 — Boundary check: length 5 classified ENGLISH (n=30)

Same procedure on the 1,199-token length-5 pool.

| TOKEN | FREQ | Example `Sentence_clean` |
|------:|-----:|--------------------------|
| after | 51 | nikon has once again proven it's a small world after all with the latest...- herald sun http/URL |
| level | 20 | ye AapGhumaKeLeLo aur AndColorPockeT alag level hai bhai, wahan nahi pahonch sakta koi! Alllahdin |
| jokes | 15 | timesn0w link bhejna mujhe bhi dekhna hai unka basis kya hai. Otherwise Pakistan is religiously tolerant in jokes only brownbrumby oirme |
| check | 15 | we daily go staff room to check that how many teachers are absent today ? ? ? ? ? |
| asked | 10 | RT helloanand : Brilliant answer by Dhoni when a media guy asked about his retirement - |
| hours | 4 | first 24 hours in london got given a free rail card ,saw 3 squirrels going to work ,may have found a home & there's big alan rickman posters |
| drunk | 4 | iamGunjanGrunge MaPoSe murder maaf kar sakta hai.. Drunk driving nahi |
| using | 4 | someUSER 9/9 account using your blackberry device , u may want to follow someUSER for updates and additional support from rim . |
| offer | 3 | offer hai bhai, waise bhi tikcets mehengi hai ye movie ke. Main toh dekhunga zaroor! |
| cries | 2 | He cries and cries and cries becoz u wnt let him do it ? Did you say you were seeing a \ " guy\ " ? ;) |
| inner | 2 | Modi channelising Inner Sonia Gandhi PowerIsPoison RT htTweets PM Modi: Satta mein ek nasha hain, bhagwan humain iss nashe se bachaye. |
| waist | 2 | we used to wear our sweaters around our waist or neck . . . mohabbatein style . . . shahrukh samajhte the khud ko :d |
| limit | 2 | Humne sarkar se kaha tha GST mein itne slabs nahi hone chahiye aur 18% par GST ka limit hona chahiye: RahulGandhi in Ahmedabad |
| samir | 2 | Jhonka hawa ka aaj bhi chhup ke hilaata hoga na Samir HawaKaJhonka BeingSalmanKhan |
| extra | 2 | amazon: extra strength hair nutrient tablets , 60-tablets (packaging may vary) by viviscal 649 days in the top 1 . . . http/UR |
| nokia | 2 | drpoonam Aap bade log ho, hum toh Nokia wale hai |
| combo | 1 | amazing concert tonight with jim white and the tcu jazz ensemble/faculty jazz combo ! don't miss tomorrow night . . . http/URL |
| salsa | 1 | victor cruz aint do the salsa all game . . . he's overdue . . . . its the 4th quarter . . . its time |
| badly | 1 | RT kchowdhury9 : boycottraees boycott badly raees |
| awwww | 1 | itsSSR anky1912 awwww happy birthday ankita lokhande na kar ke Chutti li h RahulOnLeave # balliawalebaba choriketweet -AD |
| circa | 1 | Goli maarni hai toh mujhay maaro ~ Nirupa Roy. Circa 1970s. |
| hogan | 1 | channel 4 30 years old on friday ! d'oh showed some great programmes over the years , especially paul hogan . |
| taker | 1 | RT Sharma_rajni29 : Gurmeetramrahim MSGappeals u r real care taker guru paa . hats off tu ur teachings ... |
| atari | 1 | atari 2600 - mere pass yeh system bhi tha jisme ek hi game thi - elevator action . . . . . na jaane kitne joysticks tode thi . . . . . . |
| gumbo | 1 | let the good times roll ! tomorrow is mardis gras at st . philip's , with the bob deangelis dixieland band and gumbo lunch . join us at 10:30 ! |
| sajid | 1 | LOL, aisa karna sense banta toh aaj tak Sajid Khan ki doosri movie kabhi ban hi nahi paati! |
| honor | 1 | broncos peyton manning named afc offensive player of the month . it's his 5th such honor , second to tom brady's 6 , tied w/ td . |
| sided | 1 | Ghar chale jao abhi vapas bangldesh 0 Totally 1 sided series it is 0 Dekhke maza nhi aara hai vijay pujara imVkohli gt a 200 again IndvBan |
| fancy | 1 | lahirip Arey abhi andar aur stock hai. Fancy main dikha dein ya daily use ka? |
| henry | 1 | postage for o . henry stamp unveiled: the u . s . postal service on monday unveiled the stamp commemorating the life of . . . http/URL |

## Boundary check verdict (Step 4 → Step 3)

Length-5 does NOT show a sharp drop-off in the *sample quality*: most length-5
samples are genuine English (after/level/check/asked/using/offer/…), and only a
few are Hinglish routed to ENGLISH (e.g. `lay` is not present here but `samir`,
`sajid`, `taker`, `sid` are borderline). However, the *rate* halves relative to
length ≤ 4 (22.8% vs ~35–56% of the bucket classified ENGLISH), and the
collision tokens at length 5 are proper nouns / rare words rather than high-
frequency Hinglish function words. The real danger zone is confirmed to be
**length ≤ 4**, dominated by high-frequency Hinglish function words such as
`thi` (162 rows), `jab` (149), `hue` (78), `band` (63), `ni` (61), `ham` (24).

## Recommended next step (not executed here)

Cannot be fixed in the router without changing it (forbidden this task). The
natural next artifact is a **collision override table** — an explicit
short-token → decision map (ENGLISH / HINGLISH / AMBIGUOUS) reviewed from this
sample plus the high-frequency tail of the danger zone, consumed by the Tier-1
normalization wiring rather than hardcoded into `token_router.py`.