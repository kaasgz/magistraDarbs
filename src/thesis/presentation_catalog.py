"""Shared presentation metadata for thesis-facing tables, figures, and sections."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PresentationSection:
    """One dashboard section shown in the presentation-ready UI."""

    identifier: str
    title: str
    intro: str


@dataclass(frozen=True, slots=True)
class FigureSpec:
    """One thesis-facing figure and its explanatory metadata."""

    identifier: str
    file_name: str
    section_id: str
    title: str
    description: str
    meaning: str


PRESENTATION_SECTIONS: tuple[PresentationSection, ...] = (
    PresentationSection(
        identifier="overview",
        title="Kopsavilkums",
        intro=(
            "Sadaļa rāda praktiskās daļas pārbaudei vajadzīgos galvenos skaitļus. Tā sasaista datu kopu, "
            "strukturālās pazīmes, risinātāju portfeli un validāciju ar darba eksperimentālo uzstādījumu. "
            "Interpretācijā jāņem vērā, ka sintētiskās instances veido lielāko datu kopas daļu."
        ),
    ),
    PresentationSection(
        identifier="workflow",
        title="Eksperimenta process",
        intro=(
            "Sadaļa rāda atkārtojamo eksperimenta plūsmu no datu avotiem līdz interpretācijai. Tā atbilst "
            "praktiskajā daļā aprakstītajai XML nolasīšanai, pazīmju iegūšanai, risinātāju izpildei un "
            "modeļa novērtēšanai. Ierobežojums: šī plūsma pārbauda konkrētu eksperimentālo konfigurāciju."
        ),
    ),
    PresentationSection(
        identifier="results",
        title="Nejaušo mežu klasifikatora novērtēšana",
        intro=(
            "Sadaļa rāda Random Forest jeb nejaušo mežu klasifikatora novērtējuma rādītājus. Tā saistās ar "
            "darba modeli, kas apmācīts uz pirms-risināšanas strukturālajām pazīmēm un salīdzināts ar SBS/VBS "
            "atskaites punktiem. Ierobežojums: no augstas precizitātes vien nevar izdarīt vispārīgus secinājumus."
        ),
    ),
    PresentationSection(
        identifier="solver",
        title="Risinātāju lomas",
        intro=(
            "Sadaļa rāda portfelī reģistrēto četru risināšanas variantu lomas un interpretācijas tvērumu. Tā "
            "saistās ar praktiskās daļas atskaites risinātājiem un statusu apstrādi. Ierobežojums: Timefold "
            "šajā konfigurācijā nav aktīvs veiktspējas salīdzinājuma dalībnieks."
        ),
    ),
    PresentationSection(
        identifier="best_solver",
        title="best_solver klašu sadalījums",
        intro=(
            "Sadaļa rāda gala best_solver klašu sadalījumu pa datu avotiem. Tā pārbauda, kā praktiskās daļas "
            "mērķa mainīgais izveidots pēc derīgu un interpretējamu risinātāju rezultātu atlases. Ierobežojums: "
            "pašreizējā jauktajā datu kopā labākais risinātājs cieši sakrīt ar datu avotu."
        ),
    ),
    PresentationSection(
        identifier="features",
        title="Strukturālo pazīmju nozīmīgums",
        intro=(
            "Sadaļa rāda modelim pieejamo strukturālo pazīmju nozīmīgumu. Tā saistās ar "
            "praktiskajā daļā definēto prasību izmantot tikai pirms risināšanas zināmu informāciju. Ierobežojums: "
            "pazīmju nozīmīgums jālasa kopā ar jauktās datu kopas izcelsmes efektu."
        ),
    ),
    PresentationSection(
        identifier="datasets",
        title="Datu grupu rādītāji",
        intro=(
            "Sadaļa rāda novērtējuma rādītājus atsevišķi reālajām un sintētiskajām instancēm. Tā saistās ar "
            "darba praktiskās daļas piesardzīgo rezultātu lasījumu pa datu avotiem. Ierobežojums: datu avoti nav "
            "pilnīgi līdzsvaroti pēc izcelsmes."
        ),
    ),
    PresentationSection(
        identifier="methodology",
        title="Interpretācija un ierobežojumi",
        intro=(
            "Sadaļa apkopo, kā rezultāti jāinterpretē aizstāvēšanā un pārbaudē. Tā saistās ar praktiskās daļas "
            "secinājumu par algoritmu izvēles pieejas realizējamību konkrētajā uzstādījumā. Ierobežojums: "
            "nepieciešams source-holdout vai plašāka reālo instanču pārbaude."
        ),
    ),
    PresentationSection(
        identifier="implementation",
        title="Artefakti un reproducēšana",
        intro=(
            "Sadaļa rāda praktiskās daļas reproducēšanai izmantotos failus, tabulas, attēlus un dokumentus. Tā "
            "saistās ar darba prasību nodrošināt pārbaudāmu eksperimentālo sistēmu. Ierobežojums: šie artefakti "
            "apraksta eksperimentu, nevis pilnvērtīgu sporta kalendāru sastādīšanas produktu."
        ),
    ),
)


FIGURE_SPECS: tuple[FigureSpec, ...] = (
    FigureSpec(
        identifier="selector_performance",
        file_name="selector_performance.png",
        section_id="results",
        title="Nejaušo mežu klasifikatora galvenie rādītāji",
        description=(
            "Attēlā vienkopus parādīti četri jauktās datu kopas galvenie novērtējuma rādītāji."
        ),
        meaning=(
            "Tas parāda pieejas realizējamību šajā eksperimentālajā uzstādījumā, nevis universālu algoritmu izvēles efektivitāti."
        ),
    ),
    FigureSpec(
        identifier="selector_vs_baselines",
        file_name="selector_vs_baselines.png",
        section_id="results",
        title="Algoritmu izvēles modeļa salīdzinājums ar SBS un VBS",
        description=(
            "Attēlā salīdzināta algoritmu izvēles modeļa, viena labākā fiksētā risinātāja un virtuāli labākā risinātāja "
            "vidējā mērķfunkcijas vērtība."
        ),
        meaning=(
            "Tas ļauj redzēt, kā izvēles modelis uzvedas pret SBS un VBS atskaites punktiem konkrētajā datu kopā."
        ),
    ),
    FigureSpec(
        identifier="solver_comparison",
        file_name="solver_comparison.png",
        section_id="solver",
        title="Atskaites risinātāju kvalitāte pēc datu tipa",
        description=(
            "Grafikā salīdzināta risinātāju vidējā sasniegtā kvalitāte reālajās un sintētiskajās instancēs."
        ),
        meaning=(
            "Tas jālasa kopā ar risinātāju tvērumu: CP-SAT un simulētā rūdīšana ir atskaites risinātāji, bet Timefold nav konfigurēts."
        ),
    ),
    FigureSpec(
        identifier="solver_runtime",
        file_name="solver_runtime.png",
        section_id="solver",
        title="Atskaites risinātāju izpildes laiks",
        description=(
            "Attēlā redzams vidējais izpildes laiks pa risinātājiem, nošķirot reālās un sintētiskās instances."
        ),
        meaning=(
            "No šī var secināt, ka kvalitāte jāvērtē kopā ar aprēķina laiku."
        ),
    ),
    FigureSpec(
        identifier="feature_importance",
        file_name="feature_importance.png",
        section_id="features",
        title="Desmit nozīmīgākās strukturālās pazīmes nejaušo mežu klasifikatorā",
        description=(
            "Grafikā parādītas desmit strukturālās pazīmes ar lielāko nozīmīgumu nejaušo mežu klasifikatorā."
        ),
        meaning=(
            "Pazīmju nozīmīgums rāda, kuras pazīmes modelis izmanto prognozēšanā šajā datu kopā. "
            "Tas nepierāda cēlonisku saistību starp pazīmi un risinātāja pārākumu. Rezultāti jāinterpretē "
            "kopā ar datu avota efektu un pārējiem eksperimenta ierobežojumiem."
        ),
    ),
    FigureSpec(
        identifier="real_vs_synthetic",
        file_name="real_vs_synthetic.png",
        section_id="datasets",
        title="Reālo un sintētisko datu salīdzinājums",
        description=(
            "Attēlā salīdzināti galvenie modeļa rezultāti abās datu grupās: precizitāte, kvalitāte un regret."
        ),
        meaning=(
            "Tas parāda, ka rezultāti jāinterpretē atsevišķi pa datu avotiem un piesardzīgi pret datu avota efektu."
        ),
    ),
    FigureSpec(
        identifier="solver_win_distribution",
        file_name="solver_win_distribution.png",
        section_id="best_solver",
        title="best_solver klašu sadalījums pa datu avotiem",
        description=(
            "Diagramma rāda gala best_solver klašu sadalījumu reālajās un sintētiskajās instancēs."
        ),
        meaning=(
            "Tas nodala reālo un sintētisko datu klašu sadalījumu un nepasniedz Timefold kā aktīvu salīdzinājuma dalībnieku."
        ),
    ),
    FigureSpec(
        identifier="dataset_distribution",
        file_name="dataset_distribution.png",
        section_id="overview",
        title="Eksperimentā izmantotās datu kopas sastāvs",
        description=(
            "Attēlā parādīts instanču sadalījums pa datu tipiem."
        ),
        meaning=(
            "Tas parāda jauktās datu kopas sastāvu un sintētisko instanču lielo īpatsvaru, kas jāņem vērā rezultātu interpretācijā."
        ),
    ),
    FigureSpec(
        identifier="best_solver_class_distribution",
        file_name="best_solver_class_distribution.png",
        section_id="best_solver",
        title="best_solver klašu sadalījums",
        description=(
            "Attēlā parādīts, cik bieži katrs risinātājs kļūst par best_solver visā jauktajā datu kopā."
        ),
        meaning=(
            "Tas parāda divas aktīvas mērķa klases un palīdz pamanīt, ka klašu sadalījums cieši sakrīt ar datu avotu."
        ),
    ),
    FigureSpec(
        identifier="objective_distribution",
        file_name="objective_distribution.png",
        section_id="datasets",
        title="Mērķfunkcijas vērtību sadalījums",
        description=(
            "Diagrammā salīdzināts labākais sasniegtais mērķfunkcijas līmenis reālajās un sintētiskajās instancēs."
        ),
        meaning=(
            "No šī var secināt, ka abu datu grupu optimizācijas grūtības līmenis atšķiras."
        ),
    ),
    FigureSpec(
        identifier="runtime_distribution",
        file_name="runtime_distribution.png",
        section_id="datasets",
        title="Izpildes laika sadalījums",
        description=(
            "Kastes diagrammā parādīts algoritmu izpildes laiku sadalījums, izmantojot visus saglabātos benchmark rezultātus."
        ),
        meaning=(
            "Tas ļauj novērtēt ne tikai vidējo laiku, bet arī rezultātu izkliedi un stabilitāti."
        ),
    ),
    FigureSpec(
        identifier="accuracy_by_dataset_type",
        file_name="accuracy_by_dataset_type.png",
        section_id="results",
        title="Precizitāte pa datu tipiem",
        description=(
            "Diagramma salīdzina precizitāti jauktajā kopā, reālajās instancēs un sintētiskajās instancēs."
        ),
        meaning=(
            "Tas parāda, ka kopējais rezultāts jāinterpretē kopā ar abu datu apakškopu uzvedību."
        ),
    ),
    FigureSpec(
        identifier="regret_distribution",
        file_name="regret_distribution.png",
        section_id="results",
        title="Regret sadalījums validācijas sadalījumos",
        description=(
            "Attēlā parādīts regret sadalījums pa validācijas sadalījumiem un datu tipiem."
        ),
        meaning=(
            "Tas parāda, cik stabils modelis ir dažādos validācijas griezumos."
        ),
    ),
    FigureSpec(
        identifier="confusion_matrix",
        file_name="confusion_matrix.png",
        section_id="results",
        title="Klasifikācijas kļūdu matrica",
        description=(
            "Matrica apkopo, cik bieži modelis katru patieso labāko algoritmu prognozēja kā konkrētu portfeļa algoritmu."
        ),
        meaning=(
            "Tas palīdz redzēt, ka kļūdas koncentrējas šaurā robežgadījumu daļā, nevis vienmērīgi visās klasēs."
        ),
    ),
    FigureSpec(
        identifier="feature_correlation_matrix",
        file_name="feature_correlation_matrix.png",
        section_id="features",
        title="Svarīgāko pazīmju korelācijas",
        description=(
            "Korelāciju matrica parāda savstarpējās saites starp modeļa svarīgākajām strukturālajām pazīmēm."
        ),
        meaning=(
            "No šī var secināt, kur pazīmes nes līdzīgu informāciju un kur tās viena otru papildina."
        ),
    ),
    FigureSpec(
        identifier="constraint_distribution",
        file_name="constraint_distribution.png",
        section_id="overview",
        title="Ierobežojumu sadalījums instancēs",
        description=(
            "Attēlā salīdzināts kopējais, stingro un mīksto ierobežojumu sadalījums reālajās un sintētiskajās instancēs."
        ),
        meaning=(
            "Tas parāda, cik atšķirīga ir problēmu struktūra un kāpēc viena algoritma dominance nevar tikt pieņemta automātiski."
        ),
    ),
    FigureSpec(
        identifier="teams_vs_slots_plot",
        file_name="teams_vs_slots_plot.png",
        section_id="overview",
        title="Komandu skaits pret laika vietu skaitu",
        description=(
            "Izkliedes diagramma rāda, kā instanču izmērs sadalās pa datu tipiem pēc komandu un laika vietu skaita."
        ),
        meaning=(
            "Tas parāda, cik plašu strukturālo telpu aptver izmantotā datu kopa."
        ),
    ),
    FigureSpec(
        identifier="constraints_vs_objective",
        file_name="constraints_vs_objective.png",
        section_id="features",
        title="Ierobežojumu skaits pret sasniegto kvalitāti",
        description=(
            "Diagramma salīdzina instanču ierobežojumu skaitu ar labāko sasniegto mērķfunkcijas vērtību."
        ),
        meaning=(
            "Tas parāda, ka strukturālā sarežģītība ir saistīta ar sasniedzamās kvalitātes līmeni."
        ),
    ),
)
