# MDL-Beträge werden nie nachgerechnet (K14)

Betrag / Satz: Eine hochgeladene Messdienst-Abrechnung wird validiert (Kontrollsumme M3), aber nie neu berechnet. Der ausgewiesene Betrag je Nutzeinheit wird unverändert übernommen.
Betroffene Seite: 01b · Heizkosten- & CO₂-Verteilung (../../Spec-Seiten/01b%20%C2%B7%20Heizkosten-%20&%20CO%E2%82%82-Verteilung%203a95fd420731814e9e5be043028d4856.md)
Flag: verify-before-production
Letzte Änderung um: 27. Juli 2026 19:16
Prüfen bis: 5. August 2026
Rechtsgrundlage §: keine — Produkt- und Haftungsentscheidung. Lokara hat keine Rechtsposition, eine Messdienst-Abrechnung zu überstimmen; zwei konkurrierende Zahlen für denselben Mieter wären ein Haftungsrisiko.
Rechtsnatur: Konvention
Rechtsstand: 07/2026

Angelegt am 27.07.2026 bei der Querprüfung Seite 01b gegen das Register — die Konvention stand auf 01b als **K14**, hatte aber keinen Registereintrag.

**Abgrenzung:** Validieren heißt Kontrollsumme, Vollständigkeit und Plausibilität prüfen (H7 / M1–M3). Nachrechnen hieße, aus den Rohdaten eine eigene Verteilung zu erzeugen und der des Messdiensts gegenüberzustellen. Letzteres ist bewusst ausgeschlossen.

**Was daraus folgt:** Im MDL-Pfad gibt es keinen Verteilungsrest aus eigener Rechnung. Weicht die Summe vom erwarteten Gesamtbetrag ab, ist das ein Eingabe- oder OCR-Problem und wird über M3 behandelt — nicht durch stille Korrektur.