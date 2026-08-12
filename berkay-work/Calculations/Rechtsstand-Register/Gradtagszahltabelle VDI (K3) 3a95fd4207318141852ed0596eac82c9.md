# Gradtagszahltabelle VDI (K3)

Betrag / Satz: Zehntelpromille je Monat (Σ = 10000): 1700·1500·1300·800·400·133·133·134·300·800·1200·1600. Anzeige in Promille = Wert / 10.
Betroffene Seite: 01b · Heizkosten- & CO₂-Verteilung (../Spec-Seiten/01b%20%C2%B7%20Heizkosten-%20&%20CO%E2%82%82-Verteilung%203a95fd420731814e9e5be043028d4856.md), 01 · Die Abrechnung (../Spec-Seiten/01%20%C2%B7%20Die%20Abrechnung%203a95fd420731816c9048ed7a517c3e9e.md)
Flag: verify-before-production
Letzte Änderung um: 27. Juli 2026 19:01
Prüfen bis: 5. August 2026
Quelle: https://www.gesetze-im-internet.de/heizkostenv/__9b.html
Rechtsgrundlage §: § 9b Abs. 2 HeizkostenV („anerkannte Regeln der Technik"); Tabelle selbst: VDI 2067 Blatt 1, Ausgabe 12/1983, Tabelle 22.
Rechtsnatur: Konvention
Rechtsstand: 07/2026

## Herkunft der Tabelle

VDI 2067 Blatt 1, Ausgabe **12/1983, Tabelle 22**. Grundlage: 20-jährige Temperaturmessung an verschiedenen Orten in Deutschland, Heizgrenze +15 °C, 1000 ‰ auf die Monate verteilt. Die Tabelle ist in der aktuellen VDI-2067-Fassung nicht mehr enthalten, gilt aber weiter als anerkannte Regel der Technik im Sinne von § 9b Abs. 2 HeizkostenV — sie wird von allen Messdienstleistern seit Jahrzehnten angewandt und ist in DIN 94680 übernommen.

Wichtig zur Abgrenzung: Das ist **nicht** dieselbe Größe wie die Gradtage nach **VDI 3807**, die für die Witterungsbereinigung und die DWD-Klimafaktoren (K12) verwendet werden. Zwei verschiedene Zwecke, zwei verschiedene Tabellen.

## Korrigiert am 27.07.2026

| Monat | Zehntel‰ (neu) | ‰ | vorher ‰ | VDI 2067 Tab. 22 |
| --- | --- | --- | --- | --- |
| Januar | 1700 | 170,0 | 170 | 170 |
| Februar | 1500 | 150,0 | 150 | 150 |
| März | 1300 | 130,0 | 130 | 130 |
| April | 800 | 80,0 | 80 | 80 |
| Mai | 400 | 40,0 | 40 | 40 |
| Juni | 133 | 13,3 | 13 | 40/3 ≈ 13,33 |
| Juli | 133 | 13,3 | **7** | 40/3 ≈ 13,33 |
| August | 134 | 13,4 | **10** | 40/3 ≈ 13,33 |
| September | 300 | 30,0 | 30 | 30 |
| Oktober | 800 | 80,0 | 80 | 80 |
| November | 1200 | 120,0 | 120 | 120 |
| Dezember | 1600 | 160,0 | **170** | 160 |
| **Summe** | **10000** | 1000,0 | 1000 | 1000 |

**Warum Zehntelpromille:** Juni, Juli und August tragen zusammen 40 ‰, einzeln also 40/3 = 13,333… ‰ — als ganze Promille nicht darstellbar. In Zehntelpromille sind es 400/3, ganzzahlig aufgeteilt als **133 / 133 / 134**. Die verbleibende Ungenauigkeit liegt bei 0,03 ‰ statt bei 0,33 ‰ wie bei einer Aufteilung 13/13/14 auf Promille-Basis. Integer bleibt Integer — keine Float-Rundungsfehler in der Abrechnung.

**Was vorher falsch war:** Juli (7 statt 13,33), August (10 statt 13,33) und Dezember (170 statt 160). Die Fehler hoben sich gegenseitig auf, die alte Tabelle summierte ebenfalls exakt auf 1000 ‰ — eine Summenprüfung hätte das nie gefunden.

**Wo die Tabelle bei Lokara überhaupt wirkt:** nur im Block `verbrauchHz` und nur bei **fehlender Zwischenablesung** (§ 9b Abs. 3, E12 / `01b-F16`). Die Grundkosten laufen bei uns nach **m²-Tagen** (K2), nicht nach Gradtagszahlen — § 9b Abs. 2 lässt beides zu, wir haben zeitanteilig gewählt. Warmwasser ebenfalls zeitanteilig. Der Fehler war also enger begrenzt, als es zunächst aussieht.

**Gemessene Wirkung im Referenzhaus** (`01b-F16`, Nutzerwechsel Schneider → Weber, Leerstand August):

| Mieter | alte Tabelle | korrigiert | Δ |
| --- | --- | --- | --- |
| Schneider | 688,23 € | 691,65 € | +3,42 € |
| Weber | 399,50 € | 394,33 € | −5,17 € |
| Eigentümer | 38,02 € | 39,77 € | +1,75 € |

Rund 0,5 % des jeweiligen Mieteranteils — klein genug, um in keiner Plausibilitätsprüfung aufzufallen, groß genug, damit ein Mieter es beim Nachrechnen findet.

**Für die Umsetzung:** Die Spalte heißt `gradtagszahlen(monat, zehntelpromille)`, Typ Integer, Σ = 10000. Wer Promille anzeigen will, teilt durch 10. Als ‰-Integer ist die Tabelle **nicht** darstellbar — Jun/Jul/Aug sind 400/3. Steht so auch in Abschnitt 3.4 der Seite 01b.

*(Berkays Ablage, für die Umsetzung ohne Belang: die lokalen Dateien `Lokara_Heizkosten-CO2-Engine-Spec_V1.md` Z. 92 und `Lokara_Datenmodell-Spec_V1.md` Z. 106 sind am 27.07.2026 mitgezogen.)*

Flag bleibt `verify-before-production` gemäß der Roadmap-Regel, dass jede Rechtsnatur `Konvention` dieses Flag trägt.