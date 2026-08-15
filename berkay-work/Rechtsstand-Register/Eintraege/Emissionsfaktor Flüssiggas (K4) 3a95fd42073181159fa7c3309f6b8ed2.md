# Emissionsfaktor Flüssiggas (K4)

Betrag / Satz: 0,236 kg CO₂/kWh — nur Fallback
Betroffene Seite: 01b · Heizkosten- & CO₂-Verteilung (../../Spec-Seiten/01b%20%C2%B7%20Heizkosten-%20&%20CO%E2%82%82-Verteilung%203a95fd420731814e9e5be043028d4856.md)
Flag: verify-before-production
Letzte Änderung um: 27. Juli 2026 19:01
Prüfen bis: 5. August 2026
Quelle: https://www.gesetze-im-internet.de/ebev_2030/anlage_2.html
Rechtsgrundlage §: keine Anwendungspflicht — Ersatzwert bei fehlender Lieferantenangabe nach § 3 CO2KostAufG. Wert = Anlage 2 Teil 4 Nr. 5b EBeV 2030 (Flüssiggas zu Heizzwecken: 0,0655 t CO₂/GJ × 0,0036 GJ/kWh = 0,2358 kg/kWh, kaufmännisch 0,236).
Rechtsnatur: Konvention
Rechtsstand: 07/2026

## Korrigiert am 27.07.2026: 0,234 → 0,236 kg CO₂/kWh

Der frühere Wert 0,234 stimmte nicht mit der Verordnungsquelle überein.

**Anlage 2 Teil 4 Nr. 5b EBeV 2030** (Flüssiggas zu Heizzwecken) nennt einen heizwertbezogenen Emissionsfaktor von **0,0655 t CO₂/GJ**:

0,0655 t CO₂/GJ × 0,0036 GJ/kWh = 0,2358 kg CO₂/kWh → kaufmännisch **0,236**

Damit haben alle drei Fallback-Faktoren dieselbe Quelle und dieselbe Rundungsregel (3 Nachkommastellen):

| Energieträger | EBeV 2030 Anlage 2 Teil 4 | t CO₂/GJ | exakt kg/kWh | Registerwert |
| --- | --- | --- | --- | --- |
| Erdgas | Nr. 6 | 0,0558 | 0,20088 | 0,201 |
| Heizöl EL | Nr. 3b | 0,0740 | 0,26640 | 0,266 |
| Flüssiggas | Nr. 5b | 0,0655 | 0,23580 | **0,236** |

Erdgas und Heizöl waren bereits korrekt; nur Flüssiggas wich ab (−0,8 %).

*(Berkays Ablage, für die Umsetzung ohne Belang: die lokale Datei `Lokara_Heizkosten-CO2-Engine-Spec_V1.md` Z. 29 ist am 27.07.2026 mitgezogen.)*

Flag bleibt `verify-before-production`: Der Wert ist jetzt belegt, aber die Rechtsnatur bleibt `Konvention`, weil das CO2KostAufG keine Pflicht zur Anwendung der EBeV-Standardwerte als Ersatzwert kennt. Die Entscheidung, diese Quelle zu verwenden, ist unsere.