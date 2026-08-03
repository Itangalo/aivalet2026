#!/usr/bin/env python3
"""Bygg sajten för "Partiernas AI-politik" ur md-källorna.

Läser ramtexterna (inledning + syntes) och de 18 perspektivanalyserna i
`3 Analys/` och producerar:

- `index.html`  – hela sajten (flikar: Analysen, Källor, Om)
- `innehall.md` – allt innehåll i en fil (LLM-vänligt)

Kör från projektets `4 Sajt/`-mapp:  python3 bygg_sajt.py
Sajten byggs alltid om från källorna, så redigera aldrig index.html för hand –
ändra i md-filerna och kör om skriptet.
"""

import html
import os
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Två layouter stöds med samma kod:
#  - Repo-layout (self-contained, t.ex. GitHub Pages): innehall/ + kallor/ ligger
#    bredvid skriptet, och sajten byggs direkt hit med lokala kallor/-länkar.
#  - Dev-layout (i kunskapsbasen): skriptet ligger i "4 Sajt/" och läser ur
#    "3 Analys/" och "1 Källmaterial/".
REPO_LAYOUT = (HERE / "innehall").is_dir() and (HERE / "kallor").is_dir()
if REPO_LAYOUT:
    ANALYS = HERE / "innehall"
    KALLOR = HERE / "kallor"
else:
    ROOT = HERE.parent
    ANALYS = ROOT / "3 Analys"
    KALLOR = ROOT / "1 Källmaterial"
PERSP = ANALYS / "perspektivanalyser"
PARTIER = ANALYS / "partier"

# ---------------------------------------------------------------------------
# Kluster: hur de 18 perspektiven grupperas, med en brygga som leder läsningen.
# ---------------------------------------------------------------------------
CLUSTERS = [
    ("Utgångspunkt", [1],
     "Var partierna börjar: grundhållningen till AI och hur högt Sverige siktar."),
    ("Vad AI ska göra – och för vem", [2, 3, 4],
     "Från principer till praktik – vad tekniken ska användas till, och vem som ska vinna på den."),
    ("Hur AI ska styras", [5, 6, 7],
     "Reglering, oberoende och den beredskap partierna faktiskt bygger upp."),
    ("Individens skydd och rättigheter", [8, 9, 10, 11],
     "När AI möter den enskilda: integritet, rättssäkerhet, likabehandling och upphovsrätt."),
    ("Demokrati", [12, 13],
     "AI:s påverkan på det offentliga samtalet – och på vårt eget tänkande."),
    ("Särskilda hänsyn", [14, 15],
     "Två frågor som lätt faller mellan stolarna: barnen och klimatet."),
    ("Det stora och det osagda", [16, 17, 18],
     "De mest långtgående konsekvenserna – och materialets tydligaste tystnader."),
]

# Spotify-avsnitt (AI Sweden-podden). Från tidigare kartläggning.
SPOTIFY = {
    "Socialdemokraterna": "https://open.spotify.com/episode/6rAkteSviAZFMu8xbik8R8",
    "Moderaterna": "https://open.spotify.com/episode/75PYBCY4aNte27ehrCDh5b",
    "Centerpartiet": "https://open.spotify.com/episode/3CdZLF8QieoXofnJf1uNNt",
    "Vänsterpartiet": "https://open.spotify.com/episode/3Mj1sOfkw4U7D7yDODrSDR",
    "Kristdemokraterna": "https://open.spotify.com/episode/4Z8GZ7ApOU1w91SmJBNu6G",
    "Liberalerna": "https://open.spotify.com/episode/6F1M1OLNo6edQKRk93m8Ct",
    "Miljöpartiet": "https://open.spotify.com/episode/2q5xLfJlgltjqwsGoNcVjy",
}

SEP = '<span class="sep">·</span>'
PARTY_ORDER = ["S", "M", "SD", "C", "V", "KD", "L", "MP"]
PARTY_FULL = {
    "S": "Socialdemokraterna", "M": "Moderaterna", "SD": "Sverigedemokraterna",
    "C": "Centerpartiet", "V": "Vänsterpartiet", "KD": "Kristdemokraterna",
    "L": "Liberalerna", "MP": "Miljöpartiet",
}


# ---------------------------------------------------------------------------
# Markdown → inline-HTML (bara det vi använder: **fet**, *kursiv*, "citat")
# ---------------------------------------------------------------------------
def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def blocks(raw: str):
    """Dela en textklump i block: ('p', text) eller ('ul', [items])."""
    out = []
    para_lines, list_items = [], []

    def flush_para():
        nonlocal para_lines
        if para_lines:
            out.append(("p", " ".join(para_lines).strip()))
            para_lines = []

    def flush_list():
        nonlocal list_items
        if list_items:
            out.append(("ul", list_items))
            list_items = []

    for line in raw.splitlines():
        s = line.strip()
        if not s:
            flush_para(); flush_list(); continue
        if s.startswith("- "):
            flush_para()
            list_items.append(s[2:].strip())
        else:
            flush_list()
            para_lines.append(s)
    flush_para(); flush_list()
    return out


def render_blocks(raw: str) -> str:
    parts = []
    for kind, val in blocks(raw):
        if kind == "p":
            parts.append(f"<p>{inline(val)}</p>")
        else:
            lis = "".join(f"<li>{inline(i)}</li>" for i in val)
            parts.append(f"<ul>{lis}</ul>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Parsning
# ---------------------------------------------------------------------------
def split_sections(text: str):
    """Dela ett md-dokument på '## '-rubriker → dict(rubrik → kropp)."""
    sections, cur, buf = {}, None, []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            if cur is not None:
                sections[cur] = "\n".join(buf).strip()
            cur, buf = m.group(1).strip(), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        sections[cur] = "\n".join(buf).strip()
    return sections


def parse_ramtexter():
    text = (ANALYS / "Ramtexter – inledning och syntes.md").read_text(encoding="utf-8")
    secs = split_sections(text)
    inledning = secs.get("Inledning", "")
    syntes_raw = secs.get("Syntes", "")
    # Syntes har ### underrubriker
    sub = []
    cur, buf = None, []
    for line in syntes_raw.splitlines():
        m = re.match(r"^###\s+(.*)$", line)
        if m:
            if cur is not None:
                sub.append((cur, "\n".join(buf).strip()))
            cur, buf = m.group(1).strip(), []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        sub.append((cur, "\n".join(buf).strip()))
    return inledning, sub


SAJTHUVUD_STANDARD = {
    "överrubrik": "Riksdagspartierna + Piratpartiet · inför valet 2026",
    "rubrik": "Vad säger partierna om AI?",
    "ingress": ("En empirisk genomgång av vad partierna faktiskt skriver och säger om AI – "
                "ordnad i sex frågor, med arton analyserade perspektiv och primärkällorna "
                "under varje."),
}


def parse_sajthuvud():
    """Läs sajtens rubriktexter ur '## Sajthuvud' i ramtextfilen.

    Formatet är en rad per text: 'Överrubrik: …', 'Rubrik: …', 'Ingress: …'.
    Saknas avsnittet eller en rad används standardtexten, så att sajten alltid
    går att bygga.
    """
    huvud = dict(SAJTHUVUD_STANDARD)
    path = ANALYS / "Ramtexter – inledning och syntes.md"
    if not path.exists():
        return huvud
    body = split_sections(path.read_text(encoding="utf-8")).get("Sajthuvud", "")
    for line in body.splitlines():
        m = re.match(r"^\s*(Överrubrik|Rubrik|Ingress)\s*:\s*(.+?)\s*$", line)
        if m:
            huvud[m.group(1).lower()] = m.group(2)
    return huvud


def parse_perspektiv(num: int):
    path = next(PERSP.glob(f"{num:02d} *.md"))
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    h1 = next(l for l in lines if l.startswith("# "))
    title = re.sub(r"^#\s+\d+\.\s*", "", h1).strip()
    secs = split_sections(text)
    grundbild = secs.get("Grundbild", "")
    if "Nyanser" in secs:
        var_label, var_body = "Nyanser", secs["Nyanser"]
    elif "Avvikelser" in secs:
        var_label, var_body = "Avvikelser", secs["Avvikelser"]
    else:
        var_label, var_body = None, ""
    underlag = secs.get("Underlag", "")
    return {
        "num": num, "title": title, "grundbild": grundbild,
        "var_label": var_label, "var_body": var_body, "underlag": underlag,
    }


def parse_omraden():
    """Läs Områdessynteser.md → lista med de sex frågorna (solfjäderns revben)."""
    text = (ANALYS / "Områdessynteser.md").read_text(encoding="utf-8")
    areas = []
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        lines = block.splitlines()
        question = lines[0].strip()
        body = "\n".join(lines[1:])
        m = re.search(r"^###\s+Här skiljer de sig\s*$", body, flags=re.M)
        if m:
            grund, skiljer = body[:m.start()], body[m.end():]
        else:
            grund, skiljer = body, ""
        pm = re.search(r"^Perspektiv:\s*(.+)$", grund, flags=re.M)
        nums = []
        if pm:
            nums = [int(x) for x in re.findall(r"\d+", pm.group(1))]
            grund = grund[:pm.start()] + grund[pm.end():]
        areas.append({"question": question, "nums": nums,
                      "grundbild": grund.strip(), "skiljer": skiljer.strip()})
    return areas


def parse_partier():
    """Läs partier/NN Parti.md → lista med partiporträtt.

    Filformat: H1 = partinamn, kursiv metadatarad (Kortnamn · riksdagsstatus),
    därefter en ingress utan rubrik, och sedan '## '-avsnitten Så ställer de sig,
    Utmärkande drag, Där de tiger, Underlag och Källor. Källor listar sökvägar
    relativt källmaterialsmappen, en per rad.
    """
    parties = []
    if not PARTIER.is_dir():
        return parties
    for path in sorted(PARTIER.glob("[0-9][0-9] *.md")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        name = next(l for l in lines if l.startswith("# "))[2:].strip()

        # Allt före första '## ' är metadatarad + ingress.
        rest = "\n".join(lines[1:])
        m = re.search(r"^##\s", rest, flags=re.M)
        head = rest[:m.start()] if m else rest
        kort, i_riksdagen = "", True
        meta = re.search(r"^\*(.+?)\*\s*$", head, flags=re.M)
        if meta:
            km = re.search(r"Kortnamn:\s*([^\s·]+)", meta.group(1))
            kort = km.group(1) if km else ""
            i_riksdagen = "utanför riksdagen" not in meta.group(1).lower()
            head = head[:meta.start()] + head[meta.end():]

        secs = split_sections(text)
        kallor = [ln[2:].strip() for ln in secs.get("Källor", "").splitlines()
                  if ln.strip().startswith("- ")]
        parties.append({
            "namn": name, "kort": kort, "i_riksdagen": i_riksdagen,
            "ingress": head.strip(),
            "stallning": secs.get("Så ställer de sig", ""),
            "utmarkande": secs.get("Utmärkande drag", ""),
            "tystnad": secs.get("Där de tiger", ""),
            "underlag": secs.get("Underlag", ""),
            "kallor": kallor,
        })
    return parties


# ---------------------------------------------------------------------------
# Källor
# ---------------------------------------------------------------------------
# Publiceringsläge: när PUBLISH är på pekar källänkar mot en lokal, självbärande
# kallor/-mapp (i stället för ../1 Källmaterial), pdf:er utelämnas, och de källor
# som faktiskt länkas samlas i COPIED för att kopieras med i exporten.
# I repo-layout är sajten redan självbärande, så publiceringsläget är default på.
PUBLISH = REPO_LAYOUT
COPIED = set()


def href(path: Path) -> str:
    if PUBLISH:
        try:
            rel = path.relative_to(KALLOR)
            COPIED.add(path)
            return "kallor/" + "/".join(urllib.parse.quote(s) for s in rel.parts)
        except ValueError:
            pass
    rel = os.path.relpath(path, HERE)
    return "/".join(urllib.parse.quote(seg) for seg in rel.split(os.sep))


def file_links(mdpath: Path) -> str:
    """md-länk + ev. pdf-länk för en källa (pdf utelämnas i publiceringsläge)."""
    links = [f'<a href="{href(mdpath)}">md</a>']
    pdf = mdpath.with_suffix(".pdf")
    if pdf.exists() and not PUBLISH:
        links.insert(0, f'<a href="{href(pdf)}">PDF</a>')
    return SEP.join(links)


def source_group(title, folder, note=None):
    d = KALLOR / folder
    if not d.exists():
        return ""
    items = sorted(p for p in d.glob("*.md") if p.name != "README.md" and not p.name.startswith("_"))
    rows = []
    for p in items:
        label = html.escape(p.stem)
        rows.append(f'<li><span class="src-label">{label}</span>'
                    f'<span class="src-links">{file_links(p)}</span></li>')
    note_html = f'<p class="rowspan-note">{note}</p>' if note else ""
    return (f'<h3 class="grouphead">{html.escape(title)}</h3>'
            f'{note_html}<ul class="srclist">{"".join(rows)}</ul>')


def podd_group():
    d = KALLOR / "Podd – AI Sweden"
    rows = []
    for party in ["Socialdemokraterna", "Moderaterna", "Centerpartiet", "Vänsterpartiet",
                  "Kristdemokraterna", "Liberalerna", "Miljöpartiet"]:
        p = d / f"AI Sweden - {party}.md"
        if not p.exists():
            continue
        links = []
        if party in SPOTIFY:
            links.append(f'<a href="{SPOTIFY[party]}" target="_blank" rel="noopener">Spotify</a>')
        links.append(f'<a href="{href(p)}">Transkript</a>')
        joined = SEP.join(links)
        rows.append(f'<li><span class="src-label">{html.escape(party)}</span>'
                    f'<span class="src-links">{joined}</span></li>')
    note = ("Transkripten är AI-genererade (KB-Whisper), inte officiella – verifiera mot ljudet vid citat. "
            "Sverigedemokraterna och Piratpartiet saknas i podden.")
    return (f'<h3 class="grouphead">AI Sweden-podden</h3>'
            f'<p class="rowspan-note">{note}</p><ul class="srclist">{"".join(rows)}</ul>')


def riksdag_group():
    d = KALLOR / "Riksdagsdokument"
    by_party = {p: [] for p in PARTY_ORDER}
    for p in sorted(d.glob("*.md")):
        if p.name.startswith("_"):
            continue
        m = re.match(r"^([A-ZÅÄÖ]+)\s+-\s+(.*)$", p.stem)
        if not m:
            continue
        party = m.group(1)
        by_party.setdefault(party, []).append((m.group(2), p))
    inner = []
    for party in PARTY_ORDER:
        docs = by_party.get(party) or []
        if not docs:
            continue
        rows = "".join(
            f'<li><span class="src-label">{html.escape(label)}</span>'
            f'<span class="src-links">{file_links(p)}</span></li>'
            for label, p in docs)
        inner.append(f'<p class="party-sub">{PARTY_FULL[party]} '
                     f'<span class="cnt">{len(docs)} dokument</span></p>'
                     f'<ul class="srclist">{rows}</ul>')
    note = ("Systematiskt svep av riksdagsdokument med AI i titeln (2021/22–2025/26). "
            "De flesta är enskilda motioner – de visar tänkandet inom partierna, inte beslutad politik. "
            "Kristdemokraterna och Liberalerna saknar helt dokument med AI i titeln.")
    return (f'<h3 class="grouphead">Riksdagsdokument</h3>'
            f'<p class="rowspan-note">{note}</p>'
            f'<details class="riksdag"><summary>Visa alla riksdagsdokument</summary>'
            f'<div class="riksdag-body">{"".join(inner)}</div></details>')


# ---------------------------------------------------------------------------
# HTML-bygge
# ---------------------------------------------------------------------------
def render_perspektiv_card(p):
    """En perspektivruta: grundbild + nyanser/avvikelser + utfällbart underlag."""
    parts = [f'<article class="perspektiv" id="p{p["num"]}">',
             f'<span class="pnum">Perspektiv {p["num"]}</span>',
             f'<h4>{inline(p["title"])}</h4>',
             f'<div class="grundbild">{render_blocks(p["grundbild"])}</div>']
    if p["var_label"]:
        cls = "avvikelser" if p["var_label"] == "Avvikelser" else "nyanser"
        parts.append(f'<div class="variation {cls}">')
        parts.append(f'<span class="vlabel">{p["var_label"]}</span>')
        parts.append(render_blocks(p["var_body"]))
        parts.append('</div>')
    parts.append('<details class="underlag"><summary>Underlag och källor</summary>')
    parts.append(f'<div class="underlag-body">{render_blocks(p["underlag"])}</div>')
    parts.append('</details></article>')
    return "\n".join(parts)


def build_analys_panel(inledning, areas, perspektiv):
    out = ['<div class="panel active" id="analysen">']

    # Inledning
    out.append('<section class="intro">')
    out.append(render_blocks(inledning))
    out.append('</section>')

    # Översiktskarta – de sex frågorna som klickbara ankare
    out.append('<nav class="oversikt" aria-label="De sex frågorna">')
    out.append('<p class="oversikt-label">Sex frågor</p>')
    out.append('<ol>')
    for i, a in enumerate(areas, 1):
        out.append(f'<li><a href="#omrade-{i}">{inline(a["question"])}</a></li>')
    out.append('</ol>')
    out.append('</nav>')

    # De sex frågorna (solfjädern)
    out.append('<section class="omraden">')
    for i, a in enumerate(areas, 1):
        title_attr = html.escape(a["question"], quote=True)
        out.append(f'<section class="omrade" id="omrade-{i}" data-num="{i}" data-title="{title_attr}">')
        out.append('<div class="fraga-head">')
        out.append(f'<span class="fraga-num">{i}</span>')
        out.append(f'<h2 class="fraga">{inline(a["question"])}</h2>')
        out.append('</div>')
        out.append(f'<div class="omrade-grund">{render_blocks(a["grundbild"])}</div>')
        if a["skiljer"]:
            out.append('<div class="skiljer">')
            out.append('<span class="skiljer-label">Här skiljer de sig</span>')
            out.append(render_blocks(a["skiljer"]))
            out.append('</div>')
        nums = a["nums"]
        if nums:
            if len(nums) == 1:
                count_txt, tail = "1 analyserat perspektiv", ", med källhänvisning"
            else:
                count_txt = f"{len(nums)} analyserade perspektiv"
                tail = ", samtliga med källhänvisningar"
            out.append('<details class="perspektiv-foldout">')
            out.append(f'<summary>Bygger på <span class="count">{count_txt}</span>{tail}</summary>')
            out.append('<div class="perspektiv-lista">')
            for pn in nums:
                out.append(render_perspektiv_card(perspektiv[pn]))
            out.append('</div>')
            out.append('</details>')
        out.append('</section>')
    out.append('</section>')

    out.append('</div>')
    return "\n".join(out)


def riksdag_docs(kort):
    """Riksdagsdokument för ett parti, utifrån filnamnens partiprefix."""
    d = KALLOR / "Riksdagsdokument"
    if not kort or not d.is_dir():
        return []
    out = []
    for p in sorted(d.glob("*.md")):
        if p.name.startswith("_"):
            continue
        m = re.match(r"^([A-ZÅÄÖ]+)\s+-\s+(.*)$", p.stem)
        if m and m.group(1) == kort:
            out.append((m.group(2), p))
    return out


def render_parti_card(pt):
    """Ett partiporträtt: ingress + sex frågor + krok + tystnad + utfällbart underlag."""
    anchor = f'parti-{(pt["kort"] or pt["namn"]).lower()}'
    parts = [f'<article class="parti" id="{anchor}" data-num="{html.escape(pt["kort"], quote=True)}"'
             f' data-title="{html.escape(pt["namn"], quote=True)}">', '<div class="parti-head">']
    if pt["kort"]:
        parts.append(f'<span class="pkort">{inline(pt["kort"])}</span>')
    parts.append(f'<h3>{inline(pt["namn"])}</h3>')
    parts.append('</div>')
    if pt["ingress"]:
        parts.append(f'<div class="parti-ingress">{render_blocks(pt["ingress"])}</div>')
    for cls, label, body in [("stallning", "Så ställer de sig", pt["stallning"]),
                             ("utmarkande", "Utmärkande drag", pt["utmarkande"]),
                             ("tystnad", "Där de tiger", pt["tystnad"])]:
        if not body:
            continue
        parts.append(f'<div class="parti-sekt {cls}">')
        parts.append(f'<span class="slabel">{label}</span>')
        parts.append(render_blocks(body))
        parts.append('</div>')

    parts.append('<details class="underlag"><summary>Underlag och källor</summary>')
    parts.append('<div class="underlag-body">')
    if pt["underlag"]:
        parts.append(render_blocks(pt["underlag"]))
    rows = []
    for rel in pt["kallor"]:
        p = KALLOR / rel
        if not p.exists():
            continue
        label = p.stem
        links = []
        if p.parent.name == "Podd – AI Sweden":
            party = label.replace("AI Sweden - ", "")
            label = f"Poddintervju ({p.parent.name.split(' – ')[1]})"
            if party in SPOTIFY:
                links.append(f'<a href="{SPOTIFY[party]}" target="_blank" rel="noopener">Spotify</a>')
            links.append(f'<a href="{href(p)}">Transkript</a>')
        else:
            label = f"{p.parent.name}: {label}"
            links.append(file_links(p))
        rows.append(f'<li><span class="src-label">{html.escape(label)}</span>'
                    f'<span class="src-links">{SEP.join(links)}</span></li>')
    docs = riksdag_docs(pt["kort"])
    if docs:
        rows.append(f'<li><span class="src-label">Riksdagsdokument med AI i titeln</span>'
                    f'<span class="src-links">{len(docs)} st, se fliken Källor</span></li>')
    if rows:
        parts.append(f'<ul class="srclist">{"".join(rows)}</ul>')
    parts.append('</div></details></article>')
    return "\n".join(parts)


def build_partier_panel(parties):
    out = ['<div class="panel" id="partier">']
    out.append('<p class="panel-intro">Samma material sett parti för parti. Varje porträtt '
               'sammanfattar var partiet står i de sex frågorna, vad som är dess egen krok, '
               'och var det tiger. Tystnad är inte en hållning – där underlaget är tunt eller '
               'indirekt sägs det ut, och beläggen ligger under "Underlag och källor".</p>')
    out.append('<p class="rowspan-note">En del av materialet kommer från en enkät där alla '
               'partier fick samma fem frågor. Svaren speglar därför vad de tillfrågades om, '
               'inte nödvändigtvis vad de själva prioriterar – väg in det när flera partier '
               'tar upp samma sak.</p>')
    riksdag = [p for p in parties if p["i_riksdagen"]]
    ovriga = [p for p in parties if not p["i_riksdagen"]]

    # Innehållsförteckning – de nio partierna som klickbara ankare.
    out.append('<nav class="oversikt oversikt-partier" aria-label="De nio partierna">')
    out.append('<p class="oversikt-label">Nio partier</p>')
    out.append('<ul>')
    for p in parties:
        anchor = f'parti-{(p["kort"] or p["namn"]).lower()}'
        kort = f'<span class="ov-kort">{inline(p["kort"])}</span>' if p["kort"] else ""
        out.append(f'<li><a href="#{anchor}">{kort}{inline(p["namn"])}</a></li>')
    out.append('</ul>')
    out.append('</nav>')
    if riksdag:
        out.append('<h3 class="grouphead">Riksdagspartierna</h3>')
        out.extend(render_parti_card(p) for p in riksdag)
    if ovriga:
        out.append('<h3 class="grouphead">Utanför riksdagen</h3>')
        out.append('<p class="rowspan-note">Piratpartiet sitter inte i riksdagen och kom med '
                   'i undersökningen senare. Det är en värdefull jämförelsepunkt, men bör '
                   'hållas isär från riksdagspartierna.</p>')
        out.extend(render_parti_card(p) for p in ovriga)
    out.append('</div>')
    return "\n".join(out)


def build_kallor_panel():
    out = ['<div class="panel" id="kallor">']
    out.append('<p class="panel-intro">Alla primärkällor bakom analysen, öppet redovisade. '
               'Varje källa finns som redigerbar markdown; där det finns en officiell länk '
               'anges den också. Analysen ska gå att kontrollera mot källan.</p>')
    out.append(source_group("Enkätsvar 2026", "Enkätsvar 2026",
               "Nio partier har besvarat samma fem frågor. Moderaterna inkom sist, i augusti 2026."))
    out.append(source_group("Valmanifest och plattformar 2026", "Valmanifest 2026"))
    out.append(source_group("Parti- och principprogram", "Parti- och principprogram"))
    out.append(source_group("EU-valmanifest 2024", "EU-valmanifest 2024"))
    out.append(source_group("Partiernas webbsidor om AI", "Webbsidor om AI"))
    out.append(podd_group())
    out.append(riksdag_group())
    out.append('</div>')
    return "\n".join(out)


BILDER = HERE / "bilder"
PERSON_SEKTION = "Vilka vi är"


def person_slug(namn):
    """'Maria Ottosson' → 'maria-ottosson' (för att hitta bilder/<slug>.jpg)."""
    s = namn.strip().lower()
    for a, b in (("å", "a"), ("ä", "a"), ("ö", "o"), ("é", "e"), ("ü", "u")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def person_card(namn, beskrivning):
    """Porträtt i om-sidans 'Vilka vi är': cirkelbild (om den finns) + namn + rad."""
    parts = ['<figure class="person">']
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        img = BILDER / f"{person_slug(namn)}{ext}"
        if img.exists():
            src = "bilder/" + urllib.parse.quote(img.name)
            parts.append(f'<img src="{src}" alt="{html.escape(namn, quote=True)}" '
                         f'width="132" height="132" loading="lazy">')
            break
    parts.append('<figcaption>')
    parts.append(f'<span class="person-namn">{inline(namn)}</span>')
    parts.append(f'<span class="person-om">{inline(beskrivning)}</span>')
    parts.append('</figcaption></figure>')
    return "\n".join(parts)


def render_om_md(text):
    """Liten md-renderare för om-sidan: '# ' → sektionsrubrik, '## ' → underrubrik,
    '> ' → liten not, övrigt → stycken (med inline fet/kursiv/länk).

    I avsnittet 'Vilka vi är' blir stycken på formen 'Namn: beskrivning' i stället
    porträttkort, med bilden hämtad ur bilder/<namn-i-gemener>.jpg om den finns.
    """
    parts, para, personer = [], [], []
    i_personsektion = False

    def flush_personer():
        if personer:
            parts.append('<div class="personer">')
            parts.extend(personer)
            parts.append('</div>')
            personer.clear()

    def flush():
        if not para:
            return
        stycke = " ".join(para)
        para.clear()
        m = re.match(r"^([^:]{2,48}):\s+(.+)$", stycke)
        if i_personsektion and m and not m.group(1).startswith(("[", "*")):
            personer.append(person_card(m.group(1).strip(), m.group(2).strip()))
        else:
            flush_personer()
            parts.append(f'<p>{inline(stycke)}</p>')

    for line in text.splitlines():
        s = line.strip()
        if not s:
            flush()
        elif s.startswith("# "):
            flush(); flush_personer(); i_personsektion = False
            parts.append(f'<h2 class="sectionhead">{inline(s[2:])}</h2>')
        elif s.startswith("## "):
            flush(); flush_personer()
            i_personsektion = s[3:].strip() == PERSON_SEKTION
            parts.append(f'<h3 class="syntes-sub">{inline(s[3:])}</h3>')
        elif s.startswith("> "):
            flush(); flush_personer(); parts.append(f'<p class="rowspan-note">{inline(s[2:])}</p>')
        else:
            para.append(s)
    flush(); flush_personer()
    return "\n".join(parts)


def build_om_panel():
    om_file = ANALYS / "Om.md"
    if om_file.exists():
        return ('<div class="panel" id="om">\n  <section class="intro">\n'
                + render_om_md(om_file.read_text(encoding="utf-8"))
                + '\n  </section>\n</div>')
    # Fallback (om Om.md saknas, t.ex. i äldre dev-layout)
    return """<div class="panel" id="om">
  <section class="intro">
    <h2 class="sectionhead">Om projektet</h2>
    <p>Den här sajten kartlägger vad riksdagspartierna och Piratpartiet säger – och inte säger –
    om artificiell intelligens inför valet hösten 2026. Utgångspunkten är empirisk: vad partierna
    faktiskt har skrivit och sagt, sammanställt i arton perspektiv med primärkällorna öppet redovisade.</p>

    <h3 class="syntes-sub">Varför</h3>
    <p>AI pekas ut som en av de mest avgörande frågorna för samhället – av forskning, näringsliv och
    partierna själva. Ändå är den påfallande frånvarande i valrörelsen. Vi ville göra det gjorda jobbet:
    gå igenom allt material och visa mönstret, så att väljare kan se var partierna står och var de tiger.</p>

    <h3 class="syntes-sub">Så gjordes analysen</h3>
    <p>Arbetet med att samla in, sammanställa och analysera materialet har i stor utsträckning gjorts
    med hjälp av AI, under mänsklig ledning och granskning. Varje slutsats vilar på angivna källor,
    som redovisas under respektive perspektiv och samlat under fliken Källor. Anser företrädare för
    något parti att partiets hållning beskrivs på fel sätt är de välkomna att höra av sig, så rättar vi.</p>

    <h3 class="syntes-sub">Vilka vi är</h3>
    <p><em>[Platshållare – kort om gruppen bakom sajten.]</em></p>

    <h3 class="syntes-sub">Kontakt</h3>
    <p><em>[Platshållare – e-post och ev. övriga kontaktvägar.]</em></p>

    <p class="rowspan-note">Allt innehåll finns också samlat i en enda fil:
    <a href="innehall.md">innehall.md</a> – tänkt att vara lätt att arbeta med för både människor och språkmodeller.</p>
  </section>
</div>"""


def build_html(inledning, areas, perspektiv, parties=()):
    css = CSS
    analys = build_analys_panel(inledning, areas, perspektiv)
    partier = build_partier_panel(parties) if parties else ""
    kallor = build_kallor_panel()
    om = build_om_panel()
    partier_tab = ('<button class="tab" data-panel="partier">Partierna</button>'
                   if parties else "")
    huvud = parse_sajthuvud()
    sidtitel = html.escape(huvud["rubrik"])
    overrubrik = inline(huvud["överrubrik"])
    ingress = inline(huvud["ingress"])
    # Håll ihop rubrikens sista ord med det näst sista, så att inte ett kort ord
    # (t.ex. "AI?") blir ensamt på en egen rad.
    rubrik = inline(huvud["rubrik"])
    if rubrik.count(" ") >= 1:
        head, _, tail = rubrik.rpartition(" ")
        rubrik = f"{head}&nbsp;{tail}"
    party_bar = ('<div class="area-bar" id="partyBar" data-panel="partier" '
                 'data-items="article.parti">\n'
                 '      <a href="#parti-s"><span class="ab-num"></span>'
                 '<span class="ab-title"></span></a>\n    </div>') if parties else ""
    return f"""<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{sidtitel}</title>
<style>
{css}
</style>
</head>
<body>
<div class="wrap">

  <header class="hero">
    <p class="kicker">{overrubrik}</p>
    <h1>{rubrik}</h1>
    <p class="lede">{ingress}</p>
  </header>

  <div class="topbar">
    <nav class="tabs">
      <button class="tab active" data-panel="analysen">Analysen</button>
      {partier_tab}
      <button class="tab" data-panel="kallor">Källor</button>
      <button class="tab" data-panel="om">Om</button>
    </nav>
    <div class="area-bar" id="areaBar" data-panel="analysen" data-items=".omrade">
      <a href="#omrade-1"><span class="ab-num"></span><span class="ab-title"></span></a>
    </div>
    {party_bar}
  </div>

{analys}

{partier}

{kallor}

{om}

  <footer>Sammanställt {DATE} · underlaget uppdateras löpande inför valet</footer>

</div>

<script>
  document.querySelectorAll('.tab').forEach(function (tab) {{
    tab.addEventListener('click', function () {{
      document.querySelectorAll('.tab').forEach(function (t) {{ t.classList.remove('active'); }});
      document.querySelectorAll('.panel').forEach(function (p) {{ p.classList.remove('active'); }});
      tab.classList.add('active');
      document.getElementById(tab.dataset.panel).classList.add('active');
      window.scrollTo({{ top: 0, behavior: 'smooth' }});
      updateAreaBar();
    }});
  }});

  // Sticky-rad: visar vilken fråga (respektive vilket parti) läsaren är i
  // medan hen scrollar. En rad per flik, samma logik för alla.
  var bars = Array.prototype.slice.call(document.querySelectorAll('.area-bar')).map(function (bar) {{
    return {{
      el: bar,
      num: bar.querySelector('.ab-num'),
      title: bar.querySelector('.ab-title'),
      link: bar.querySelector('a'),
      panel: document.getElementById(bar.dataset.panel),
      items: Array.prototype.slice.call(document.querySelectorAll(bar.dataset.items))
    }};
  }});
  var ticking = false;

  function updateAreaBar() {{
    bars.forEach(function (bar) {{
      if (!bar.panel || !bar.panel.classList.contains('active')) {{
        bar.el.classList.remove('visible');
        return;
      }}
      var line = 100, active = null;
      for (var i = 0; i < bar.items.length; i++) {{
        if (bar.items[i].getBoundingClientRect().top <= line) active = bar.items[i];
      }}
      if (active) {{
        bar.num.textContent = active.dataset.num || '';
        bar.title.textContent = active.dataset.title || '';
        bar.link.setAttribute('href', '#' + active.id);
        bar.el.classList.add('visible');
      }} else {{
        bar.el.classList.remove('visible');
      }}
    }});
  }}

  window.addEventListener('scroll', function () {{
    if (!ticking) {{
      window.requestAnimationFrame(function () {{ updateAreaBar(); ticking = false; }});
      ticking = true;
    }}
  }});
  updateAreaBar();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# innehall.md (LLM-vänlig helhet)
# ---------------------------------------------------------------------------
def build_markdown(inledning, areas, perspektiv, parties=()):
    out = ["# Vad säger partierna om AI?", "",
           "En empirisk genomgång inför valet 2026. Sammanställd ur källmaterialet i "
           "`1 Källmaterial/`. Denna fil speglar sajten och genereras av `4 Sajt/bygg_sajt.py`.",
           "", "## Inledning", "", inledning.strip(), ""]
    for a in areas:
        out += [f"## {a['question']}", "", a["grundbild"].strip(), ""]
        if a["skiljer"]:
            out += ["**Här skiljer de sig**", "", a["skiljer"].strip(), ""]
        n = len(a["nums"])
        label = ("1 analyserat perspektiv" if n == 1 else f"{n} analyserade perspektiv")
        out += [f"*Bygger på {label}, med källor:*", ""]
        for pn in a["nums"]:
            p = perspektiv[pn]
            out += [f"### {pn}. {p['title']}", "", p["grundbild"].strip(), ""]
            if p["var_label"]:
                out += [f"*{p['var_label']}*", "", p["var_body"].strip(), ""]
            out += ["<details><summary>Underlag och källor</summary>", "",
                    p["underlag"].strip(), "", "</details>", ""]
    if parties:
        out += ["## Partierna", "",
                "Samma material sett parti för parti: var partiet står i de sex frågorna, "
                "dess egen krok, och var det tiger.", ""]
        for pt in parties:
            head = pt["namn"] + (f" ({pt['kort']})" if pt["kort"] else "")
            out += [f"### {head}", ""]
            if not pt["i_riksdagen"]:
                out += ["*Utanför riksdagen.*", ""]
            if pt["ingress"]:
                out += [pt["ingress"].strip(), ""]
            for label, body in [("Så ställer de sig", pt["stallning"]),
                                ("Utmärkande drag", pt["utmarkande"]),
                                ("Där de tiger", pt["tystnad"])]:
                if body:
                    out += [f"**{label}**", "", body.strip(), ""]
            out += ["<details><summary>Underlag och källor</summary>", "",
                    pt["underlag"].strip(), ""]
            if pt["kallor"]:
                out += ["Källor:", ""] + [f"- {k}" for k in pt["kallor"]] + [""]
            out += ["</details>", ""]
    return "\n".join(out).rstrip() + "\n"


# ---------------------------------------------------------------------------
CSS = r"""
  :root {
    --bg: #f7f6f3; --card: #ffffff; --ink: #1c1c1a; --muted: #5f5c56;
    --line: #e4e1da; --accent: #1a5f5a; --accent-soft: #e7f0ef;
    --flag: #b3541e; --flag-soft: #f6e9df; --maxw: 800px;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #16171a; --card: #1e2024; --ink: #eceae5; --muted: #a3a09a;
      --line: #33353b; --accent: #6fc8bf; --accent-soft: #1c2c2b;
      --flag: #e08a54; --flag-soft: #2c2320;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: Georgia, 'Iowan Old Style', 'Times New Roman', serif;
    line-height: 1.65; -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: var(--maxw); margin: 0 auto; padding: 0 22px 90px; }
  header.hero { padding: 58px 0 22px; }
  .kicker {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.72rem; letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--accent); font-weight: 600; margin: 0 0 14px;
  }
  h1 { font-size: 2.5rem; line-height: 1.1; margin: 0 0 18px; letter-spacing: -0.01em; }
  .lede { font-size: 1.14rem; color: var(--muted); margin: 0; max-width: 62ch; }
  /* Tabs */
  .topbar { position: sticky; top: 0; z-index: 10; background: var(--bg); }
  .tabs {
    display: flex; gap: 6px; border-bottom: 1px solid var(--line);
    margin: 4px 0 0; padding-top: 8px;
  }
  .area-bar { display: none; border-bottom: 1px solid var(--line); }
  .area-bar.visible { display: block; }
  .area-bar a {
    display: block; padding: 9px 2px; text-decoration: none;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.85rem; line-height: 1.3;
  }
  .area-bar .ab-num {
    color: var(--accent); font-weight: 700; margin-right: 9px;
  }
  .area-bar .ab-title { color: var(--ink); }
  .tab {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.95rem; font-weight: 600; color: var(--muted); background: none;
    border: none; border-bottom: 2px solid transparent; padding: 12px 14px;
    cursor: pointer; margin-bottom: -1px;
  }
  .tab:hover { color: var(--ink); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
  .panel { display: none; }
  .panel.active { display: block; }
  /* Body text */
  section.intro { margin: 30px 0 10px; }
  section.intro p { font-size: 1.12rem; margin: 0 0 18px; }
  .sectionhead {
    font-size: 1.9rem; letter-spacing: -0.01em; margin: 52px 0 6px;
    padding-top: 26px; border-top: 1px solid var(--line);
  }
  .sectionlede { color: var(--muted); font-size: 1.05rem; margin: 0 0 22px; max-width: 60ch; }
  .syntes p { font-size: 1.08rem; margin: 0 0 16px; }
  .syntes-sub {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 1.02rem; font-weight: 700; letter-spacing: 0.01em;
    margin: 26px 0 10px; color: var(--ink);
  }
  /* Översiktskarta */
  .oversikt {
    margin: 30px 0 10px; padding: 20px 24px;
    border: 1px solid var(--line); border-radius: 12px; background: var(--card);
  }
  .oversikt-label {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.72rem; letter-spacing: 0.12em; text-transform: uppercase;
    color: var(--muted); font-weight: 700; margin: 0;
  }
  .oversikt ol { margin: 12px 0 0; padding-left: 1.5em; }
  .oversikt li { margin-bottom: 9px; font-size: 1.06rem; }
  .oversikt li::marker { color: var(--accent); font-weight: 700; }
  .oversikt a {
    color: var(--ink); text-decoration: none;
    border-bottom: 1px solid var(--accent-soft);
  }
  .oversikt a:hover { border-bottom-color: var(--accent); color: var(--accent); }
  /* Områden (solfjädern) */
  .omraden { margin-top: 8px; }
  .omrade {
    margin: 44px 0; padding-top: 32px; border-top: 2px solid var(--line);
    scroll-margin-top: 104px;
  }
  .fraga-head { display: flex; align-items: center; gap: 18px; margin: 0 0 18px; }
  .fraga-num {
    flex: none; width: 58px; height: 58px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: var(--accent-soft); color: var(--accent);
    border: 2px solid var(--accent);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 1.7rem; font-weight: 700; font-variant-numeric: tabular-nums;
  }
  h2.fraga {
    font-size: 1.85rem; line-height: 1.15; letter-spacing: -0.01em;
    margin: 0; color: var(--accent); flex: 1;
  }
  .omrade-grund p { font-size: 1.1rem; margin: 0 0 14px; }
  .omrade-grund p:last-child { margin-bottom: 0; }
  .skiljer {
    margin: 20px 0 4px; padding: 16px 20px 8px;
    background: var(--accent-soft); border-radius: 10px;
  }
  .skiljer-label {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--accent);
  }
  .skiljer ul { margin: 10px 0 0; padding-left: 20px; }
  .skiljer li { font-size: 1.02rem; margin-bottom: 10px; line-height: 1.5; }
  .skiljer p { font-size: 1.02rem; margin: 10px 0 6px; }
  details.perspektiv-foldout { margin-top: 18px; }
  details.perspektiv-foldout > summary {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.9rem; color: var(--muted); cursor: pointer;
    list-style: none; padding: 8px 0;
  }
  details.perspektiv-foldout > summary::-webkit-details-marker { display: none; }
  details.perspektiv-foldout > summary::before {
    content: "▸"; color: var(--accent); display: inline-block;
    font-size: 1.6em; line-height: 1; vertical-align: middle;
    margin-right: 11px; position: relative; top: -1px;
  }
  details.perspektiv-foldout[open] > summary::before { content: "▾"; }
  details.perspektiv-foldout > summary .count {
    color: var(--accent); font-weight: 600; border-bottom: 1px solid var(--line);
  }
  details.perspektiv-foldout[open] > summary { margin-bottom: 6px; }
  .perspektiv-lista { padding-left: 16px; border-left: 2px solid var(--accent-soft); }
  /* Perspektiv-kort */
  article.perspektiv {
    background: var(--card); border: 1px solid var(--line); border-radius: 12px;
    padding: 24px 28px; margin: 14px 0;
  }
  .pnum {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.74rem; font-weight: 700; color: var(--accent);
    letter-spacing: 0.06em; text-transform: uppercase;
  }
  article.perspektiv h4 { font-size: 1.3rem; line-height: 1.22; margin: 5px 0 14px; }
  .grundbild p { margin: 0 0 12px; font-size: 1.06rem; }
  .grundbild p:last-child { margin-bottom: 0; }
  .variation {
    margin-top: 16px; padding: 14px 16px 6px; border-radius: 9px;
    background: var(--accent-soft);
  }
  .variation.avvikelser { background: var(--flag-soft); }
  .vlabel {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--accent);
  }
  .variation.avvikelser .vlabel { color: var(--flag); }
  .variation ul { margin: 8px 0 0; padding-left: 20px; }
  .variation li { font-size: 1.0rem; margin-bottom: 8px; line-height: 1.5; }
  .variation p { font-size: 1.0rem; margin: 10px 0 6px; }
  details.underlag { margin-top: 16px; border-top: 1px solid var(--line); padding-top: 10px; }
  details.underlag summary {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.85rem; font-weight: 600; color: var(--muted); cursor: pointer;
    list-style: none;
  }
  details.underlag summary::-webkit-details-marker { display: none; }
  details.underlag summary::before {
    content: "▸"; color: var(--accent); display: inline-block;
    font-size: 1.4em; line-height: 1; vertical-align: middle; margin-right: 9px;
  }
  details.underlag[open] summary::before { content: "▾"; }
  .underlag-body { margin-top: 10px; }
  .underlag-body ul { padding-left: 18px; margin: 0; }
  .underlag-body li {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.9rem; color: var(--muted); margin-bottom: 9px; line-height: 1.5;
  }
  /* Om-sidans porträtt */
  .personer {
    display: grid; gap: 30px 20px; margin: 24px 0 10px;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }
  figure.person { margin: 0; text-align: center; }
  figure.person img {
    width: 132px; height: 132px; border-radius: 50%; object-fit: cover;
    display: block; margin: 0 auto 12px; background: var(--accent-soft);
    box-shadow: 0 0 0 1px var(--line), 0 2px 10px rgba(0, 0, 0, 0.07);
    filter: grayscale(1); transition: filter 0.5s ease, box-shadow 0.5s ease;
  }
  figure.person:hover img, figure.person:focus-within img {
    filter: grayscale(0); box-shadow: 0 0 0 2px var(--accent), 0 3px 14px rgba(0, 0, 0, 0.12);
  }
  .person-namn {
    display: block; font-weight: 700; font-size: 1.02rem; line-height: 1.3;
    margin-bottom: 5px;
  }
  .person-om {
    display: block; color: var(--muted); line-height: 1.45;
    max-width: 24ch; margin: 0 auto;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.86rem;
  }
  /* Pekskärmar saknar hover – visa bilderna i färg direkt. */
  @media (hover: none) {
    figure.person img { filter: grayscale(0); }
  }
  @media (prefers-reduced-motion: reduce) {
    figure.person img { transition: none; }
  }
  /* Partiporträtt */
  .oversikt-partier ul {
    list-style: none; margin: 12px 0 0; padding: 0;
    display: grid; gap: 8px 18px;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  }
  .oversikt-partier li { font-size: 1.02rem; }
  .oversikt-partier a { display: flex; align-items: baseline; gap: 9px; }
  .ov-kort {
    flex: none; min-width: 2.1em; text-align: center; color: var(--accent);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.74rem; font-weight: 700; letter-spacing: 0.05em;
    border: 1px solid var(--line); border-radius: 4px; padding: 1px 4px;
  }
  article.parti {
    background: var(--card); border: 1px solid var(--line); border-radius: 12px;
    padding: 26px 28px; margin: 20px 0; scroll-margin-top: 104px;
  }
  .parti-head { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; }
  .pkort {
    flex: none; min-width: 44px; height: 44px; padding: 0 10px; border-radius: 22px;
    display: flex; align-items: center; justify-content: center;
    background: var(--accent-soft); color: var(--accent); border: 2px solid var(--accent);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 1.05rem; font-weight: 700; letter-spacing: 0.02em;
  }
  article.parti h3 { font-size: 1.55rem; line-height: 1.15; margin: 0; letter-spacing: -0.01em; }
  .parti-ingress p {
    font-size: 1.14rem; line-height: 1.5; margin: 0 0 12px; color: var(--ink);
  }
  .parti-ingress p:last-child { margin-bottom: 0; }
  .parti-sekt { margin-top: 18px; padding: 14px 18px 6px; border-radius: 9px; }
  .parti-sekt.stallning { background: var(--accent-soft); }
  .parti-sekt.utmarkande { border: 1px solid var(--line); padding-bottom: 12px; }
  .parti-sekt.tystnad { background: var(--flag-soft); }
  .slabel {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: var(--accent);
  }
  .parti-sekt.tystnad .slabel { color: var(--flag); }
  .parti-sekt ul { margin: 10px 0 0; padding-left: 20px; }
  .parti-sekt li { font-size: 1.0rem; margin-bottom: 10px; line-height: 1.5; }
  .parti-sekt p { font-size: 1.02rem; margin: 10px 0 6px; }
  article.parti .underlag-body p {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.9rem; color: var(--muted); line-height: 1.55; margin: 0 0 10px;
  }
  article.parti .underlag-body .srclist { margin-top: 6px; }
  /* Källor */
  .panel-intro { font-size: 1.05rem; color: var(--muted); margin: 26px 0 8px; max-width: 64ch; }
  h3.grouphead { font-size: 1.4rem; margin: 40px 0 6px; letter-spacing: -0.005em; }
  ul.srclist { list-style: none; padding: 0; margin: 12px 0 0; }
  ul.srclist li {
    display: flex; justify-content: space-between; gap: 16px; align-items: baseline;
    padding: 11px 0; border-bottom: 1px solid var(--line);
  }
  .src-label { font-size: 0.98rem; }
  .src-links {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    white-space: nowrap; font-size: 0.85rem;
  }
  .srclist a, .panel-intro a, .intro a {
    color: var(--accent); text-decoration: none; border-bottom: 1px solid transparent;
  }
  .srclist a:hover { border-bottom-color: var(--accent); }
  .sep { color: var(--line); margin: 0 5px; }
  .rowspan-note {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.85rem; color: var(--muted); margin: 6px 0 0; max-width: 64ch; line-height: 1.5;
  }
  details.riksdag { margin-top: 12px; }
  details.riksdag > summary {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.9rem; font-weight: 600; color: var(--accent); cursor: pointer;
  }
  .party-sub {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-weight: 700; font-size: 0.98rem; margin: 22px 0 0;
  }
  .party-sub .cnt { color: var(--muted); font-weight: 400; font-size: 0.85rem; }
  footer {
    margin-top: 50px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 0.82rem; color: var(--muted); text-align: center;
  }
"""

DATE = "juli 2026"


# Redigerbara källtexter som följer med i den publika exporten (inga interna
# arbetsdokument, inga namngivna processnoteringar).
SOURCE_FILES = [
    "Områdessynteser.md",
    "Ramtexter – inledning och syntes.md",
    "Analysmetod – grundbild och avvikelser.md",
]


def export_public(dest):
    """Bygg en självbärande, kurerad kopia för publik hosting (GitHub Pages)."""
    global PUBLISH, COPIED
    dest = Path(dest)
    PUBLISH, COPIED = True, set()
    try:
        inledning, _ = parse_ramtexter()
        areas = parse_omraden()
        perspektiv = {n: parse_perspektiv(n) for n in range(1, 19)}
        parties = parse_partier()
        html_out = build_html(inledning, areas, perspektiv, parties)
        md_out = build_markdown(inledning, areas, perspektiv, parties)
        copied = sorted(COPIED)
    finally:
        PUBLISH = False

    dest.mkdir(parents=True, exist_ok=True)
    (dest / "index.html").write_text(html_out, encoding="utf-8")
    (dest / "innehall.md").write_text(md_out, encoding="utf-8")

    # Källfiler som Källor-fliken länkar (md, inga pdf) → dest/kallor/
    for p in copied:
        target = dest / "kallor" / p.relative_to(KALLOR)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)

    # Redigerbara källtexter → dest/innehall/
    src = dest / "innehall"
    (src / "perspektivanalyser").mkdir(parents=True, exist_ok=True)
    for f in sorted(PERSP.glob("*.md")):
        shutil.copy2(f, src / "perspektivanalyser" / f.name)
    if PARTIER.is_dir():
        (src / "partier").mkdir(parents=True, exist_ok=True)
        for f in sorted(PARTIER.glob("*.md")):
            shutil.copy2(f, src / "partier" / f.name)

    # Porträttbilder till om-sidan
    if BILDER.is_dir():
        (dest / "bilder").mkdir(parents=True, exist_ok=True)
        for f in sorted(BILDER.iterdir()):
            if f.is_file() and not f.name.startswith("."):
                shutil.copy2(f, dest / "bilder" / f.name)
    for name in SOURCE_FILES:
        shutil.copy2(ANALYS / name, src / name)

    print(f"Exporterade till {dest} – {len(copied)} källfiler, {len(list(PERSP.glob('*.md')))} perspektivfiler")
    return dest, copied


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--export":
        export_public(sys.argv[2])
        return
    inledning, _syntes = parse_ramtexter()
    areas = parse_omraden()
    perspektiv = {n: parse_perspektiv(n) for n in range(1, 19)}
    parties = parse_partier()
    (HERE / "index.html").write_text(
        build_html(inledning, areas, perspektiv, parties), encoding="utf-8")
    (HERE / "innehall.md").write_text(
        build_markdown(inledning, areas, perspektiv, parties), encoding="utf-8")
    print(f"Byggde index.html och innehall.md ({len(areas)} frågor, "
          f"{len(perspektiv)} perspektiv, {len(parties)} partier)")


if __name__ == "__main__":
    main()
