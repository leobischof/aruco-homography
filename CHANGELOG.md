# Changelog

Bemerkenswerte Änderungen an diesem Projekt. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach
[SemVer](https://semver.org/lang/de/).

## [0.2.0] – 2026-09-06

### Hinzugefügt

- **Markenzeichen auf jedem Blatt.** Logo und „Made with Bischof Snowboards Software"
  stehen im Streifen unter dem Bild — auf der Einzelseite, auf *jeder* Kachel, auf dem
  Klebeplan und auf dem Markerblatt. Das Logo wird als Vektor aus der Original-SVG des
  Webprojekts eingebettet, nicht als Rasterbild, und ist damit bei jeder Druckgröße
  scharf.
- **Markenblock im PDF verlinkt** auf bischof-snowboards.com; in der Oberfläche führen
  Logo, Markenzeile und Fußzeile auf dieselbe Adresse.
- **Markenfarben und Montserrat** in der Oberfläche. Die Farbtokens stammen aus
  `snow-service-free/src/main.css`, dort in oklch notiert, hier als sRGB in
  `app/config.py`. Gegenprobe: `--foreground oklch(0.3717 0.0392 257.29)` ergibt
  `#334155`, exakt die Tinte, die `logo-dark.svg` im Dateikommentar nennt.
- **Originales Favicon** aus dem Webprojekt statt einer Nachbildung.
- `tests/test_branding.py`: prüft über die PDF-Textextraktion, dass **keine** Seite ohne
  Herkunftszeile herauskommt, und über die Link-Annotationen, dass der Markenblock
  verlinkt ist.
- `test_markersheet.py` rastert das erzeugte Markerblatt und schickt es durch den echten
  Detektor. Ein vertauschtes oder gespiegeltes Modulraster sähe auf dem Bildschirm normal
  aus und fiele sonst erst am realen Foto auf. Gemessen: Kante 66,98 mm, Abstände
  121,00 × 170,99 mm.

### Geändert

- **Das Raster ist kräftiger und auf hellem wie dunklem Untergrund lesbar.** Jede Linie
  wird zweimal gezogen: erst ein breiter weißer Saum, dann die Kernlinie in Markentinte.
  Auf Weiß verschwindet der Saum, auf Schwarz trägt er die Linie. Die Beschriftungen
  sitzen auf weißem Träger und werden in den Bildbereich hineingeklemmt.
- **Der Streifen unter dem Bild ist jetzt immer da**, auch wenn Maßstab und Fußzeile
  abgeschaltet sind — er trägt das Markenzeichen. Damit ist eine Seite nie mehr exakt so
  groß wie das Objekt; das **Bild** belegt aber unverändert exakt `crop_w × crop_h`
  Millimeter, und nur das war je die Zusage.

## [0.1.0] – 2026-09-06

Erste Fassung: Handyfoto rein, maßhaltiges PDF in Originalgröße raus.

### Hinzugefügt

- **Homographie in zwei Modi.** Blatt-Modus mit bekanntem Layout; Frei-Modus, der
  Homographie und Markerpositionen gemeinsam schätzt (8 + 2(n−1) Unbekannte gegen 8n
  Gleichungen). Vorgabe ist das real vermessene Blatt: 67 mm Marker, Mittelpunktabstände
  121 × 171 mm.
- **Dickenkorrektur.** Eine Fläche `h` über der Markerebene erscheint radial vom
  Kamera-Lotpunkt weg gestreckt um `d/(d−h)`; Höhe und Lotpunkt fallen aus der Zerlegung
  der Homographie, sobald die EXIF-Brennweite bekannt ist. Ohne EXIF wird der
  Kameraabstand zur Pflichteingabe.
- **Qualitätsbericht** statt blindem Vertrauen: Restfehler in px und mm, jeder Marker
  gegen seine Sollgröße zurückgemessen, Kamerahöhe und -neigung, und der Anteil des
  Zuschnitts außerhalb der Marker-Hülle.
- **PDF-Export** als Einzelseite in Objektgröße oder gekachelt auf A4/A3 mit Überlappung,
  Schnitt- und Klebemarken und vorangestelltem Klebeplan. Aufdrucke: 100-mm-Kontroll­maßstab,
  Metadaten-Fußzeile, 50-mm-Raster, optional der erkannte Umriss als Vektor-Schnittlinie.
- **Markerblatt-Generator**, Marker Modul für Modul als Vektorrechtecke gezeichnet, mit
  eigenem Kontrollmaßstab und dem Hinweis, nach dem Druck nachzumessen.
- **Weboberfläche** mit Foto-Upload (auch HEIC), Crop-Rechteck mit Live-Millimeteranzeige
  und Druckoptionen; der Server nennt beim Start die LAN-Adresse samt QR-Code fürs Handy.
- **Testsuite gegen synthetische Grundwahrheit.** Virtuelle Kamera, bekannte Pose,
  bekanntes Objekt; die Dickenkorrektur wird beidseitig geprüft. Der Renderer filtert vor
  dem Warp tief — ohne das verschiebt Aliasing die Markerecken um bis zu 0,58 px und der
  Test misst den Testaufbau statt den Detektor.
- **Selbstheilendes `dev.ps1`** mit Stempel über den SHA-256 von `requirements.txt`, plus
  passende VS-Code-Tasks.

### Bekannte Grenzen

- Objektivverzeichnung bleibt unkorrigiert; mit vier koplanaren Markern nicht abtrennbar.
  Gegenmittel beim Fotografieren: Tele, großer Abstand, Objekt mittig.
- Gewölbte Objekte gehen nicht — eine Homographie beschreibt genau eine Ebene.
- Die Maßhaltigkeit ist bisher **nur gegen synthetische Szenen** belegt. Der Beweis am
  echten Ausdruck (drucken, 100-mm-Maßstab mit dem Messschieber nachmessen) steht aus.
