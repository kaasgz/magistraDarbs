# Maģistra darba praktiskās daļas kods

Šis repozitorijs satur maģistra darba **"Optimizācijas algoritmu izvēle sporta turnīru kalendāru sastādīšanai, balstoties uz problēmas strukturālajām īpašībām"** praktiskās daļas kodu, reproducēšanas skriptus un lokālu UI pārskatu.

Projekts nav komerciāls produkts un nav pilnvērtīga sporta kalendāru sastādīšanas sistēma. Tas ir reproducējams eksperimentāls ietvars, kas ļauj pārbaudīt datu sagatavošanu, risinātāju portfeļa interpretāciju, algoritmu izvēles modeļa novērtējumu un maģistra darbā izmantotos artefaktus.

## Praktiskās daļas tvērums

Eksperiments pēta algoritmu izvēli sporta turnīru kalendāru sastādīšanai, izmantojot pirms risināšanas iegūstamas strukturālās pazīmes.

Galvenie fakti:

- datu kopa satur 234 instances;
- 54 instances ir reālas RobinX/ITC2021 tipa instances;
- 180 instances ir sintētiski ģenerētas instances;
- modelis izmanto 25 pirms-risināšanas strukturālās pazīmes;
- pazīmes raksturo instances izmēru, ierobežojumu sastāvu, blīvumu un daudzveidību;
- modelis ir nejaušo mežu klasifikators;
- novērtēšana veikta ar atkārtotu stratificētu krustoto pārbaudi, 3x3 jeb 9 pārbaudes sadalījumiem.

Risinātāju portfelī ir 4 reģistrēti risināšanas varianti:

- CP-SAT;
- simulētā rūdīšana;
- diagnostiskā atskaites pieeja;
- Timefold integrācijas saskarne.

Timefold šajā eksperimentālajā konfigurācijā nav aktīvs veiktspējas salīdzinājuma dalībnieks, jo ārējais izpildāmais fails nav konfigurēts. Diagnostiskā atskaites pieeja nav praktisks sporta kalendāra risinātājs. CP-SAT un simulētā rūdīšana ir atskaites risinātāji ar ierobežotu tvērumu, nevis pilns ITC2021 līmeņa risinātāju portfelis.

## Rezultātu interpretācija

`best_solver` netiek noteikts mehāniski tikai pēc mazākās mērķfunkcijas vērtības. Pirms izvēles tiek pārbaudīts, vai rezultāts ir derīgs, skaitliski novērtējams un interpretējams konkrētā risinātāja modelēšanas tvērumā.

Gala `best_solver` mērķī ir 2 aktīvas klases:

- reālajām instancēm: `simulated_annealing_solver`;
- sintētiskajām instancēm: `cpsat_solver`.

Rezultāti jāinterpretē piesardzīgi. Tie parāda algoritmu izvēles pieejas realizējamību konkrētajā eksperimentālajā uzstādījumā, nevis universālu algoritmu izvēles efektivitāti pilnvērtīgā ITC2021 risinātāju portfelī. Pašreizējā jauktajā datu kopā jāņem vērā datu avota efekts: labākais risinātājs cieši sakrīt ar datu izcelsmi. Nākamais spēcīgākais pārbaudes solis būtu `source-holdout` novērtēšana vai plašāka reālo instanču pārbaude.

## Repozitorija struktūra

- `configs/` - reproducējamās konfigurācijas.
- `data/raw/` - reālās un sintētiskās XML instances.
- `data/processed/` - apstrādātās datu kopas un pazīmju tabulas.
- `data/results/` - benchmark rezultāti, modeļa novērtējumi, tabulas un attēli.
- `atteli_latviski/` - UI pārskatā izmantoto attēlu kopijas latviskajai iesniegšanas mapei.
- `docs/` - reproducēšanas, metodoloģijas un audita dokumentācija.
- `src/` - parsēšana, pazīmju iegūšana, risinātāji, modeļa apmācība, rezultātu ģenerēšana un UI.
- `tests/` - automatizētās pārbaudes.

## Vides sagatavošana

Ieteicamā vide ir Python 3.12.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## UI palaišana

UI ir lokāls, lasīšanas režīma pārskats recenzentam vai darba vadītājam. Tas nepārrēķina rezultātus lapas ielādes brīdī.

```powershell
.\.venv\Scripts\python.exe -m src.web.app
```

Pēc palaišanas atvērt:

```text
http://127.0.0.1:8000/
```

Poga **Pārlādēt pārskatu** atkārtoti nolasa sagatavotos projekta artefaktus no diska. Tā nepalaiž benchmark, modeļa apmācību vai jaunu eksperimentu.

## Artefaktu atjaunošana

Pilna reproducēšanas secība ir dokumentēta [docs/reproduction_guide.md](docs/reproduction_guide.md). No repozitorija saknes gala artefaktus var atjaunot ar šādu komandu secību:

```powershell
.\.venv\Scripts\python.exe -m src.experiments.generate_synthetic_dataset --n 180 --seeds 42,43,44 --output-root data\raw\synthetic\study
.\.venv\Scripts\python.exe -m src.experiments.run_real_pipeline_current --config configs\real_pipeline_current.yaml
.\.venv\Scripts\python.exe -m src.experiments.build_solver_compatibility_matrix
.\.venv\Scripts\python.exe -m src.experiments.run_synthetic_study --config configs\synthetic_study.yaml
.\.venv\Scripts\python.exe -m src.selection.build_selection_dataset_full
.\.venv\Scripts\python.exe -m src.selection.train_selector --full-dataset
.\.venv\Scripts\python.exe -m src.selection.evaluate_selector --full-dataset
.\.venv\Scripts\python.exe -m src.experiments.thesis_report
.\.venv\Scripts\python.exe -m src.thesis.generate_assets
```

Ja nepieciešams atjaunot tikai tabulu, attēlu un UI metadatu artefaktus no jau sagatavotajiem rezultātiem:

```powershell
.\.venv\Scripts\python.exe -m src.thesis.generate_assets
```

## Galvenie iesniegšanas artefakti

- `data/processed/selection_dataset_full.csv`
- `data/results/full_selection/combined_benchmark_results.csv`
- `data/results/full_selection/selector_evaluation_summary.csv`
- `data/results/full_selection/feature_importance.csv`
- `data/results/thesis_tables/`
- `data/results/figures/`
- `atteli_latviski/`
- `docs/reproduction_guide.md`
- `docs/reproducibility_audit.md`

## Pārbaudes

Minimāla sintakses pārbaude:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src
```

UI un maģistra darba artefaktu pārbaudes:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_web_dashboard.py tests/test_thesis_plots.py -q
```

Pilna testu kopa:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Piezīme par GitHub iesniegšanu

Repozitorijs ir paredzēts koda, reproducēšanas instrukciju un maģistra darba praktiskās daļas pārskata iesniegšanai. Pirms publicēšanas jāpārbauda, vai reālo RobinX/ITC2021 instanču iekļaušana atbilst attiecīgo datu izplatīšanas noteikumiem.
