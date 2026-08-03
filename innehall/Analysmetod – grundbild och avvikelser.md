# Analysmetod – grundbild och avvikelser

Så här analyseras partiernas AI-material, ett perspektiv i taget. Metoden är gjord för att kunna köras av en agent: ge den ett perspektiv, så producerar den en färdig analys enligt mönstret nedan.

Resultatet är råmaterial till en publik webbplats som sammanfattar vad partierna säger om AI. Texten ska därför vara **självbärande och skriven för en allmän läsare** – ingen ska behöva känna till vårt arbetsmaterial för att förstå den.

Perspektiven finns i arbetslistan `Perspektiv att analysera.md`. Källmaterialet finns i `../1 Källmaterial/` och kvaliteten per parti i `../1 Källmaterial/Status och källor.md`.

## Mönstret

Ett perspektiv analyseras isolerat. Resultatet har tre delar:

1. **Grundbild** – vad partierna som grupp säger. Obligatorisk.
2. **Avvikelser eller nyanser** – hur bilden bryts upp eller fördjupas. Frivillig.
3. **Underlag** – beläggen bakom, tänkt som en utfällbar ruta på webbplatsen.

Skrivregler för den publika texten (delarna Grundbild och Avvikelser/Nyanser):

- Skriv för en intresserad allmän läsare: konkret, klart, utan jargong.
- Håll texten **självbärande**. Inga interna hänvisningar – skriv aldrig om "hypoteser", "se nedan", "enligt enkäten", "öppen läsning" eller liknande. Läsaren ska mötas av vad partierna tycker, inte av hur vi arbetat.
- Håll det **kort**: grundbilden ca 500 tecken, och i regel inget avsnitt längre än ca 500 tecken. Underlag är undantaget och får bli längre.
- Källord som "enkätsvar", "motion" och "podd" hör hemma i Underlag, inte i brödtexten.

### Grundbilden

Ca 500 tecken. Den gemensamma nämnaren – den hållning som samlar flest partier.

- Den kan vara **tystnad**: att nästan ingen adresserar perspektivet är en fullgod grundbild och ofta själva poängen.
- Den får **göras bred** när det behövs för att samla tillräckligt många partier. Bredda formuleringen tills den rymmer den stora gruppen – men inte så vagt att den blir intetsägande.
- Den ska **inte tvingas fram**. Om partierna är för spretiga för att en ärlig gemensam nämnare ska gå att formulera, säg det rakt ut och beskriv i stället de tydligaste polerna.

### Avvikelser eller nyanser (frivilligt)

Behövs inte alltid. Om alla säger nästan samma sak räcker grundbilden – hoppa då över avsnittet eller konstatera kort att bilden är samstämmig. Annars styr en enkel fråga vilken rubrik som gäller: **ryms partierna fortfarande i grundbilden eller inte?**

- **Nyanser** – när partierna i grunden är överens och ryms i grundbilden, men lägger tyngdpunkten olika. Detta är normalfallet: komplettera grundbilden med nyanser i stället för att tvinga fram motpoler. (Reglering är ett bra exempel: alla vill ha riskbaserad EU-reglering, men hur hårt den ska hållas skiljer sig i grad. Även breda "poler" inom en gemensam hållning – t.ex. tillväxt kontra styrning när alla ändå är teknikpositiva – är nyanser, inte avvikelser.)
- **Avvikelser** – reserveras för partier vars hållning faktiskt faller *utanför* grundbilden, alltså bryter mot den gemensamma nämnaren. Använd bara när ett parti tar en position grundbilden inte rymmer.

Oavsett vilket: redovisa hållningar, inte partier – en hållning kan bäras av flera, gruppera dem. Sikta på högst två; fler bara om en sammanslagning skulle dölja något väsentligt. Varje punkt hålls kort. Namnge parti(er) och beskriv kortfattat hur de skiljer sig eller vad de betonar. Partier som varken bär grundbilden eller nämns förutsätts ligga inom den.

### Underlag (utfällbar ruta)

Beläggen bakom analysen, tänkt att på webbplatsen ligga i en ruta som läsaren kan fälla ut. De flesta bryr sig inte, men den ger trovärdighet och ett sätt att kontrollera. Här – och bara här – hör följande hemma:

- kompakta hänvisningar per parti: parti + vad de säger + källa (dokumenttyp).
- källtypsförbehåll: att en hållning bara vilar på podd/intervju (svagare belagt), eller kommer från en enskild ledamots motion snarare än partiets beslutade linje.
- att Moderaterna besvarade enkäten sent (partilinjen finns nu i enkätsvar, podd och motioner), men att AI ändå saknas i partiets egna programdokument och valmanifest.

Underlag får vara längre än 500 tecken.

## Så kör en agent detta

**Indata:** ett (1) perspektiv från arbetslistan, med dess beskrivning och interna förhandshypotes.

**Steg:**

1. Läs perspektivets beskrivning och lins-typ. Förhandshypotesen i arbetslistan är ett internt arbetsstöd – verifiera den mot materialet, och låt den aldrig synas i den färdiga texten.
2. Gå igenom källmaterialet parti för parti och fånga vad vart och ett faktiskt säger om perspektivet (och om det inte säger något – notera det). Håll källhierarkin: partiförfattat väger tyngre än enskild motion, som väger tyngre än podd.
3. Formulera grundbilden (ca 500 tecken), bredda vid behov, tvinga inte fram.
4. Avgör om bilden behöver avvikelser, nyanser eller inget alls.
5. Skriv Underlag med belägg och källförbehåll.
6. Skriv rent enligt utdataformatet – självbärande och inom teckengränserna.

**Utdataformat:**

```
# NN. Perspektivets namn

*Ursprung: … · Lins: … · Analyserad: ÅÅÅÅ-MM-DD*

## Grundbild

[Ca 500 tecken, självbärande.]

## Avvikelser

(eller "## Nyanser" – eller utelämna avsnittet helt om bilden är samstämmig)

- **[Parti / partier]:** [kort: hur de skiljer sig eller vad de betonar.]
- **[Parti / partier]:** [kort.]

## Underlag

- **[Parti]:** [vad de säger + källa/typ; källförbehåll där det behövs.]
- …
```

## Var resultatet sparas

En färdig perspektivanalys sparas som en egen md-fil i `perspektivanalyser/` (under `3 Analys/`).

- **Filnamn:** `NN Perspektivnamn.md`, där `NN` är perspektivets nummer i `Perspektiv att analysera.md` (nollfyllt: `01`, `02` …).
- **Innehåll:** rubrik med perspektivets namn, en metadatarad (ursprung · lins · analysdatum), `## Grundbild`, valfritt `## Avvikelser` eller `## Nyanser`, och `## Underlag`.

## Beslutsregler och fallgropar

- **Håll brödtexten publik och självbärande.** Inga interna referenser, inga källord i Grundbild/Avvikelser.
- **Tvinga inte fram symmetri eller motpoler.** Samstämmighet är ett giltigt resultat, och nyanser kan ersätta avvikelser.
- **Blanda inte ihop tystnad med hållning.** Ett parti som inget säger ska inte tilldelas en åsikt.
- **Källtypsförbehåll hör hemma i Underlag** – att något vilar på podd, på en enskild motion, eller att Moderaterna saknar besvarat underlag, nämns där, inte i brödtexten.
- **Enskilda ledamöter ≠ partiet.** Gör den skillnaden i Underlag.

## Källdisciplin

Varje påstående ska gå att spåra till en källfil. Brödtexten hålls ren och läsbar; beläggen och källtypsförbehållen samlas i Underlag. Analysen är empirisk och verifierbar – det är hela poängen med vinkeln.

## Två korta exempel

Nyanser är normalfallet – partierna ryms i grundbilden men betonar olika (perspektivet *Reglering*):

```
## Grundbild

Nästan alla partier vill ha en riskbaserad och teknikneutral reglering med EU som naturlig nivå. Skillnaden ligger inte i formen utan i hur hårt regleringen ska hållas.

## Nyanser

- **Lättare hand:** Moderaterna, Kristdemokraterna och Sverigedemokraterna betonar att inte reglera bort konkurrenskraften.
- **Hårdare tag:** Miljöpartiet och Piratpartiet ser reglering som ett demokratiskt värn och vill gå längre.
```

Avvikelser används först när något faller *utanför* grundbilden. Här är grundbilden tystnad, och en enda röst bryter den (perspektivet *Kontrollförlust och AGI-säkerhet*):

```
## Grundbild

Risken att AI:s egen förmågetillväxt leder till kontrollförlust är i praktiken frånvarande i partiernas AI-politik. Ingen gör den till en fråga.

## Avvikelser

- **Sverigedemokraterna:** en enskild företrädare har lyft frågan om avancerad AI som ett storskaligt, i förlängningen existentiellt hot – den enda gång temat berörs.
```
