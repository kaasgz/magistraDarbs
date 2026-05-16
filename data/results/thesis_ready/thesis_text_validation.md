# Thesis Text Validation

This report audits the practical section (4. nodaļa) of the thesis against repository artifacts.

## Summary

- Checked claims: 315
- `OK`: 15
- `MISMATCH`: 0
- `NOT_FOUND`: 300

## Correctly aligned claims

- [DATA-40] 4. Datu avoti un datu sagatavošana: Ģenerēšanas procesā tika variēts turnīra formāts, komandu skaits, laika posmu skaits, spēļu skaits, ierobežojumu skaits, ierobežojumu blīvums, ierobežojumu grupu daudzveidība un soda svaru diapazons.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [data/processed/selection_dataset_full.csv](https://github.com/kaasgz/magistraDarbs/blob/main/data/processed/selection_dataset_full.csv)
  Actual: `num_constraints, num_slots, num_teams`
- [DATA-48] 4. Datu avoti un datu sagatavošana: Modeļa ievaddatus veido strukturālās pazīmes, kas aprēķinātas no instances apraksta pirms risināšanas, piemēram, komandu skaits, laika posmu skaits, ierobežojumu skaits, stingro un mīksto ierobežojumu sadalījums, ierobežojumu blīvums un ierobežojumu daudzveidība.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [data/processed/selection_dataset_full.csv](https://github.com/kaasgz/magistraDarbs/blob/main/data/processed/selection_dataset_full.csv)
  Actual: `num_constraints, num_slots, num_teams`
- [DATA-94] 4. Algoritmu portfelis un rezultātu interpretācija: Reģistrētajā portfelī iekļauti četri risinātāji: nejaušā diagnostiskā atskaites pieeja, CP-SAT modelis, simulētās rūdīšanas heiristika un Timefold integrācija.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [src/experiments/full_benchmark.py](https://github.com/kaasgz/magistraDarbs/blob/main/src/experiments/full_benchmark.py)
  Actual: `random_baseline, cpsat_solver, simulated_annealing_solver, timefold`
- [DATA-117] 4. Algoritmu portfelis un rezultātu interpretācija: Mērķfunkcija minimizē izmantoto laika posmu skaitu.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [src/solvers/cpsat_solver.py](https://github.com/kaasgz/magistraDarbs/blob/main/src/solvers/cpsat_solver.py)
  Actual: `one required match per pair/leg; at most one match per team per slot; minimize used slots`
- [DATA-122] 4. Algoritmu portfelis un rezultātu interpretācija: Meklēšanā izmantoti divi apkaimes operatori: spēles pārvietošana uz citu laika posmu (reassign) un divu spēļu izvietojuma apmaiņa (swap).
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [src/solvers/simulated_annealing_solver.py](https://github.com/kaasgz/magistraDarbs/blob/main/src/solvers/simulated_annealing_solver.py)
  Actual: `single round-robin simulated annealing baseline with reassign and swap neighborhoods`
- [DATA-143] 4. Jauktās algoritmu izvēles datu kopas izveide: Tajā katra rinda atbilst vienai sporta turnīru kalendāru sastādīšanas instancei, savukārt mērķa mainīgais best_solver norāda risinātāju, kas konkrētajā atskaites portfelī un izvēlētajā vērtēšanas tvērumā uzskatāms par piemērotāko.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [data/processed/selection_dataset_full.csv](https://github.com/kaasgz/magistraDarbs/blob/main/data/processed/selection_dataset_full.csv), [src/selection/modeling.py](https://github.com/kaasgz/magistraDarbs/blob/main/src/selection/modeling.py)
  Actual: `TARGET_COLUMN=best_solver`
- [DATA-150] 4. Jauktās algoritmu izvēles datu kopas izveide: Mērķa mainīgais best_solver netika noteikts, vienkārši izvēloties mazāko mērķfunkcijas vērtību no visām rezultātu rindām.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [data/processed/selection_dataset_full.csv](https://github.com/kaasgz/magistraDarbs/blob/main/data/processed/selection_dataset_full.csv), [src/selection/modeling.py](https://github.com/kaasgz/magistraDarbs/blob/main/src/selection/modeling.py)
  Actual: `TARGET_COLUMN=best_solver`
- [DATA-154] 4. Jauktās algoritmu izvēles datu kopas izveide: Tabulā “Mērķa mainīgā best_solver izveides nosacījumi” redzams, ka mērķa mainīgais veidots kontrolēti.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [data/processed/selection_dataset_full.csv](https://github.com/kaasgz/magistraDarbs/blob/main/data/processed/selection_dataset_full.csv), [src/selection/modeling.py](https://github.com/kaasgz/magistraDarbs/blob/main/src/selection/modeling.py)
  Actual: `TARGET_COLUMN=best_solver`
- [DATA-170] 4. Jauktās algoritmu izvēles datu kopas izveide: Praktiski tas nozīmē, ka no apmācības pazīmēm tika izslēgtas kolonnas ar prefiksiem objective_, benchmark_, label_, target_ un dataset_, kā arī pats mērķa mainīgais best_solver.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [data/processed/selection_dataset_full.csv](https://github.com/kaasgz/magistraDarbs/blob/main/data/processed/selection_dataset_full.csv), [src/selection/modeling.py](https://github.com/kaasgz/magistraDarbs/blob/main/src/selection/modeling.py)
  Actual: `TARGET_COLUMN=best_solver`
- [DATA-184] 4. Jauktās algoritmu izvēles datu kopas izveide: Kopumā tika izveidotas 234 algoritmu izvēles rindas: 54 reālajām un 180 sintētiskajām instancēm.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [data/processed/selection_dataset_full_run_summary.json](https://github.com/kaasgz/magistraDarbs/blob/main/data/processed/selection_dataset_full_run_summary.json)
  Actual: `234; 54; 180`
- [DATA-190] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Algoritmu izvēles modelis šajā darbā veidots kā nejaušo mežu klasifikators.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [src/selection/modeling.py](https://github.com/kaasgz/magistraDarbs/blob/main/src/selection/modeling.py)
  Actual: `RandomForestClassifier`
- [DATA-198] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Hiperparametru optimizācija netika veikta, jo galvenais mērķis bija pārbaudīt algoritmu izvēles pieejas realizējamību ar kontrolētu un atkārtojamu modeli..
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [src/selection/modeling.py](https://github.com/kaasgz/magistraDarbs/blob/main/src/selection/modeling.py), [configs/real_pipeline_current.yaml](https://github.com/kaasgz/magistraDarbs/blob/main/configs/real_pipeline_current.yaml)
  Actual: `fixed random_forest baseline configuration`
- [DATA-203] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Mērķa mainīgais bija best_solver, kas definēts iepriekšējā apakšnodaļā.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [data/processed/selection_dataset_full.csv](https://github.com/kaasgz/magistraDarbs/blob/main/data/processed/selection_dataset_full.csv), [src/selection/modeling.py](https://github.com/kaasgz/magistraDarbs/blob/main/src/selection/modeling.py)
  Actual: `TARGET_COLUMN=best_solver`
- [DATA-223] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tabulā “Algoritmu izvēles modeļa veiktspējas kopsavilkums” redzams, ka modelis sasniedza augstu klasifikācijas precizitāti un sabalansēto precizitāti.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [data/results/full_selection/selector_evaluation_run_summary.json](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/full_selection/selector_evaluation_run_summary.json)
  Actual: `accuracy=0.9957; balanced_accuracy=0.9907`
- [DATA-238] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Kļūdu stabiņi attēlo rezultātu mainīgumu deviņos pārbaudes sadalījumos.
  Source: Precīzais avots GitHub krātuvē (skatīt šeit): [data/results/full_selection/selector_evaluation_run_summary.json](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/full_selection/selector_evaluation_run_summary.json)
  Actual: `9`

## Inconsistencies

- No direct numeric mismatches were detected.

## Manual review needed

- [DATA-1] ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ: Šajā nodaļā aprakstīta maģistra darba eksperimentālā daļa, kurā pārbaudīts, vai sporta turnīru kalendāru sastādīšanas instanču strukturālās pazīmes var izmantot piemērotākā risinātāja prognozēšanai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-2] ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ: Šim nolūkam, izmantojot Python, izveidots reproducējams eksperimentālais process, kas ietver instanču nolasīšanu, strukturālo pazīmju iegūšanu, risinātāju portfeļa izpildi, algoritmu izvēles datu kopas izveidi un mašīnmācīšanās modeļa novērtēšanu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-3] ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ: Eksperimentālajā izpētē izmantota datu kopa ar 234 instancēm, kas apvieno reālas un sintētiski ģenerētas sporta turnīru kalendāru sastādīšanas instances.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-4] ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ: No tām 54 ir reālas instances, kas iegūtas no RobinX un ITC2021 problēmu aprakstiem, bet 180 ir sintētiski ģenerētas instances.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-5] ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ: Šāds datu kopas sastāvs ļauj vienā eksperimentālajā procesā analizēt gan reālu instanču struktūru, gan kontrolēti ģenerētu instanču strukturālās īpašības.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-6] ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ: Eksperimentālajā daļā īpaši nodalīta informācija, kas ir pieejama pirms instances risināšanas, no informācijas, kas rodas tikai pēc risinātāju izpildes.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-7] ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ: Algoritmu izvēles modeļa ievaddatos tiek izmantotas tikai strukturālās pazīmes, savukārt risinātāju rezultāti, mērķa mainīgie, datu izcelsmes metadati un citi ar mērķa mainīgo saistīti lauki modeļa apmācībā netiek izmantoti.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-8] ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ: Šāds nodalījums nepieciešams, lai mazinātu informācijas noplūdes risku un saglabātu algoritmu izvēles uzdevuma korektu interpretāciju.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-9] ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ: Šajā darbā izmantotais risinātāju portfelis interpretējams kā reproducējams atskaites risinātāju portfelis, nevis kā pilnvērtīgs RobinX vai ITC2021 sacensību līmeņa risinātāju kopums.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-10] ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ: Portfelī iekļautie risinātāji atšķiras pēc lomas un modelēšanas tvēruma, tādēļ rezultāti jāinterpretē kopā ar risinātāju atbalsta statusiem un rezultātu vērtēšanas nosacījumiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-11] ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ: Šāda pieeja ļauj novērtēt izstrādāto algoritmu izvēles ietvaru, vienlaikus skaidri norādot tā praktiskos ierobežojumus.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-12] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Eksperimentālās daļas mērķis ir izveidot reproducējamu eksperimentālo procesu, kas ļauj sporta turnīru kalendāru sastādīšanas instances raksturot ar strukturālām pazīmēm, izpildīt definētu risinātāju portfeli un uz šā pamata novērtēt algoritmu izvēles modeli.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-13] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Process veidots tā, lai katrā posmā būtu skaidri nodalīti ievaddati, veiktā apstrāde un iegūtais rezultāts.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-14] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Eksperimentālā sistēma sastāv no vairākiem secīgiem posmiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-15] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Vispirms tiek identificētas un nolasītas pieejamās RobinX formāta un ITC2021 etalona instances.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-16] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Pēc tam no instanču aprakstiem tiek iegūtas strukturālās pazīmes, kas raksturo instances izmēru, ierobežojumu sastāvu, blīvumu un daudzveidību.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-17] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Nākamajā posmā šīm instancēm tiek izpildīts risinātāju portfelis, un iegūtie rezultāti tiek saglabāti vienotā formātā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-18] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Pēc tam strukturālās pazīmes tiek apvienotas ar risinātāju veiktspējas datiem, lai izveidotu algoritmu izvēles datu kopu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-19] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Modeļa novērtēšana tiek veikta, izmantojot atkārtotu krustotās pārbaudes procedūru, lai rezultāti nebūtu atkarīgi tikai no viena datu sadalījuma.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-20] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Novērtējumā tiek ņemta vērā ne tikai klasifikācijas precizitāte, bet arī modeļa izvēles rezultātu salīdzinājums ar labāko fiksēto risinātāju un virtuāli labāko risinātāju.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-21] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Tas ļauj vērtēt gan prognozēšanas kvalitāti, gan praktisko ieguvumu no algoritmu izvēles pieejas.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-22] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Eksperimentālās sistēmas galvenie posmi apkopoti tabulā “Eksperimentālās sistēmas galvenie posmi”.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-23] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Tabulā “Eksperimentālās sistēmas galvenie posmi” apkopotais posmu sadalījums parāda, ka algoritmu izvēles eksperiments nav tikai modeļa apmācība.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-24] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Tā kvalitāte ir atkarīga arī no instanču sagatavošanas, pazīmju iegūšanas, risinātāju rezultātu korektas saglabāšanas un mērķa mainīgā definēšanas.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-25] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Ja kādā no šiem posmiem rodas nekonsekvence, tā var ietekmēt gan algoritmu izvēles datu kopu, gan modeļa novērtējumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-26] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Tāpēc eksperimentālajā sistēmā atsevišķi nodalīta informācija, kas pieejama pirms instances risināšanas, un informācija, kas rodas tikai pēc risinātāju izpildes.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-27] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Strukturālās pazīmes veido modeļa ievaddatus, savukārt risinātāju rezultāti un ar tiem saistītie statusi tiek izmantoti mērķa mainīgā definēšanai un rezultātu interpretācijai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-28] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Šāds nodalījums ir nepieciešams, lai mazinātu informācijas noplūdes risku un saglabātu algoritmu izvēles uzdevuma korektu interpretāciju.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-29] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Šajā apakšnodaļā eksperimentālā sistēma raksturota vispārīgā līmenī.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-30] 4. Eksperimentālās daļas mērķis un vispārējā uzbūve: Turpmākajās apakšnodaļās atsevišķi aplūkota instanču kopa, pazīmju iegūšana, risinātāju portfelis, algoritmu izvēles datu kopas izveide, modeļa apmācība un iegūto rezultātu interpretācija.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-31] 4. Datu avoti un datu sagatavošana: Eksperimentālajā daļā izmantota datu kopa, kurā iekļautas 234 sporta turnīru kalendāru sastādīšanas instances.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-32] 4. Datu avoti un datu sagatavošana: Tā apvieno 54 reālas instances, kas iegūtas no RobinX formāta un ITC2021 etalona datiem, un 180 sintētiski ģenerētas instances.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-33] 4. Datu avoti un datu sagatavošana: Reālās instances nodrošina saikni ar standartizētiem sporta turnīru kalendāru sastādīšanas uzdevumiem, savukārt sintētiskās instances izmantotas, lai kontrolēti paplašinātu instanču kopu pēc komandu skaita, laika posmu skaita, turnīra formāta un ierobežojumu struktūras.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-34] 4. Datu avoti un datu sagatavošana: Attēlā “ Eksperimentā izmantotās datu kopas sastāvs” , parādīts eksperimentā izmantotās datu kopas sastāvs.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-35] 4. Datu avoti un datu sagatavošana: Sintētiskās instances veido lielāko datu kopas daļu - 180 no 234 instancēm jeb 76,9 %.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-36] 4. Datu avoti un datu sagatavošana: Tāpēc turpmākie rezultāti interpretējami kā jauktas datu kopas eksperiments, nevis kā secinājumi tikai par reālajām RobinX un ITC2021 instancēm.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-37] 4. Datu avoti un datu sagatavošana: Sintētiskās instances tika ģenerētas reproducējamā Python procedūrā, izmantojot fiksētas nejaušības ģeneratora sākumvērtības 42, 43 un 44.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-38] 4. Datu avoti un datu sagatavošana: Datu kopa tika sadalīta trīs ģenerēšanas profilos: 60 vienkāršās, 60 vidējas sarežģītības un 60 sarežģītās instancēs.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-39] 4. Datu avoti un datu sagatavošana: Šis sadalījums ļauj kontrolēti variēt instanču struktūru, vienlaikus saglabājot iespēju atkārtot ģenerēšanas procesu ar tiem pašiem sākuma nosacījumiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-41] 4. Datu avoti un datu sagatavošana: Kopumā izveidotas 93 vienkārtēja pilna savstarpējo spēļu turnīra instances un 87 divkārtēja pilna savstarpējo spēļu turnīra instances.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-42] 4. Datu avoti un datu sagatavošana: Galvenie sintētisko instanču ģenerēšanā izmantotie parametri apkopoti tabulā “Sintētisko instanču ģenerēšanā variētie strukturālie parametri”.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-43] 4. Datu avoti un datu sagatavošana: “Sintētisko instanču ģenerēšanā variētie strukturālie parametri” apkopotie parametri parāda, ka sintētisko instanču ģenerēšanā tika variēts ne tikai instances izmērs, bet arī tās strukturālais raksturojums.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-44] 4. Datu avoti un datu sagatavošana: Komandu, laika posmu un spēļu skaits nosaka instances mērogu, savukārt ierobežojumu skaits, blīvums, grupu daudzveidība un soda svaru diapazons raksturo ierobežojumu struktūru.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-45] 4. Datu avoti un datu sagatavošana: Šāda parametru izvēle ir būtiska algoritmu izvēles kontekstā, jo tā ļauj izveidot instances, kas atšķiras ne tikai pēc apjoma, bet arī pēc risinājumu telpas ierobežotības un kvalitātes kritēriju nozīmīguma.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-46] 4. Datu avoti un datu sagatavošana: Svarīgi atšķirt ģenerēšanas parametrus, metadatus un modeļa ievades pazīmes.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-47] 4. Datu avoti un datu sagatavošana: Ģenerēšanas sākumvērtība, ģenerēšanas profils un citi ar datu kopas izveidi saistītie lauki tika saglabāti izsekojamībai, taču tie netiek izmantoti kā algoritmu izvēles modeļa ievaddati.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-49] 4. Datu avoti un datu sagatavošana: Sintētiskajās instancēs tika izmantotas vairākas ierobežojumu grupas: kapacitāte (Capacity), pieejamība (Availability), norises vieta (Venue), atdalījums (Separation), pārtraukumi (Break), mājas un izbraukuma spēles (HomeAway), taisnīgums (Fairness) un ceļošana (Travel).
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-50] 4. Datu avoti un datu sagatavošana: Šīs grupas šajā darbā nav interpretējamas kā pilnīgs sporta turnīru kalendāru sastādīšanas ierobežojumu semantiskais modelis.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-51] 4. Datu avoti un datu sagatavošana: Tās galvenokārt izmantotas kā strukturāli apzīmējumi, kas ļauj kontrolēti mainīt ierobežojumu skaitu, sadalījumu un daudzveidību.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-52] 4. Datu avoti un datu sagatavošana: Tāpēc sintētisko instanču rezultāti raksturo algoritmu izvēles pieejas darbību kontrolētā eksperimentālā vidē, nevis pierāda tās tiešu pārnesamību uz visiem reāliem turnīru kalendāru sastādīšanas gadījumiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-53] 4. Datu avoti un datu sagatavošana: Katra sintētiskā instance tika saglabāta RobinX tipa XML pierakstā un papildināta ar metadatiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-54] 4. Datu avoti un datu sagatavošana: Metadatos iekļauta informācija par instances izcelsmi, ģenerēšanas parametriem, ierobežojumu struktūru un soda svaru diapazoniem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-55] 4. Datu avoti un datu sagatavošana: Šie dati ļauj pārbaudīt, kā katra instance izveidota un kā tā iekļauta kopējā eksperimentālajā procesā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-56] 4. Datu avoti un datu sagatavošana: Pēc ģenerēšanas sintētiskās instances tika apstrādātas kopā ar reālajām instancēm.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-57] 4. Datu avoti un datu sagatavošana: Abām datu grupām tika piemērota viena un tā pati strukturālo pazīmju iegūšanas, risinātāju izpildes un rezultātu saglabāšanas procedūra.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-58] 4. Datu avoti un datu sagatavošana: Vienots apstrādes process nepieciešams, lai reālās un sintētiskās instances būtu salīdzināmas pēc vienotas pazīmju shēmas un vienotiem rezultātu marķēšanas principiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-59] 4. Datu avoti un datu sagatavošana: Datu sagatavošanas posmā iegūtā datu kopa nodrošina gan saikni ar reāliem sporta turnīru kalendāru sastādīšanas etaloniem, gan kontrolētu sintētisko instanču kopu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-60] 4. Datu avoti un datu sagatavošana: Vienlaikus sintētisko instanču lielais īpatsvars nozīmē, ka modeļa rezultāti jāinterpretē piesardzīgi, īpaši vērtējot to pārnesamību uz reāliem sporta turnīru kalendāru sastādīšanas uzdevumiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-61] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Pēc datu kopas sagatavošanas eksperimentālajā procesā tika veikta instanču nolasīšana un strukturālo pazīmju iegūšana.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-62] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Šajā posmā RobinX formāta un ITC2021 etalona instanču XML apraksti tika pārveidoti tabulārā formā, kur katru instanci raksturo viena rinda ar identifikatoru instance_name.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-63] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Šāda pārveide bija nepieciešama, jo algoritmu izvēles modelis nevar tieši izmantot XML failu hierarhisko struktūru.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-64] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Lai instances varētu izmantot modeļa apmācībā, tās bija jāapraksta ar vienotām skaitliskām vai kategoriskām pazīmēm.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-65] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Instanču nolasīšanas mehānisms tika veidots tā, lai tas spētu apstrādāt arī praktiskos datos sastopamas XML īpatnības, piemēram, XML nosaukumtelpas, trūkstošas neobligātās sadaļas un atsevišķas labojamas sintakses nepilnības.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-66] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Apstrādes laikā tika reģistrētas arī konstatētās neatbilstības, piemēram, dublēti ieraksti, trūkstoši lauki vai nesakritības starp deklarēto un faktiski iegūto elementu skaitu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-67] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Šī informācija izmantota pārbaudei un izsekojamībai, bet nav iekļauta modeļa ievades pazīmēs.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-68] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Strukturālo pazīmju iegūšanā tika izmantota tikai informācija, kas pieejama pirms instances risināšanas.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-69] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Tādēļ pazīmes tika aprēķinātas no instances apraksta, nevis no risinātāju izpildes rezultātiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-70] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Iegūtās pazīmes raksturo instances uzbūvi - komandu un laika posmu skaitu, ierobežojumu sastāvu, ierobežojumu blīvumu un ierobežojumu daudzveidību.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-71] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Tādējādi pazīmju tabula veido instances strukturālu aprakstu, ko tālāk var izmantot algoritmu izvēles modelī.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-72] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Šajā darbā strukturālās pazīmes tiek interpretētas kā konkrētas instances raksturlielumi.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-73] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Sporta turnīru kalendāru sastādīšanas problēmu klase nosaka kopīgo ietvaru - komandas, laika posmus, spēļu pārus un ierobežojumus, taču algoritmu izvēles modelim būtiskas ir tieši atšķirības starp atsevišķām instancēm.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-74] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Piemēram, ierobežojumu skaits ir konkrētas instances ievaddatu īpašība.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-75] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Risināšanas laikā tas nemainās, taču starp instancēm šis rādītājs var būt atšķirīgs, tāpēc to var izmantot kā instances līmeņa pazīmi.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-76] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Strukturālās pazīmes tika sadalītas četrās grupās.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-77] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Izmēra pazīmes raksturo instances mērogu, piemēram, komandu un laika posmu skaitu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-78] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Ierobežojumu sastāva pazīmes apraksta kopējo ierobežojumu skaitu un stingro un mīksto ierobežojumu sadalījumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-79] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Ierobežojumu blīvuma pazīmes raksturo ierobežojumu daudzumu attiecībā pret instances izmēru, piemēram, pret komandu vai laika posmu skaitu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-80] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Savukārt ierobežojumu daudzveidības pazīmes raksturo atšķirīgo ierobežojumu tipu, kategoriju un marķieru skaitu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-81] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Tabulā “Strukturālo pazīmju grupējums un piemēri” redzams, ka izmantotā pazīmju kopa neaprobežojas tikai ar instances izmēru.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-82] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Komandu un laika posmu skaits raksturo problēmas apjomu, bet ierobežojumu sastāva, blīvuma un daudzveidības pazīmes ļauj aprakstīt ierobežojumu struktūru.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-83] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Tas ir būtiski algoritmu izvēles kontekstā, jo divas vienāda izmēra instances var būt atšķirīgas pēc ierobežojumu skaita, stingro un mīksto ierobežojumu sadalījuma un prasību daudzveidības.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-84] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Reālo un sintētisko instanču izcelsme tika saglabāta metadatos, lai rezultātus vēlāk būtu iespējams analizēt pa instanču grupām.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-85] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Tomēr datu izcelsme netika izmantota kā modeļa ievades pazīme.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-86] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Šāds lēmums pieņemts, lai modelis piemērotāko risinātāju noteiktu pēc instances strukturālajām īpašībām, nevis pēc tā, vai instance ir reāla vai sintētiski ģenerēta.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-87] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Šajā posmā iegūtā pazīmju tabula nosaka, kā sporta turnīru kalendāru sastādīšanas instance tiek attēlota algoritmu izvēles modelī.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-88] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Tāpēc pazīmju iegūšana nav tikai tehniska XML failu pārveidošana tabulā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-89] 4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana: Tā ir metodoloģiska izvēle par to, kuri instances raksturlielumi tiek uzskatīti par būtiskiem piemērotākā risinātāja prognozēšanai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-90] 4. Algoritmu portfelis un rezultātu interpretācija: Eksperimentālajā daļā izmantots atskaites risinātāju portfelis, kura uzdevums ir nodrošināt reproducējamu vidi algoritmu izvēles pieejas pārbaudei.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-91] 4. Algoritmu portfelis un rezultātu interpretācija: Šis portfelis nav uzskatāms par pilnvērtīgu RobinX vai ITC2021 sacensību līmeņa risinātāju kopumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-92] 4. Algoritmu portfelis un rezultātu interpretācija: Tajā iekļautie risinātāji atšķiras pēc lomas, modelēšanas tvēruma un rezultātu interpretācijas nosacījumiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-93] 4. Algoritmu portfelis un rezultātu interpretācija: Darbā jānošķir reģistrētais risinātāju portfelis un rezultāti, kurus var izmantot salīdzināšanai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-95] 4. Algoritmu portfelis un rezultātu interpretācija: Tomēr konkrētajā eksperimentālajā konfigurācijā ne visi šie risinātāji sniedz pilnvērtīgi salīdzināmus veiktspējas rezultātus.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-96] 4. Algoritmu portfelis un rezultātu interpretācija: Timefold šajā darbā iekļauts kā ārējas integrācijas pārbaudes punkts.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-97] 4. Algoritmu portfelis un rezultātu interpretācija: Tā kā ārējais izpildāmais fails nebija konfigurēts, Timefold rezultātu rindas saglabātas auditēšanai, bet netiek interpretētas kā šī risinātāja veiktspējas novērtējums.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-98] 4. Algoritmu portfelis un rezultātu interpretācija: Eksperimenta izpildes pamatvienība bija instances, risinātāja un nejaušības sākumvērtības kombinācija.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-99] 4. Algoritmu portfelis un rezultātu interpretācija: Reālajām instancēm katrs no četriem reģistrētajiem risinātājiem tika izpildīts vienu reizi, kopā veidojot 216 rezultātu rindas.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-100] 4. Algoritmu portfelis un rezultātu interpretācija: Sintētiskajām instancēm izpilde tika veikta ar trim nejaušības sākumvērtībām, kopā veidojot 2160 rezultātu rindas.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-101] 4. Algoritmu portfelis un rezultātu interpretācija: Tādējādi pilnajā rezultātu tabulā tika iegūtas 2376 rindas, kuru tālāka izmantošana bija atkarīga no risinātāja atbalsta un vērtēšanas statusa.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-102] 4. Algoritmu portfelis un rezultātu interpretācija: Risinātāju pārklājums un galvenie interpretācijas nosacījumi apkopoti “Risinātāju izpildes pārklājums un interpretācija” tabulā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-103] 4. Algoritmu portfelis un rezultātu interpretācija: “Risinātāju izpildes pārklājums un interpretācija” parāda, ka portfelī reģistrētie risinātāji atšķiras gan pēc pārklājuma, gan pēc modelēšanas tvēruma.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-104] 4. Algoritmu portfelis un rezultātu interpretācija: CP-SAT modelis nodrošina pamatstruktūras optimizāciju gan vienkārtēja, gan divkārtēja pilna savstarpējo spēļu turnīra gadījumā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-105] 4. Algoritmu portfelis un rezultātu interpretācija: Simulētā rūdīšana darbojas tikai vienkārtēja turnīra vienkāršotā attēlojumā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-106] 4. Algoritmu portfelis un rezultātu interpretācija: Nejaušā diagnostiskā atskaites pieeja neveido sporta kalendāru, bet kalpo eksperimentālās datu plūsmas pārbaudei.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-107] 4. Algoritmu portfelis un rezultātu interpretācija: Timefold integrācija šajā konfigurācijā nav izmantojama veiktspējas salīdzināšanai, jo ārējais izpildāmais fails nav iestatīts.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-108] 4. Algoritmu portfelis un rezultātu interpretācija: Šis nošķīrums ir būtisks turpmākajā rezultātu interpretācijā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-109] 4. Algoritmu portfelis un rezultātu interpretācija: Šajā darbā netiek salīdzināti četri pilnvērtīgi ITC2021 risinātāji.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-110] 4. Algoritmu portfelis un rezultātu interpretācija: Salīdzinājums tiek veikts atskaites portfelī, kur katram risinātājam ir noteikta loma un ierobežots modelēšanas tvērums.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-111] 4. Algoritmu portfelis un rezultātu interpretācija: Nejaušā diagnostiskā atskaites pieeja šajā darbā nav nejauša sporta kalendāra konstruktors.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-112] 4. Algoritmu portfelis un rezultātu interpretācija: Tā aprēķina reproducējamu diagnostisku mērķvērtību, izmantojot instances izmēra rādītājus un fiksētu nejaušības komponenti.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-113] 4. Algoritmu portfelis un rezultātu interpretācija: Šī pieeja palīdz pārbaudīt datu plūsmu un salīdzināšanas mehānismu, bet tās rezultāti nav interpretējami kā praktisks kalendāru sastādīšanas risinājums.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-114] 4. Algoritmu portfelis un rezultātu interpretācija: CP-SAT modelis izmantots kā strukturāla optimizācijas atskaites pieeja.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-115] 4. Algoritmu portfelis un rezultātu interpretācija: Tajā spēļu izvietošana formulēta ar bināriem piešķiršanas mainīgajiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-116] 4. Algoritmu portfelis un rezultātu interpretācija: Modelis nosaka, ka katra spēle jāpiešķir tieši vienam laika posmam, kā arī ierobežo komandu dalību tā, lai vienā laika posmā komandai nebūtu vairāk par vienu spēli.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-118] 4. Algoritmu portfelis un rezultātu interpretācija: Šāds modelis nodrošina turnīra pamatstruktūras korektumu, tomēr neietver pilnu RobinX vai ITC2021 papildu ierobežojumu semantiku.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-119] 4. Algoritmu portfelis un rezultātu interpretācija: Tāpēc instancēs ar papildu ierobežojumiem CP-SAT rezultāti interpretējami kā daļēji modelēti.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-120] 4. Algoritmu portfelis un rezultātu interpretācija: Simulētās rūdīšanas risinātājs veidots kā vienkāršota heiristiska atskaites pieeja.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-121] 4. Algoritmu portfelis un rezultātu interpretācija: Tas darbojas vienkārtēja pilna savstarpējo spēļu turnīra attēlojumā, kur katrs komandu pāris tiek ieplānots vienu reizi.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-123] 4. Algoritmu portfelis un rezultātu interpretācija: Risinājuma novērtējumā primāri tiek sodīti komandu konflikti, bet sekundāri tiek samazināts izmantoto laika posmu skaits.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-124] 4. Algoritmu portfelis un rezultātu interpretācija: Šī pieeja nav pilns RobinX vai ITC2021 kvalitātes mērs un neatbalsta divkārtēja pilna savstarpējo spēļu turnīra gadījumus.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-125] 4. Algoritmu portfelis un rezultātu interpretācija: Timefold risinātājs šajā darbā izmantots kā ārējas sistēmas integrācijas punkts.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-126] 4. Algoritmu portfelis un rezultātu interpretācija: Python pusē tiek sagatavots turnīra struktūras attēlojums un datu apraksts, ko iespējams nodot ārējai sistēmai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-127] 4. Algoritmu portfelis un rezultātu interpretācija: Tomēr šajā konfigurācijā Timefold ārējais izpildāmais fails nebija iestatīts, tāpēc rezultātu rindām piešķirts statuss not_configured.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-128] 4. Algoritmu portfelis un rezultātu interpretācija: Šis statuss nozīmē, ka attiecīgais rezultāts nav interpretējams kā Timefold algoritma veiktspējas mērījums.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-129] 4. Algoritmu portfelis un rezultātu interpretācija: Lai nodrošinātu reproducējamību, risinātāji tika darbināti ar fiksētiem galvenajiem parametriem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-130] 4. Algoritmu portfelis un rezultātu interpretācija: Tie apkopoti tabulā “Risinātāju galvenā konfigurācija eksperimentā” apkopots galveno modelēto elementu pārklājums.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-131] 4. Algoritmu portfelis un rezultātu interpretācija: Šī konfigurācija apzināti dod priekšroku reproducējamībai, nevis katra risinātāja maksimālai noskaņošanai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-132] 4. Algoritmu portfelis un rezultātu interpretācija: Līdz ar to eksperiments nepierāda kāda konkrēta algoritma absolūtu pārākumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-133] 4. Algoritmu portfelis un rezultātu interpretācija: Tas pārbauda, vai strukturālās pazīmes palīdz atšķirt risinātāju piemērotību konkrētā, iepriekš definētā atskaites portfelī.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-134] 4. Algoritmu portfelis un rezultātu interpretācija: Rezultātu interpretācijai katram risinātāja iznākumam tika saglabāta ne tikai mērķfunkcijas vērtība un izpildes laiks, bet arī statusa un interpretācijas lauki.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-135] 4. Algoritmu portfelis un rezultātu interpretācija: Šo statusu nozīme apkopota tabulā “Risinātāju rezultātu statusu interpretācija”.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-136] 4. Algoritmu portfelis un rezultātu interpretācija: Statusu saglabāšana ir nepieciešama, jo viena un tā pati skaitliskā mērķfunkcijas vērtība var būt atšķirīgi interpretējama atkarībā no risinātāja modelēšanas tvēruma.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-137] 4. Algoritmu portfelis un rezultātu interpretācija: Piemēram, vienkāršotas atskaites pieejas rezultāts nav salīdzināms ar pilnu RobinX vai ITC2021 ierobežojumu semantiku tādā pašā nozīmē kā pilnībā atbalstīts rezultāts.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-138] 4. Algoritmu portfelis un rezultātu interpretācija: Tāpēc risinātāju rezultāti šajā darbā tiek interpretēti kopā ar atbalsta statusu, vērtēšanas statusu un modelēšanas tvērumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-139] 4. Algoritmu portfelis un rezultātu interpretācija: Šīs apakšnodaļas galvenais secinājums ir, ka izmantotais risinātāju portfelis veido kontrolētu atskaites vidi, nevis pilnvērtīgu RobinX vai ITC2021 sacensību līmeņa risinātāju salīdzinājumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-140] 4. Algoritmu portfelis un rezultātu interpretācija: Portfelī iekļautajiem risinātājiem ir atšķirīgas lomas un atšķirīgs modelēšanas tvērums, tāpēc to rezultāti nav interpretējami mehāniski tikai pēc mērķfunkcijas vērtības.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-141] 4. Algoritmu portfelis un rezultātu interpretācija: Šis nošķīrums ir pamats nākamajā apakšnodaļā aprakstītajai algoritmu izvēles datu kopas izveidei.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-142] 4. Jauktās algoritmu izvēles datu kopas izveide: Pēc risinātāju portfeļa izpildes tika izveidota jaukta algoritmu izvēles datu kopa.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-144] 4. Jauktās algoritmu izvēles datu kopas izveide: Datu kopas izveides mērķis bija sasaistīt pirms risināšanas iegūstamās strukturālās pazīmes ar risinātāju empīriskajiem rezultātiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-145] 4. Jauktās algoritmu izvēles datu kopas izveide: Datu kopas izveide notika vairākos soļos.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-146] 4. Jauktās algoritmu izvēles datu kopas izveide: Vispirms strukturālo pazīmju tabula tika apvienota ar risinātāju izpildes rezultātiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-147] 4. Jauktās algoritmu izvēles datu kopas izveide: Pēc tam tika piemēroti rezultātu derīguma nosacījumi, lai no best_solver kandidātu kopas izslēgtu neatbalstītus, neiestatītus un kļūdainus iznākumus.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-148] 4. Jauktās algoritmu izvēles datu kopas izveide: Sintētisko instanču gadījumā, kur vienai instancei bija vairāki izpildes atkārtojumi, rezultāti vispirms tika apkopoti instances un risinātāja līmenī.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-149] 4. Jauktās algoritmu izvēles datu kopas izveide: Tikai pēc tam katrai instancei tika noteikts piemērotākais risinātājs.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-151] 4. Jauktās algoritmu izvēles datu kopas izveide: Pirms izvēles tika pārbaudīts, vai konkrētais rezultāts ir izmantojams šī darba vērtēšanas tvērumā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-152] 4. Jauktās algoritmu izvēles datu kopas izveide: Šāda pārbaude bija nepieciešama, jo portfelī iekļautajiem risinātājiem ir atšķirīgs modelēšanas tvērums, turklāt daļa rezultātu rindu attiecas uz neatbalstītām instancēm, neiestatītu ārējo integrāciju vai kļūdainu izpildi.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-153] 4. Jauktās algoritmu izvēles datu kopas izveide: Galvenie mērķa mainīgā izveides nosacījumi apkopoti tabulā “Mērķa mainīgā best_solver izveides nosacījumi”.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-155] 4. Jauktās algoritmu izvēles datu kopas izveide: Neatbalstīti, neiestatīti un kļūdaini iznākumi netika izmantoti piemērotākā risinātāja noteikšanai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-156] 4. Jauktās algoritmu izvēles datu kopas izveide: Savukārt daļēji modelēti rezultāti varēja palikt kandidātu kopā, ja tie bija tehniski derīgi un skaitliski salīdzināmi.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-157] 4. Jauktās algoritmu izvēles datu kopas izveide: Tāpēc best_solver šajā darbā jāinterpretē kā piemērotākais risinātājs konkrētajā atskaites portfelī, nevis kā absolūti labākais risinātājs pilnā RobinX vai ITC2021 semantikā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-158] 4. Jauktās algoritmu izvēles datu kopas izveide: Sintētiskajām instancēm pirms best_solver noteikšanas tika veikta rezultātu apkopošana, jo katrai instancei bija vairāki izpildes atkārtojumi ar dažādām nejaušības sākumvērtībām.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-159] 4. Jauktās algoritmu izvēles datu kopas izveide: Rezultāti tika grupēti pēc instances un risinātāja, aprēķinot vidējo mērķfunkcijas vērtību, vidējo izpildes laiku un derīgo izpildes reižu skaitu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-160] 4. Jauktās algoritmu izvēles datu kopas izveide: Šāda apkopošana mazina atsevišķas izpildes nejaušības ietekmi, kas ir īpaši svarīgi heiristiskām pieejām.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-161] 4. Jauktās algoritmu izvēles datu kopas izveide: Ja pēc rezultātu apkopošanas vairākiem risinātājiem bija vienāda mērķfunkcijas vērtība, tika izmantota deterministiska vienādu rezultātu izšķiršanas kārtība.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-162] 4. Jauktās algoritmu izvēles datu kopas izveide: Vispirms priekšroka tika dota zemākai vidējai mērķfunkcijas vērtībai, pēc tam - zemākam vidējam izpildes laikam.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-163] 4. Jauktās algoritmu izvēles datu kopas izveide: Ja arī šie rādītāji sakrita, izvēle tika veikta pēc risinātāja nosaukuma leksikogrāfiskā secībā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-164] 4. Jauktās algoritmu izvēles datu kopas izveide: Šāda kārtība nodrošina, ka best_solver vērtības ir atkārtojami iegūstamas arī vienādu rezultātu gadījumā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-165] 4. Jauktās algoritmu izvēles datu kopas izveide: Papildus strukturālajām pazīmēm un mērķa mainīgajam pilnajā datu kopā tika saglabāti arī pārbaudes un interpretācijas lauki.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-166] 4. Jauktās algoritmu izvēles datu kopas izveide: Tie ietver risinātāju statusus, apkopotās mērķfunkcijas vērtības, izpildes laikus, derīgo izpildes reižu skaitu un pārklājuma informāciju.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-167] 4. Jauktās algoritmu izvēles datu kopas izveide: Šie lauki palīdz pārbaudīt, kāpēc konkrētai instancei piešķirta noteikta best_solver vērtība, taču tie netiek izmantoti kā modeļa ievades pazīmes.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-168] 4. Jauktās algoritmu izvēles datu kopas izveide: Modeļa apmācības ievade tika veidota piesardzīgi, lai mazinātu informācijas noplūdes risku.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-169] 4. Jauktās algoritmu izvēles datu kopas izveide: No ievades pazīmēm tika izslēgti risinātāju rezultāti, mērķa mainīgie, datu izcelsmes lauki un citi pārbaudes lauki.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-171] 4. Jauktās algoritmu izvēles datu kopas izveide: Atsevišķi jāprecizē objective_* kolonnu nozīme.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-172] 4. Jauktās algoritmu izvēles datu kopas izveide: Daļa šo kolonnu apraksta instances mērķfunkcijas informāciju, piemēram, tās esamību vai virzienu, savukārt citas objective_<solver> tipa kolonnas ir saistītas ar risinātāju izpildes rezultātiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-173] 4. Jauktās algoritmu izvēles datu kopas izveide: Konservatīvajā apmācības konfigurācijā abas kolonnu grupas tika izslēgtas no modeļa ievades.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-174] 4. Jauktās algoritmu izvēles datu kopas izveide: Šāds lēmums pieņemts, lai modelis balstītos uz strukturālām pazīmēm, kas pieejamas pirms risināšanas, nevis uz informāciju, kas varētu tieši vai netieši atspoguļot rezultātu vai mērķa mainīgā izveidi.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-175] 4. Jauktās algoritmu izvēles datu kopas izveide: Lai reālās un sintētiskās instances būtu aprakstītas vienotā pazīmju telpā, gala datu kopā tika izmantota abām datu grupām kopīga kolonnu shēma.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-176] 4. Jauktās algoritmu izvēles datu kopas izveide: Pilnajā datu kopā saglabātas 30 pazīmju kolonnas.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-177] 4. Jauktās algoritmu izvēles datu kopas izveide: No tām 25 raksturo instances struktūru šaurākā nozīmē, piemēram, komandu skaitu, laika posmu skaitu, ierobežojumu skaitu, ierobežojumu blīvumu un ierobežojumu daudzveidību.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-178] 4. Jauktās algoritmu izvēles datu kopas izveide: Pārējās 5 kolonnas ir ar mērķfunkcijas aprakstu saistītas objective_* kolonnas.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-179] 4. Jauktās algoritmu izvēles datu kopas izveide: Tās saglabātas pilnajā datu kopā, bet netiek izmantotas konservatīvajā modeļa apmācības konfigurācijā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-180] 4. Jauktās algoritmu izvēles datu kopas izveide: Datu kopas struktūra apkopota tabulā “Algoritmu izvēles datu kopas struktūra”.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-181] 4. Jauktās algoritmu izvēles datu kopas izveide: “Algoritmu izvēles datu kopas struktūra” tabula parāda, ka pilnā datu kopa ir plašāka nekā modeļa apmācībā izmantotā pazīmju matrica.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-182] 4. Jauktās algoritmu izvēles datu kopas izveide: Pilnajā datu kopā saglabāti gan strukturālie rādītāji, gan mērķa mainīgais, gan pārbaudes un interpretācijas lauki.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-183] 4. Jauktās algoritmu izvēles datu kopas izveide: Šāds risinājums ļauj pārbaudīt mērķa mainīgā izveidi, vienlaikus nepieļaujot, ka modeļa apmācībā tiek izmantota informācija par risinātāju rezultātiem vai datu izcelsmi.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-185] 4. Jauktās algoritmu izvēles datu kopas izveide: Visām instancēm tika noteikta best_solver vērtība, tātad katrai instancei bija vismaz viens rezultāts, kas atbilda mērķa mainīgā definēšanas nosacījumiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-186] 4. Jauktās algoritmu izvēles datu kopas izveide: Gala mērķa mainīgajā faktiski parādījās divi risinātāji: reālajām instancēm - simulētās rūdīšanas risinātājs (simulated_annealing_solver), bet sintētiskajām instancēm - CP-SAT modelis (cpsat_solver).
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-187] 4. Jauktās algoritmu izvēles datu kopas izveide: Šis sadalījums turpmāk ņemts vērā modeļa novērtēšanā un rezultātu interpretācijā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-188] 4. Jauktās algoritmu izvēles datu kopas izveide: Šīs apakšnodaļas galvenais secinājums ir, ka algoritmu izvēles datu kopas izveide nav tikai pazīmju un rezultātu mehāniska apvienošana vienā tabulā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-189] 4. Jauktās algoritmu izvēles datu kopas izveide: Šajā posmā tiek noteikts, kuri risinātāju rezultāti var kļūt par best_solver kandidātiem, kā apstrādājami vairāki vienas instances izpildes atkārtojumi un kā nodalāma modeļa ievades informācija no pārbaudes un interpretācijas laukiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-191] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Šāda modeļa izvēle pamatota ar vairākiem apsvērumiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-192] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Pirmkārt, nejaušo mežu modelis var strādāt ar dažāda mēroga skaitliskām pazīmēm bez sarežģītas normalizācijas.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-193] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Otrkārt, tas ir salīdzinoši noturīgs pret trokšņainiem datiem un pazīmju savstarpējām korelācijām, kas var rasties, ja vairākas pazīmes raksturo līdzīgus instances aspektus.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-194] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Treškārt, modelis ļauj iegūt pazīmju nozīmīguma novērtējumu, kas ir noderīgs rezultātu interpretācijā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-195] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Modelis tika veidots kā reproducējama atskaites pieeja, nevis kā maksimāli noskaņots klasifikators.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-196] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tika izmantoti 200 koki, sabalansēta klašu svarošana un fiksēta nejaušības sākumvērtība.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-197] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Paralēlā izpilde netika izmantota, lai mazinātu nekontrolētu izpildes atšķirību ietekmi.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-199] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Modeļa konfigurācija apkopota tabulā “Algoritmu izvēles modeļa konfigurācija”
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-200] 4. Algoritmu izvēles modeļa izveide un novērtēšana: “Algoritmu izvēles modeļa konfigurācija” apkopotā konfigurācija parāda, ka modeļa izveidē priekšroka dota reproducējamībai un interpretējamībai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-201] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Šāda izvēle atbilst darba mērķim - pārbaudīt, vai pirms risināšanas iegūstamās strukturālās pazīmes ietver informāciju, ko iespējams izmantot piemērotākā risinātāja prognozēšanai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-202] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Modeļa ievadi veidoja 25 strukturālās pazīmes, kas raksturo instances izmēru, ierobežojumu sastāvu, blīvumu un daudzveidību.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-204] 4. Algoritmu izvēles modeļa izveide un novērtēšana: No modeļa ievades tika izslēgti risinātāju rezultāti, mērķa mainīgie, datu izcelsmes lauki un citas pārbaudes kolonnas.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-205] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tādējādi modelis tika apmācīts tikai ar informāciju, kas pieejama pirms konkrētās instances risināšanas.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-206] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Pirms rezultātu interpretācijas jāņem vērā mērķa mainīgā sadalījums.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-207] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Datu kopā faktiski parādās divas best_solver klases: reālajām instancēm par piemērotāko risinātāju noteikta simulētā rūdīšana (simulated_annealing_solver), savukārt sintētiskajām instancēm - CP-SAT modelis (cpsat_solver).
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-208] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Lai gan datu izcelsmes kolonnas netika izmantotas modeļa ievadē, reālās un sintētiskās instances var būt netieši atšķiramas pēc strukturālajām pazīmēm.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-209] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tāpēc augsta klasifikācijas precizitāte šajā uzstādījumā jāinterpretē piesardzīgi.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-210] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Modeļa novērtēšana tika veikta ar atkārtotu stratificētu krustoto pārbaudi.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-211] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Katrā pārbaudes sadalījumā modelis tika apmācīts no jauna, izmantojot tikai attiecīgās apmācības daļas datus, un pēc tam pārbaudīts testa daļā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-212] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Gala modelis, kas apmācīts uz pilnās datu kopas, tika saglabāts tikai pēc pārbaudes procedūras pabeigšanas, tāpēc tas neietekmēja novērtēšanas rezultātus.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-213] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Pārbaudes uzstādījums apkopots tabulā “Algoritmu izvēles modeļa pārbaudes uzstādījums”.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-214] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Salīdzinājuma etaloni katrā pārbaudes sadalījumā tika aprēķināti tā, lai netiktu izmantota informācija no testa datiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-215] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Labākais fiksētais risinātājs jeb SBS tika noteikts tikai no attiecīgās apmācības daļas.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-216] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Savukārt virtuāli labākais risinātājs jeb VBS tika aprēķināts testa daļai kā teorētisks etalons, kas katrai instancei izvēlas labāko pieejamo portfeļa risinātāju.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-217] 4. Algoritmu izvēles modeļa izveide un novērtēšana: VBS nav praktiski izmantojams modelis, jo tas balstās uz informāciju par faktisko rezultātu pēc risinātāju izpildes.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-218] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tomēr tas ļauj noteikt teorētiski labāko iespējamo rezultātu konkrētajā portfelī.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-219] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Modeļa kvalitātes novērtēšanai izmantoti gan klasifikācijas, gan optimizācijas kvalitātes rādītāji.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-220] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Klasifikācijas precizitāte parāda, cik bieži modelis pareizi prognozē best_solver, savukārt sabalansētā precizitāte ļauj ņemt vērā klašu nelīdzsvaru.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-221] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Optimizācijas kvalitātes interpretācijai izmantota vidējā mērķfunkcijas vērtība, nožēlas rādītājs attiecībā pret VBS un ieguvums attiecībā pret SBS.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-222] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Algoritmu izvēles modeļa veiktspējas kopsavilkums dots tabulā “Algoritmu izvēles modeļa veiktspējas kopsavilkums”.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-224] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tā kā šajā eksperimentā zemāka mērķfunkcijas vērtība nozīmē labāku rezultātu, modeļa vidējā mērķfunkcijas vērtība ir labāka nekā SBS un ļoti tuva VBS vērtībai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-225] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tas nozīmē, ka konkrētajā atskaites portfelī modelis vidēji uzlabo viena fiksēta risinātāja izvēli un pietuvojas teorētiski labākajai izvēlei.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-226] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Papildus kopējiem rādītājiem rezultāti aplūkoti arī pa datu grupām.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-227] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Šāds dalījums ir būtisks, jo kopējie rādītāji var noslēpt atšķirīgu modeļa uzvedību reālajās un sintētiskajās instancēs.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-228] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Šajā griezumā sabalansētā precizitāte netiek interpretēta atsevišķi, jo katrā datu grupā dominē viena mērķa klase.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-229] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Rezultāti apkopoti tabulā “Algoritmu izvēles modeļa rezultāti pa datu grupām”.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-230] 4. Algoritmu izvēles modeļa izveide un novērtēšana: “Algoritmu izvēles modeļa rezultāti pa datu grupām” parāda, ka sintētiskajās instancēs modelis pilnībā atjaunoja mērķa klasi, savukārt reālajās instancēs saglabājās neliela kļūdu daļa.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-231] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tas apstiprina, ka kopējā precizitāte jāinterpretē kopā ar datu grupu sadalījumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-232] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Šajā eksperimentālajā konfigurācijā sintētisko instanču daļā uzdevums ir stabilāks, bet reālo instanču daļā algoritmu izvēle ir nedaudz sarežģītāka.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-233] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Modeļa, SBS un VBS vidējo mērķfunkcijas vērtību salīdzinājums parādīts attēlā “Algoritmu izvēles modeļa salīdzinājums ar SBS un VBS”.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-234] 4. Algoritmu izvēles modeļa izveide un novērtēšana: “Algoritmu izvēles modeļa salīdzinājums ar SBS un VBS” attēlā redzams, ka modeļa vidējā mērķfunkcijas vērtība ir tuvāka VBS nekā SBS rezultātam.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-235] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Modelis sasniedz vidējo vērtību 19,53, VBS - 19,51, bet SBS - 19,90.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-236] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tādējādi modelis samazina vidējo mērķfunkcijas vērtību salīdzinājumā ar viena fiksēta risinātāja pieeju.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-237] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Vienlaikus kļūdu stabiņi attēlā pārklājas, tāpēc šis rezultāts jāinterpretē kā praktiska tendence konkrētajā pārbaudes shēmā, nevis kā pierādījums universālam algoritmu izvēles modeļa pārākumam.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-239] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Novērtēšanas rezultāti bija samērā stabili dažādos datu sadalījumos.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-240] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Klasifikācijas precizitātes standartnovirze bija 0,0064, sabalansētās precizitātes standartnovirze - 0,0139, bet nožēlas rādītāja standartnovirze - 0,0192.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-241] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tas norāda, ka rezultāts nav balstīts tikai uz vienu veiksmīgu datu sadalījumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-242] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tomēr šāda stabilitāte nenozīmē, ka modelis automātiski būtu vispārināms uz citām datu kopām vai pilnīgāku risinātāju portfeli.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-243] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Svarīgākais interpretācijas ierobežojums ir saistīts ar mērķa mainīgā sadalījumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-244] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Pašreizējā jauktajā datu kopā best_solver cieši sakrīt ar datu apakškopas raksturu: sintētiskajās instancēs par piemērotāko risinātāju noteikts cpsat_solver, savukārt reālajās instancēs - simulated_annealing_solver.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-245] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Lai gan datu izcelsmes lauki netika izmantoti modeļa ievadē, reālās un sintētiskās instances var būt netieši atšķiramas pēc strukturālajām pazīmēm, piemēram, komandu skaita, laika posmu skaita, ierobežojumu skaita, ierobežojumu blīvuma vai ierobežojumu daudzveidības.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-246] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tāpēc augstā precizitāte šajā darbā galvenokārt parāda, ka izveidotajā jauktajā datu kopā strukturālās pazīmes ir pietiekamas best_solver vērtības atjaunošanai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-247] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Tā vēl nepierāda, ka modelis spētu vispārināties uz jaunu reālo instanču kopu vai uz portfeli ar pilnīgāku RobinX un ITC2021 ierobežojumu semantikas atbalstu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-248] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Šīs apakšnodaļas galvenais secinājums ir, ka algoritmu izvēles pieeja konkrētajā eksperimentālajā uzstādījumā darbojas un sniedz izmērāmu ieguvumu salīdzinājumā ar labāko fiksēto risinātāju.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-249] 4. Algoritmu izvēles modeļa izveide un novērtēšana: Vienlaikus rezultātu vispārināšanai nepieciešama plašāka un līdzsvarotāka datu kopa, kurā mērķa klašu sadalījums nav tik cieši saistīts ar datu izcelsmi, kā arī pilnīgāks risinātāju portfelis ar plašāku RobinX un ITC2021 ierobežojumu semantikas atbalstu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-250] 4. Eksperimentu rezultāti: Šajā apakšnodaļā algoritmu izvēles modeļa rezultāti aplūkoti detalizētāk nekā kopējā veiktspējas novērtējumā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-251] 4. Eksperimentu rezultāti: Galvenā uzmanība pievērsta mērķa klašu sadalījumam, klasifikācijas kļūdām un pazīmju nozīmīguma interpretācijai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-252] 4. Eksperimentu rezultāti: Šāda analīze ir nepieciešama, jo augsta kopējā precizitāte pati par sevi vēl neparāda, pēc kādas informācijas modelis veic prognozes un kādos gadījumos tas kļūdās.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-253] 4. Eksperimentu rezultāti: Būtiska eksperimenta īpatnība ir mērķa mainīgā best_solver sadalījums.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-254] 4. Eksperimentu rezultāti: Pašreizējā jauktajā datu kopā sintētiskajām instancēm par piemērotāko risinātāju visos gadījumos noteikts CP-SAT modelis (cpsat_solver), savukārt reālajām instancēm - simulētās rūdīšanas risinātājs (simulated_annealing_solver).
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-255] 4. Eksperimentu rezultāti: Tādēļ algoritmu izvēles uzdevums šajā eksperimentālajā uzstādījumā daļēji pārklājas ar strukturāli atšķirīgu instanču grupu nošķiršanu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-256] 4. Eksperimentu rezultāti: Šis apstāklis jāņem vērā, interpretējot gan augsto klasifikācijas precizitāti, gan pazīmju nozīmīguma rezultātus.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-257] 4. Eksperimentu rezultāti: Kļūdu analīze rāda, ka deviņos pārbaudes sadalījumos tika novērotas tikai trīs klasifikācijas kļūdas.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-258] 4. Eksperimentu rezultāti: Visas kļūdas attiecās uz vienu un to pašu reālo instanci - Test Instance Demo, kas atkārtotās krustotās pārbaudes dēļ vairākos sadalījumos nonāca testa daļā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-259] 4. Eksperimentu rezultāti: Šajos gadījumos modelis prognozēja cpsat_solver, lai gan pēc mērķa mainīgā definīcijas piemērotākais risinātājs bija simulated_annealing_solver.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-260] 4. Eksperimentu rezultāti: Katras šādas kļūdas nožēlas rādītājs pret VBS bija 3,0 mērķfunkcijas vienības.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-261] 4. Eksperimentu rezultāti: Kļūdas nebija vienmērīgi izkliedētas visā datu kopā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-262] 4. Eksperimentu rezultāti: cpsat_solver klase tika prognozēta pareizi 540 gadījumos no 540, savukārt simulated_annealing_solver klase - 159 gadījumos no 162.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-263] 4. Eksperimentu rezultāti: Trīs atlikušajos gadījumos simulated_annealing_solver tika sajaukts ar cpsat_solver.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-264] 4. Eksperimentu rezultāti: Tas nozīmē, ka kļūdas koncentrējas vienā konkrētā robežgadījumā, nevis atkārtojas dažādos instanču tipos.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-265] 4. Eksperimentu rezultāti: Šāda kļūdu koncentrācija ir būtiska rezultātu interpretācijai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-266] 4. Eksperimentu rezultāti: Tā norāda, ka modelis kopumā stabili nošķir abas mērķa klases, tomēr viena reālā instance pēc strukturālajām pazīmēm, visticamāk, ir tuvāka sintētisko instanču profilam vai neatbilst tipiskajam reālo instanču raksturojumam.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-267] 4. Eksperimentu rezultāti: Tā kā mērķa telpā faktiski parādās tikai divi risinātāji, kļūdu analīze šajā eksperimentā galvenokārt nozīmē to gadījumu izpēti, kuros modelis sajauc cpsat_solver un simulated_annealing_solver.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-268] 4. Eksperimentu rezultāti: Svarīgāko pazīmju nozīmīgums nejaušo mežu modelī parādīts attēlā “Svarīgāko strukturālo pazīmju nozīmīgums algoritmu izvēles modelī”.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-269] 4. Eksperimentu rezultāti: Attēlā “Svarīgāko strukturālo pazīmju nozīmīgums algoritmu izvēles modelī” redzams, ka nozīmīgākās pazīmes galvenokārt saistītas ar ierobežojumu blīvumu, ierobežojumu sastāvu un ierobežojumu daudzveidību.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-270] 4. Eksperimentu rezultāti: Augstāko nozīmīgumu ieguva constraints_per_slot, ratio_constraint_tags_to_constraints, num_soft_constraints, ratio_constraint_types_to_constraints un constraints_per_team.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-271] 4. Eksperimentu rezultāti: Lai gan šie nosaukumi ir datu kopas kolonnu nosaukumi, to saturs ir interpretējams arī plašākā strukturālā nozīmē.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-272] 4. Eksperimentu rezultāti: Šīs pazīmes var sasaistīt ar vairākiem vispārīgiem strukturāliem rādītājiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-273] 4. Eksperimentu rezultāti: constraints_per_slot, slot_pressure un slot_surplus raksturo ierobežojumu slodzi attiecībā pret laika resursu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-274] 4. Eksperimentu rezultāti: constraints_per_team raksturo ierobežojumu slodzi attiecībā pret plānojamajiem objektiem, šajā gadījumā komandām.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-275] 4. Eksperimentu rezultāti: num_soft_constraints un num_hard_constraints raksturo attiecīgi kvalitātes kritēriju apjomu un pieļaujamības nosacījumu apjomu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-276] 4. Eksperimentu rezultāti: Savukārt ratio_constraint_tags_to_constraints, ratio_constraint_types_to_constraints un ratio_constraint_categories_to_constraints raksturo ierobežojumu daudzveidību.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-277] 4. Eksperimentu rezultāti: Tādējādi modelī nozīmīgās pazīmes nav tikai tehniski kolonnu nosaukumi, bet rādītāji, kas apraksta risinājumu telpas ierobežotību, kvalitātes kritēriju nozīmi un prasību struktūras daudzveidību.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-278] 4. Eksperimentu rezultāti: Lai novērtētu, vai modelis balstās galvenokārt uz instances izmēru vai izmanto arī ierobežojumu struktūras informāciju, pazīmju nozīmīgums tika apkopots pa pazīmju grupām.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-279] 4. Eksperimentu rezultāti: Rezultāti apkopoti tabulā “Pazīmju grupu kopējais nozīmīgums”.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-280] 4. Eksperimentu rezultāti: Tabulā “Pazīmju grupu kopējais nozīmīgums” redzams, ka lielāko kopējo nozīmīgumu veido ierobežojumu daudzveidības un blīvuma pazīmes.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-281] 4. Eksperimentu rezultāti: Tas ir būtiski darba interpretācijai, jo modelis nebalstās tikai uz instances izmēru, piemēram, komandu vai laika posmu skaitu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-282] 4. Eksperimentu rezultāti: Lielāka nozīme ir tam, kā ierobežojumi sadalās, cik intensīvi tie noslogo laika posmus un komandas, kā arī cik daudzveidīga ir ierobežojumu struktūra.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-283] 4. Eksperimentu rezultāti: Šis rezultāts atbalsta darba pieņēmumu, ka algoritmu izvēlē nozīmīga var būt ne tikai problēmas mēroga informācija, bet arī ierobežojumu organizācija.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-284] 4. Eksperimentu rezultāti: Vienlaikus pazīmju nozīmīguma rezultāti jāinterpretē piesardzīgi.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-285] 4. Eksperimentu rezultāti: Nejaušo mežu pazīmju nozīmīgums parāda, kuras pazīmes modelis izmanto prognozēšanā, bet nepierāda cēlonisku saistību starp konkrētu pazīmi un risinātāja pārākumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-286] 4. Eksperimentu rezultāti: Turklāt reālās un sintētiskās instances šajā datu kopā būtiski atšķiras pēc struktūras, tāpēc daļa pazīmju nozīmīguma var atspoguļot šo divu datu grupu atšķirības.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-287] 4. Eksperimentu rezultāti: Tādēļ šie rezultāti nav jāinterpretē tā, ka, piemēram, lielāka constraints_per_slot vērtība vienmēr nozīmē konkrēta risinātāja priekšrocību.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-288] 4. Eksperimentu rezultāti: Tie drīzāk rāda, ka šāda strukturālā informācija šajā eksperimentālajā uzstādījumā ir noderīga modeļa lēmumu pieņemšanā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-289] 4. Eksperimentu rezultāti: Šīs apakšnodaļas galvenais secinājums ir, ka strukturālās pazīmes ietver informāciju, ko modelis izmanto best_solver prognozēšanai konkrētajā jauktajā datu kopā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-290] 4. Eksperimentu rezultāti: Tomēr iegūtie rezultāti nav uzskatāmi par galīgu pierādījumu universālai algoritmu izvēles metodei sporta turnīru kalendāru sastādīšanā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-291] 4. Eksperimentu rezultāti: Tie apstiprina pieejas realizējamību konkrētajā eksperimentālajā vidē, vienlaikus norādot uz nepieciešamību pārbaudīt pieeju līdzsvarotākā datu kopā un ar pilnīgāku risinātāju portfeli.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-292] 4. Rezultātu interpretācija un ierobežojumi: Eksperimentālās daļas rezultāti parāda, ka algoritmu izvēles pieeju sporta turnīru kalendāru sastādīšanā var īstenot reproducējamā veidā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-293] 4. Rezultātu interpretācija un ierobežojumi: Izveidotā procedūra ļauj sasaistīt instanču strukturālās pazīmes ar risinātāju portfeļa rezultātiem, definēt mērķa mainīgo best_solver un novērtēt modeli piemērotākā risinātāja prognozēšanai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-294] 4. Rezultātu interpretācija un ierobežojumi: Vienlaikus rezultāti jāinterpretē konkrētā eksperimentālā uzstādījuma robežās, jo datu kopas sastāvs, risinātāju portfelis un vērtēšanas tvērums būtiski ietekmē gan mērķa mainīgo, gan modeļa novērtējumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-295] 4. Rezultātu interpretācija un ierobežojumi: Būtiskākais praktiskais rezultāts ir izveidotā un pārbaudāmā algoritmu izvēles eksperimentālā procedūra.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-296] 4. Rezultātu interpretācija un ierobežojumi: Instances tiek raksturotas ar pirms risināšanas iegūstamām strukturālām pazīmēm, risinātāju rezultāti tiek saglabāti kopā ar interpretācijas statusiem, bet mērķa mainīgais tiek veidots tikai no tehniski izmantojamiem rezultātiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-297] 4. Rezultātu interpretācija un ierobežojumi: Šāds nodalījums mazina informācijas noplūdes risku un ļauj pārbaudīt, kā katrai instancei iegūta konkrētā best_solver vērtība.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-298] 4. Rezultātu interpretācija un ierobežojumi: Empīriskie rezultāti rāda, ka konkrētajā jauktajā datu kopā modelis sasniedza augstu prognozēšanas precizitāti un uzlaboja vidējo mērķfunkcijas vērtību salīdzinājumā ar labāko fiksēto risinātāju.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-299] 4. Rezultātu interpretācija un ierobežojumi: Tomēr šis rezultāts nav uzskatāms par pierādījumu universālai algoritmu izvēles modeļa efektivitātei.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-300] 4. Rezultātu interpretācija un ierobežojumi: Pašreizējā datu kopā mērķa klašu sadalījums ir cieši saistīts ar datu grupām, tāpēc augstā precizitāte galvenokārt parāda, ka strukturālās pazīmes ir pietiekamas šīs konkrētās mērķa vērtības atjaunošanai.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-301] 4. Rezultātu interpretācija un ierobežojumi: Pazīmju nozīmīguma analīze norāda, ka modelis prognozēšanā izmantoja ne tikai instances izmēra pazīmes, bet arī ierobežojumu blīvuma, sastāva un daudzveidības rādītājus.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-302] 4. Rezultātu interpretācija un ierobežojumi: Tas atbilst darba pieņēmumam, ka algoritmu izvēlē nozīme var būt ne tikai komandu vai laika posmu skaitam, bet arī ierobežojumu organizācijai konkrētajā instancē.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-303] 4. Rezultātu interpretācija un ierobežojumi: Vienlaikus šie rezultāti jāinterpretē piesardzīgi, jo pazīmju nozīmīgums nepierāda cēlonisku saistību starp konkrētu pazīmi un risinātāja pārākumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-304] 4. Rezultātu interpretācija un ierobežojumi: Galvenie eksperimenta ierobežojumi apkopoti “Eksperimenta ierobežojumu kopsavilkums” tabulā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-305] 4. Rezultātu interpretācija un ierobežojumi: Tabulā “Eksperimenta ierobežojumu kopsavilkums” apkopotie ierobežojumi parāda, ka galvenie piesardzības iemesli saistīti nevis ar modeļa tehnisku darbību, bet ar eksperimenta uzstādījumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-306] 4. Rezultātu interpretācija un ierobežojumi: Īpaši svarīgi ir tas, ka best_solver nenozīmē objektīvi labāko algoritmu visai sporta turnīru kalendāru sastādīšanas problēmu klasei.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-307] 4. Rezultātu interpretācija un ierobežojumi: Tas apzīmē piemērotāko tehniski izmantojamo risinātāju šajā datu kopā, šajā atskaites portfelī un šajā vērtēšanas tvērumā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-308] 4. Rezultātu interpretācija un ierobežojumi: Ja portfelī tiktu iekļauti pilnīgāki risinātāji ar plašāku RobinX un ITC2021 ierobežojumu semantikas atbalstu, mērķa mainīgā sadalījums un modeļa secinājumi varētu mainīties.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-309] 4. Rezultātu interpretācija un ierobežojumi: No metodoloģiskā viedokļa darba praktiskās daļas vērtība nav tikai sasniegtā klasifikācijas precizitāte.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-310] 4. Rezultātu interpretācija un ierobežojumi: Būtiska ir arī pati eksperimentālā procedūra: tajā atsevišķi nodalīts instances strukturālais apraksts, risinātāju izpildes rezultāti, rezultātu derīguma statusi, mērķa mainīgā izveides informācija un modeļa apmācībā izmantojamās pazīmes.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-311] 4. Rezultātu interpretācija un ierobežojumi: Šāds nodalījums ļauj pārbaudīt datu kopas izveidi un uztur algoritmu izvēles uzdevuma korektu interpretāciju.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-312] 4. Rezultātu interpretācija un ierobežojumi: Kopumā rezultāti apstiprina algoritmu izvēles pieejas realizējamību konkrētajā pētījuma uzstādījumā.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-313] 4. Rezultātu interpretācija un ierobežojumi: Strukturālās pazīmes šajā datu kopā ietver informāciju, ar kuru iespējams prognozēt best_solver, un modelis sasniedz labākus rezultātus nekā labākais fiksētais risinātājs.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-314] 4. Rezultātu interpretācija un ierobežojumi: Tomēr šis secinājums attiecas uz šajā darbā definēto datu kopu, atskaites portfeli un vērtēšanas tvērumu.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- [DATA-315] 4. Rezultātu interpretācija un ierobežojumi: Pieejas vispārināmības pārbaudei nepieciešama plašāka un līdzsvarotāka instanču kopa, neatkarīga pārbaude un portfelis ar vairākiem pilnvērtīgiem, savstarpēji konkurējošiem risinātājiem.
  Note: This sentence is interpretive or too broad for exact machine validation from repository artifacts.

## Recommended thesis text fixes

- Review DATA-1 in `ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-2 in `ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-3 in `ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-4 in `ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-5 in `ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-6 in `ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-7 in `ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-8 in `ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-9 in `ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-10 in `ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-11 in `ALGORITMU IZVĒLES EKSPERIMENTĀLĀ IZPĒTE SPORTA TURNĪRU KALENDĀRU SASTĀDĪŠANĀ`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-12 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-13 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-14 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-15 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-16 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-17 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-18 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-19 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-20 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-21 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-22 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-23 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-24 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-25 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-26 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-27 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-28 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-29 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-30 in `4. Eksperimentālās daļas mērķis un vispārējā uzbūve`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-31 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-32 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-33 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-34 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-35 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-36 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-37 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-38 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-39 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-41 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-42 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-43 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-44 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-45 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-46 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-47 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-49 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-50 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-51 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-52 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-53 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-54 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-55 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-56 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-57 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-58 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-59 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-60 in `4. Datu avoti un datu sagatavošana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-61 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-62 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-63 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-64 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-65 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-66 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-67 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-68 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-69 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-70 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-71 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-72 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-73 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-74 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-75 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-76 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-77 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-78 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-79 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-80 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-81 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-82 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-83 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-84 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-85 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-86 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-87 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-88 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-89 in `4. Instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-90 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-91 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-92 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-93 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-95 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-96 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-97 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-98 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-99 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-100 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-101 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-102 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-103 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-104 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-105 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-106 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-107 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-108 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-109 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-110 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-111 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-112 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-113 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-114 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-115 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-116 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-118 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-119 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-120 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-121 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-123 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-124 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-125 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-126 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-127 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-128 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-129 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-130 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-131 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-132 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-133 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-134 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-135 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-136 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-137 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-138 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-139 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-140 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-141 in `4. Algoritmu portfelis un rezultātu interpretācija`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-142 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-144 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-145 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-146 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-147 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-148 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-149 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-151 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-152 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-153 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-155 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-156 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-157 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-158 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-159 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-160 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-161 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-162 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-163 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-164 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-165 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-166 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-167 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-168 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-169 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-171 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-172 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-173 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-174 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-175 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-176 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-177 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-178 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-179 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-180 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-181 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-182 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-183 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-185 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-186 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-187 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-188 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-189 in `4. Jauktās algoritmu izvēles datu kopas izveide`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-191 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-192 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-193 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-194 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-195 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-196 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-197 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-199 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-200 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-201 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-202 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-204 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-205 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-206 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-207 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-208 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-209 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-210 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-211 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-212 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-213 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-214 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-215 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-216 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-217 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-218 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-219 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-220 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-221 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-222 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-224 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-225 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-226 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-227 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-228 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-229 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-230 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-231 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-232 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-233 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-234 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-235 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-236 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-237 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-239 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-240 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-241 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-242 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-243 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-244 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-245 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-246 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-247 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-248 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-249 in `4. Algoritmu izvēles modeļa izveide un novērtēšana`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-250 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-251 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-252 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-253 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-254 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-255 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-256 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-257 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-258 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-259 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-260 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-261 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-262 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-263 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-264 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-265 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-266 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-267 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-268 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-269 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-270 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-271 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-272 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-273 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-274 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-275 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-276 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-277 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-278 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-279 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-280 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-281 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-282 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-283 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-284 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-285 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-286 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-287 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-288 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-289 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-290 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-291 in `4. Eksperimentu rezultāti`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-292 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-293 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-294 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-295 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-296 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-297 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-298 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-299 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-300 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-301 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-302 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-303 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-304 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-305 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-306 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-307 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-308 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-309 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-310 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-311 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-312 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-313 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-314 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
- Review DATA-315 in `4. Rezultātu interpretācija un ierobežojumi`: This sentence is interpretive or too broad for exact machine validation from repository artifacts.
