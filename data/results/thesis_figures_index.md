# Darbam sagatavoto attēlu indekss

- `selector_performance.png`
  Virsraksts: Nejaušo mežu klasifikatora galvenie rādītāji
  Apraksts: Attēlā vienkopus parādīti četri jauktās datu kopas galvenie novērtējuma rādītāji.
  Nozīme: Tas parāda pieejas realizējamību šajā eksperimentālajā uzstādījumā, nevis universālu algoritmu izvēles efektivitāti.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/selector_performance.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/selector_performance.png)
- `selector_vs_baselines.png`
  Virsraksts: Algoritmu izvēles modeļa salīdzinājums ar SBS un VBS
  Apraksts: Attēlā salīdzināta algoritmu izvēles modeļa, viena labākā fiksētā risinātāja un virtuāli labākā risinātāja vidējā mērķfunkcijas vērtība.
  Nozīme: Tas ļauj redzēt, kā izvēles modelis uzvedas pret SBS un VBS atskaites punktiem konkrētajā datu kopā.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/selector_vs_baselines.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/selector_vs_baselines.png)
- `solver_comparison.png`
  Virsraksts: Atskaites risinātāju kvalitāte pēc datu tipa
  Apraksts: Grafikā salīdzināta risinātāju vidējā sasniegtā kvalitāte reālajās un sintētiskajās instancēs.
  Nozīme: Tas jālasa kopā ar risinātāju tvērumu: CP-SAT un simulētā rūdīšana ir atskaites risinātāji, bet Timefold nav konfigurēts.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/solver_comparison.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/solver_comparison.png)
- `solver_runtime.png`
  Virsraksts: Atskaites risinātāju izpildes laiks
  Apraksts: Attēlā redzams vidējais izpildes laiks pa risinātājiem, nošķirot reālās un sintētiskās instances.
  Nozīme: No šī var secināt, ka kvalitāte jāvērtē kopā ar aprēķina laiku.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/solver_runtime.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/solver_runtime.png)
- `feature_importance.png`
  Virsraksts: Desmit nozīmīgākās strukturālās pazīmes nejaušo mežu klasifikatorā
  Apraksts: Grafikā parādītas desmit strukturālās pazīmes ar lielāko nozīmīgumu nejaušo mežu klasifikatorā.
  Nozīme: Pazīmju nozīmīgums rāda, kuras pazīmes modelis izmanto prognozēšanā šajā datu kopā. Tas nepierāda cēlonisku saistību starp pazīmi un risinātāja pārākumu. Rezultāti jāinterpretē kopā ar datu avota efektu un pārējiem eksperimenta ierobežojumiem.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/feature_importance.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/feature_importance.png)
- `real_vs_synthetic.png`
  Virsraksts: Reālo un sintētisko datu salīdzinājums
  Apraksts: Attēlā salīdzināti galvenie modeļa rezultāti abās datu grupās: precizitāte, kvalitāte un regret.
  Nozīme: Tas parāda, ka rezultāti jāinterpretē atsevišķi pa datu avotiem un piesardzīgi pret datu avota efektu.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/real_vs_synthetic.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/real_vs_synthetic.png)
- `solver_win_distribution.png`
  Virsraksts: best_solver klašu sadalījums pa datu avotiem
  Apraksts: Diagramma rāda gala best_solver klašu sadalījumu reālajās un sintētiskajās instancēs.
  Nozīme: Tas nodala reālo un sintētisko datu klašu sadalījumu un nepasniedz Timefold kā aktīvu salīdzinājuma dalībnieku.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/solver_win_distribution.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/solver_win_distribution.png)
- `dataset_distribution.png`
  Virsraksts: Eksperimentā izmantotās datu kopas sastāvs
  Apraksts: Attēlā parādīts instanču sadalījums pa datu tipiem.
  Nozīme: Tas parāda jauktās datu kopas sastāvu un sintētisko instanču lielo īpatsvaru, kas jāņem vērā rezultātu interpretācijā.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/dataset_distribution.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/dataset_distribution.png)
- `best_solver_class_distribution.png`
  Virsraksts: best_solver klašu sadalījums
  Apraksts: Attēlā parādīts, cik bieži katrs risinātājs kļūst par best_solver visā jauktajā datu kopā.
  Nozīme: Tas parāda divas aktīvas mērķa klases un palīdz pamanīt, ka klašu sadalījums cieši sakrīt ar datu avotu.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/best_solver_class_distribution.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/best_solver_class_distribution.png)
- `objective_distribution.png`
  Virsraksts: Mērķfunkcijas vērtību sadalījums
  Apraksts: Diagrammā salīdzināts labākais sasniegtais mērķfunkcijas līmenis reālajās un sintētiskajās instancēs.
  Nozīme: No šī var secināt, ka abu datu grupu optimizācijas grūtības līmenis atšķiras.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/objective_distribution.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/objective_distribution.png)
- `runtime_distribution.png`
  Virsraksts: Izpildes laika sadalījums
  Apraksts: Kastes diagrammā parādīts algoritmu izpildes laiku sadalījums, izmantojot visus saglabātos benchmark rezultātus.
  Nozīme: Tas ļauj novērtēt ne tikai vidējo laiku, bet arī rezultātu izkliedi un stabilitāti.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/runtime_distribution.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/runtime_distribution.png)
- `accuracy_by_dataset_type.png`
  Virsraksts: Precizitāte pa datu tipiem
  Apraksts: Diagramma salīdzina precizitāti jauktajā kopā, reālajās instancēs un sintētiskajās instancēs.
  Nozīme: Tas parāda, ka kopējais rezultāts jāinterpretē kopā ar abu datu apakškopu uzvedību.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/accuracy_by_dataset_type.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/accuracy_by_dataset_type.png)
- `regret_distribution.png`
  Virsraksts: Regret sadalījums validācijas sadalījumos
  Apraksts: Attēlā parādīts regret sadalījums pa validācijas sadalījumiem un datu tipiem.
  Nozīme: Tas parāda, cik stabils modelis ir dažādos validācijas griezumos.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/regret_distribution.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/regret_distribution.png)
- `confusion_matrix.png`
  Virsraksts: Klasifikācijas kļūdu matrica
  Apraksts: Matrica apkopo, cik bieži modelis katru patieso labāko algoritmu prognozēja kā konkrētu portfeļa algoritmu.
  Nozīme: Tas palīdz redzēt, ka kļūdas koncentrējas šaurā robežgadījumu daļā, nevis vienmērīgi visās klasēs.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/confusion_matrix.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/confusion_matrix.png)
- `feature_correlation_matrix.png`
  Virsraksts: Svarīgāko pazīmju korelācijas
  Apraksts: Korelāciju matrica parāda savstarpējās saites starp modeļa svarīgākajām strukturālajām pazīmēm.
  Nozīme: No šī var secināt, kur pazīmes nes līdzīgu informāciju un kur tās viena otru papildina.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/feature_correlation_matrix.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/feature_correlation_matrix.png)
- `constraint_distribution.png`
  Virsraksts: Ierobežojumu sadalījums instancēs
  Apraksts: Attēlā salīdzināts kopējais, stingro un mīksto ierobežojumu sadalījums reālajās un sintētiskajās instancēs.
  Nozīme: Tas parāda, cik atšķirīga ir problēmu struktūra un kāpēc viena algoritma dominance nevar tikt pieņemta automātiski.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/constraint_distribution.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/constraint_distribution.png)
- `teams_vs_slots_plot.png`
  Virsraksts: Komandu skaits pret laika vietu skaitu
  Apraksts: Izkliedes diagramma rāda, kā instanču izmērs sadalās pa datu tipiem pēc komandu un laika vietu skaita.
  Nozīme: Tas parāda, cik plašu strukturālo telpu aptver izmantotā datu kopa.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/teams_vs_slots_plot.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/teams_vs_slots_plot.png)
- `constraints_vs_objective.png`
  Virsraksts: Ierobežojumu skaits pret sasniegto kvalitāti
  Apraksts: Diagramma salīdzina instanču ierobežojumu skaitu ar labāko sasniegto mērķfunkcijas vērtību.
  Nozīme: Tas parāda, ka strukturālā sarežģītība ir saistīta ar sasniedzamās kvalitātes līmeni.
  Avots: Precīzais artefakts GitHub krātuvē (skatīt šeit): [data/results/figures/constraints_vs_objective.png](https://github.com/kaasgz/magistraDarbs/blob/main/data/results/figures/constraints_vs_objective.png)
