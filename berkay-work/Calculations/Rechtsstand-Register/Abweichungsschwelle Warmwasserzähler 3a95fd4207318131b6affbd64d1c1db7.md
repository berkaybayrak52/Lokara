# Abweichungsschwelle Warmwasserzähler

Betrag / Satz: Zweistufig zwischen Σ Wohnungszähler und zentralem Volumen: ab 10 % Hinweis (nicht blockierend), ab 20 % Warnung mit Rechtsfolgenhinweis. Nie Blockade.
Betroffene Seite: 01b · Heizkosten- & CO₂-Verteilung (../Spec-Seiten/01b%20%C2%B7%20Heizkosten-%20&%20CO%E2%82%82-Verteilung%203a95fd420731814e9e5be043028d4856.md)
Flag: verify-before-production
Letzte Änderung um: 27. Juli 2026 17:00
Prüfen bis: 5. August 2026
Rechtsgrundlage §: keine — Produktheuristik. Anknüpfung untere Stufe: Verkehrsfehlergrenze Wohnungswasserzähler nach § 22 Abs. 2 MessEV i. V. m. RL 2014/32/EU Anhang III (MI-001) = doppelte Eichfehlergrenze, also ± 10 % im unteren und ± 4 % im oberen Belastungsbereich. Obere Stufe (20 %): NICHT gegen eine Primärquelle verifiziert — die Zahl stammt aus Instanzrechtsprechung zur Umlagefähigkeit, konkrete Fundstelle steht aus.
Rechtsnatur: Heuristik
Rechtsstand: 07/2026

## Korrigiert am 27.07.2026: 5 % → zweistufig 10 % / 20 %

Die alte 5-%-Schwelle lag **unterhalb der normalen Messtoleranz** und hätte in der Mehrzahl der Bestandsgebäude ausgelöst, ohne dass ein Fehler vorlag.

Größenordnungen:

- **Eichfehlergrenze** Wohnungswasserzähler: ± 2–5 %
- **Verkehrsfehlergrenze** (im Betrieb zulässig): bis ± 10 %
- **Rechtsprechung**: erst ab über **20 %** Differenz zwischen Hauptzähler und Summe der Einzelzähler muss der Vermieter die Mehrkosten selbst tragen; darunter gilt sie als toleranzbedingt und umlagefähig

Bei Warmwasser kommt systematisch hinzu: Zirkulationsverluste, Zapfmengen unterhalb der Anlaufschwelle der Wohnungszähler, nicht erfasste Entnahmestellen (Waschküche, Außenzapfstelle). Eine reale Differenz von 10–20 % ist in Bestandsgebäuden der Normalfall.

## Neues Verhalten

| Differenz | Stufe | Text (Vorschlag) |
| --- | --- | --- |
| < 10 % | nichts | — |
| 10–20 % | **Hinweis**, nicht blockierend | „Die Summe der Wohnungszähler weicht um X % vom zentralen Volumen ab. Das liegt über der Verkehrsfehlergrenze — Anlage und Zählerstände prüfen." |
| > 20 % | **Warnung**, nicht blockierend | „Die Differenz von X % liegt über der Grenze, bis zu der Messdifferenzen nach der Rechtsprechung umlagefähig sind. Mehrkosten oberhalb dieser Grenze trägt in der Regel der Vermieter. Mögliche Ursachen: Leckage, defekter Zähler, nicht erfasste Entnahmestelle." |

Die untere Stufe ist ein **technisches** Signal, die obere ein **rechtliches**. Beide sind nie blockierend — der Vermieter muss die Abrechnung auch mit bekannter Differenz abschließen können.

Flag bleibt `verify-before-production`: die Schwellen sind jetzt begründet, aber die konkreten Warntexte sind noch nicht abgenommen.