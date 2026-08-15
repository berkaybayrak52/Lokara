# Grundkosten-Verteilung nach m²-Tagen (K2)

Betrag / Satz: Grundkosten Heizung und Warmwasser werden zeitanteilig nach m²-Tagen verteilt, nicht nach Gradtagszahlen. Nenner nM2Tage einschließlich Leerstand.
Betroffene Seite: 01b · Heizkosten- & CO₂-Verteilung (../../Spec-Seiten/01b%20%C2%B7%20Heizkosten-%20&%20CO%E2%82%82-Verteilung%203a95fd420731814e9e5be043028d4856.md), 01 · Die Abrechnung (../../Spec-Seiten/01%20%C2%B7%20Die%20Abrechnung%203a95fd420731816c9048ed7a517c3e9e.md)
Flag: verify-before-production
Letzte Änderung um: 27. Juli 2026 19:16
Prüfen bis: 5. August 2026
Quelle: https://www.gesetze-im-internet.de/heizkostenv/__9b.html
Rechtsgrundlage §: Maßstab: § 7 Abs. 1 S. 5 HeizkostenV (übrige Kosten Wärme nach Wohn-/Nutzfläche oder umbautem Raum) und § 8 Abs. 1 HeizkostenV (übrige Kosten Warmwasser nach Wohn-/Nutzfläche). Zeitanteil: § 9b Abs. 2 HeizkostenV lässt für die übrigen Wärmekosten bei Nutzerwechsel Gradtagszahlen ODER zeitanteilig zu, für Warmwasser nur zeitanteilig — wir nehmen durchgängig zeitanteilig, weil die NK-Engine (Seite 01) denselben Nenner benutzt. § 9b Abs. 2 allein trägt den Flächenmaßstab NICHT; er regelt nur die Aufteilung zwischen Vor- und Nachnutzer.
Rechtsnatur: Konvention
Rechtsstand: 07/2026

Angelegt am 27.07.2026 bei der Querprüfung Seite 01b gegen das Register — die Konvention stand auf 01b als **K2**, hatte aber keinen Registereintrag.

**Warum das zählt:** § 9b Abs. 2 eröffnet ein Wahlrecht. Wer die Engine liest und annimmt, die Gradtagszahltabelle (K3) gälte auch für die Grundkosten, liegt falsch — K3 wirkt ausschließlich auf `verbrauchHz` bei fehlender Zwischenablesung. Die Grundkosten laufen immer über m²-Tage, auch beim Nutzerwechsel.

**Wechselwirkung:** ändert man diese Konvention auf Gradtagszahlen, verschiebt sich bei jedem unterjährigen Nutzerwechsel Geld zwischen Vor- und Nachmieter, und der Nenner weicht von dem der NK-Engine ab. Dann wären zwei verschiedene Zeitanteils-Logiken im selben Produkt.