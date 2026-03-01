Spust CogniLayer TUI Dashboard pro vizualni spravu pameti.

Spust tento prikaz:
```
python ~/.cognilayer/tui/app.py
```

Pro konkretni projekt pridej `--project <nazev>`:
```
python ~/.cognilayer/tui/app.py --project $ARGUMENTS
```

TUI ma 7 tabu:
1. **Prehled** — Statistiky, zdravi pameti, posledni session
2. **Fakty** — Prohledavatelny seznam faktu s filtry
3. **Heat mapa** — Distribuce heat score podle typu a projektu
4. **Clustery** — Stromove zobrazeni clusteru faktu
5. **Timeline** — Historie sessions s epizodami
6. **Mezery** — Sledovac mezer ve znalostech
7. **Kontradikce** — Prehled kontradikci (R pro vyreseni)

Klavesy: 1-7 pro taby, Q pro ukonceni, R pro obnoveni.
