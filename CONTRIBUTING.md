# Att föreslå ändringar

Tack för att du vill bidra. Sajten byggs ur markdown-filerna i det här repot, så alla ändringar görs i md – inte i `index.html` (den genereras).

## Enklaste vägen (ingen git-kunskap behövs)

1. Öppna filen du vill ändra här på GitHub:
   - analystexter i `innehall/` (t.ex. `Områdessynteser.md` eller en perspektivanalys),
   - källmaterial i `kallor/`.
2. Klicka på pennan (Edit) uppe till höger.
3. Gör din ändring och klicka **Propose changes**. GitHub skapar automatiskt en kopia (fork) och en pull request.
4. Beskriv kort vad du ändrat.

## Vad som hör hemma var

- `innehall/Områdessynteser.md` – de sex frågornas grundbild och "Här skiljer de sig".
- `innehall/perspektivanalyser/` – de arton perspektiven (grundbild, nyanser/avvikelser, underlag med källor).
- `innehall/partier/Intro.md` – ramtexterna på fliken Partierna: ingressen överst och noten ovanför Piratpartiet. Rader som inleds med `>` blir en mindre not.
- `innehall/partier/` – de nio partiporträtten (ingress utan rubrik, Så ställer de sig, Utmärkande drag, Där de tiger, Underlag, Källor). Källor listas som sökvägar relativt `kallor/`, en per rad.
- `innehall/Ramtexter – inledning och syntes.md` – inledningen, och under `## Sajthuvud` sajtens överrubrik, rubrik och ingress (en rad var, etiketten före kolon ska stå kvar).
- `innehall/Analysmetod – grundbild och avvikelser.md` – hur analysen görs.
- `innehall/Om.md` – om-sidan. I avsnittet "Vilka vi är" blir varje stycke på formen `Namn: kort beskrivning` automatiskt ett porträttkort. Bilden hämtas ur `bilder/` från namnet i gemener med bindestreck (Maria Ottosson → `bilder/maria-ottosson.jpg`); saknas bilden visas kortet utan foto. Använd gärna kvadratiska bilder, de beskärs till cirklar.
- `innehall/Källor.md` – texterna och grupperingen på fliken Källor. Varje `## `-avsnitt är en grupp; `Mapp:` pekar ut mappen i `kallor/` vars filer listas automatiskt, och rader som inleds med `>` blir gruppens not.
- `kallor/` – primärkällorna. Rätta gärna transkriberingsfel, men ändra inte innebörden i ett partis egna ord. Nya filer i en mapp dyker upp på sajten automatiskt.

## Stil

- Självbärande, publik text för en allmän läsare. Inga interna hänvisningar.
- Håll påståenden nära källan – varje påstående ska gå att spåra till en källa i `kallor/`.

Efter att en pull request slagits samman bygger projektets underhållare om sajten.
