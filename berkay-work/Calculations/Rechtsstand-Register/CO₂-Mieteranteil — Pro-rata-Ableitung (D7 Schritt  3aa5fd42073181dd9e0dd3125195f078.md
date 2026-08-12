# CO₂-Mieteranteil — Pro-rata-Ableitung (D7 Schritt 6)

Betrag / Satz: Der auf den einzelnen Mieter entfallende CO₂-Kostenanteil wird pro rata zu seinem Heizkostenanteil abgeleitet: co2AnteilMieter = round(co2MieterGesamt × heizAnteilMieter / Σ heizAnteilMieter). Zeilenweise round_half_up; der Verteilungsrest landet beim Eigentümer und wird NIE still verteilt. Dass die vier Werte im Referenzobjekt exakt auf co2MieterGesamt aufgehen, ist Zufall, keine Invariante — Drift von ± 1–2 ct ist zulässig.
Betroffene Seite: 01 · Die Abrechnung (../Spec-Seiten/01%20%C2%B7%20Die%20Abrechnung%203a95fd420731816c9048ed7a517c3e9e.md), 01b · Heizkosten- & CO₂-Verteilung (../Spec-Seiten/01b%20%C2%B7%20Heizkosten-%20&%20CO%E2%82%82-Verteilung%203a95fd420731814e9e5be043028d4856.md)
Flag: verify-before-production
Letzte Änderung um: 27. Juli 2026 20:14
Prüfen bis: 5. August 2026
Quelle: https://www.gesetze-im-internet.de/co2kostaufg/__7.html
Rechtsgrundlage §: § 7 Abs. 1 S. 2 CO2KostAufG verlangt die Verteilung „gemäß der Vereinbarung über die Verteilung der Heiz- und Warmwasserkosten auf Grundlage der §§ 6 bis 10 HeizkostenV" — die konkrete Pro-rata-Formel steht dort nicht und ist unsere Konvention. Der AUSWEIS des Anteils ist dagegen Pflicht (§ 7 Abs. 3), das Kürzungsrecht bei Verstoß folgt aus § 7 Abs. 4.
Rechtsnatur: Konvention
Rechtsstand: 07/2026