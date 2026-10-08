# Thuisbatterij-simulator

Simuleer winst of verlies van een thuisbatterij op basis van Fluvius-kwartierdata (afname en injectie), inclusief het Vlaamse **capaciteitstarief** (kwartierpiek).

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

## Wat de simulator doet

- **Energiekost:** afname × stroomprijs minus injectie × terugleververgoeding.
- **Kwartierpiek / capaciteitstarief:** gemiddelde van de hoogste maandelijkse kwartierpieken (afnamevermogen in kW), minimum **2,5 kW**, × tarief netbeheerder (€/kW/jaar).
- **Vergelijkingstabel** zonder / met batterij en **zoombare grafieken** (laadstatus, netafname, stromen).
- **Terugverdientijd** op basis van jaarlijkse besparing t.o.v. investeringskost en gekozen levensduur.

Presetprijzen voor bekende thuisbatterijen zijn indicatief (incl. installatie waar van toepassing); pas aan via **Aangepast** of na het kiezen van een preset.
