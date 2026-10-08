# Thuisbatterij-simulator
Schat de **toekomstige winst of het verlies** van een thuisbatterij door je **historische verbruiksdata** (Fluvius, kwartiertotalen) te gebruiken. De app simuleert wat er **in diezelfde periode** zou gebeurd zijn **alsof** je de gekozen batterij al had: per kwartier laden uit overtollige injectie, ontladen bij afname, en vergelijken van kosten met en zonder batterij (inclusief Vlaams **capaciteitstarief** / kwartierpiek).

Dat is een **indicatie op basis van het verleden**, geen garantie voor de komende jaren.

## Hoe je het resultaat leest

- **Besparing / terugverdientijd:** als je verbruikspatroon en tarieven ongeveer gelijk blijven, geeft de berekende jaarlijkse besparing een ruwe orde van grootte voor de toekomst.
- **Vergelijkingstabel:** totale netafname, injectie, energiekost, kwartierpiek-kost en totale kost over de geüploade periode — zonder vs met batterij.
- **Grafieken:** laadstatus, netafnamevermogen en stromen over de simulatieperiode.

## Limitaties

- **Geen voorspelling:** toekomstig verbruik (warmtepomp, EV, gezinsgrootte), zonne-opbrengst, weer en regelgeving kunnen afwijken van de historiek.
- **Vaste stroomprijs:** één gemiddelde €/kWh voor afname en één voor teruglevering; geen uur- of kwartierprijzen, geen dynamisch contract, geen onbalanskosten.
- **Geen markt- of beleidsmodel:** geen inschatting van toekomstige prijzen, prosumententarief, capaciteitstarief-wijzigingen of nieuwe heffingen.
- **Kwartierresolutie:** data en simulatie lopen per **15 minuten**; kortere pieken en fijne timing (bijv. binnen het kwartier) zitten er niet in.
- **Idealiseerde batterij:** efficiëntie, max. vermogen en SOC-grenzen volgens jouw parameters; geen gedetailleerd omvormer-/EMS-gedrag, geen exportlimiet of netoperator-regels.
- **Capaciteitstarief vereenvoudigd:** gemiddelde maandpiek op gesimuleerde netafname, ondergrens 2,5 kW, tarief netbeheerder in €/kW/jaar; niet de volledige Fluvius-factuur (kWh-nettarief, databeheer, maximumtarief, …).
- **Investering:** presetprijzen zijn indicatief; geen financiering, onderhoud, degradatie of restwaarde.
- **Datakwaliteit:** ontbrekende kwartieren worden 0; fouten in de export of niet-geactiveerde kwartierregistratie beïnvloeden het resultaat.

## Installatie en starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open de app in je browser (meestal `http://localhost:8501`). **Upload** je Fluvius CSV, kies een batterijpreset of **Aangepast**, stel tarieven in en klik op **Simulatie uitvoeren**.

## Online (Streamlit Community Cloud)

1. Publiceer deze map als GitHub-repo (zonder persoonlijke CSV-bestanden).
2. Ga naar [share.streamlit.io](https://share.streamlit.io), koppel GitHub en deploy met **Main file path:** `app.py`.
3. Gebruikers uploaden hun eigen export via de app; er zijn geen bestanden op de server nodig.

De upload blijft in je browsersessie; sla geen verbruiksdata op in de repo.

<a id="csv-export"></a>

## Verbruikshistoriek exporteren via Mijn Fluvius

De simulator verwacht het officiële Fluvius-exportbestand met **kwartiertotalen**, bv. `Verbruikshistoriek_elektriciteit_<EAN>_<start>_<eind>_kwartiertotalen.csv`.

### Vereisten

- Een **digitale elektriciteitsmeter** (afname én injectie per kwartier).
- Toegang tot [Mijn Fluvius](https://mijn.fluvius.be) (itsme, eID of andere Fluvius-inlogmethode).
- **Kwartierwaarden** moeten geregistreerd worden. Bij sommige meters moet je die registratie eerst activeren in het portaal; vanaf dan bouwt Fluvius een historiek op. Vanaf 2026 worden kwartierwaarden voor elektriciteit standaard uitgelezen. Meer uitleg: [Fluvius – kwartierwaarden](https://www.fluvius.be/nl/factuur-en-tarieven/kwartierwaarden).

### Stappen

1. Ga naar **https://mijn.fluvius.be** en meld je aan.
2. Open **Verbruik** in het menu.
3. Klik bij je **digitale elektriciteitsmeter** op **Details** (of vergelijkbare link naar het verbruiksoverzicht).
4. Klik op **Historiek downloaden** (soms via een export- of downloadicoon in het verbruiksscherm).
5. In het dialoogvenster:
   - **Detailniveau:** kies **Kwartiertotalen** (niet enkel dag- of maandtotalen).
   - **Periode:** selecteer de **langst mogelijke periode** (idealiter 12 volle maanden of meer) zodat pieken en zomer/winter mee tellen.
6. Klik op **Downloaden**. Het genereren kan even duren.
7. Upload het `.csv`-bestand in de app via **Fluvius CSV** (drag & drop).

Het bestand bevat o.a. kolommen `Register` (Afname Dag/Nacht, Injectie Dag/Nacht), `Volume` (kWh) en tijdstempels per kwartier. Persoonlijke verbruiksdata horen **niet** in git; `.gitignore` sluit `Verbruikshistoriek_*.csv` uit.

### Problemen?

- Geen kwartierdata? Controleer in Mijn Fluvius of kwartierregistratie actief is.
- Lege of ontbrekende volumes aan het einde van de periode? Dat komt voor bij recente dagen; de simulator vult ontbrekende kwartieren met 0 kWh.
- Hulp bij Mijn Fluvius: [Verbruik opvolgen | Fluvius](https://www.fluvius.be/nl/meters-en-meterstanden/verbruik-opvolgen).

## Wat de simulator technisch doet

- **Energiekost:** netafname × stroomprijs minus injectie × terugleververgoeding (met vs zonder batterij).
- **Kwartierpiek / capaciteitstarief:** gemiddelde van de hoogste maandelijkse kwartierpieken op netafname (kW), minimum **2,5 kW**, × tarief netbeheerder (€/kW/jaar).
- **Vergelijkingstabel** en **zoombare grafieken** (SOC, netvermogen, stromen).
- **Terugverdientijd:** investering gedeeld door geschatte jaarlijkse besparing over de geüploade periode.

Presetprijzen voor bekende thuisbatterijen zijn indicatief (incl. installatie waar van toepassing); pas aan via **Aangepast** of na het kiezen van een preset.

Presets met prefix **`[Gids]`** zijn plug-in modellen van [Thuisbatterijgids](https://thuisbatterijgids.net/thuisbatterij/) (31 geteste batterijen plus extra modellen op die site). Prijs = hardware “vanaf”; RTE onbekend → 85% aangenomen; laad-/ontlaadefficiëntie = √(RTE).
