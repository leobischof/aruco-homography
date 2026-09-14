---
title: Datenschutzerklärung
description: Die Datenschutzerklärung der Android-App, zweisprachig — sie erhebt nichts, und das Betriebssystem erzwingt es.
audience: operator
status: draft
updated: 2026-09-14
---

# Datenschutzerklärung · Privacy Policy

**ArUco Homography** (`com.bischofsnowboards.aruco`)

Stand / Last updated: 14.09.2026

---

## Deutsch

### Kurz

**Diese App erhebt keine Daten. Sie kann es nicht.**

Die App hat **keine Berechtigung, auf das Netz zuzugreifen**
(`android.permission.INTERNET` ist nicht angefordert). Ohne diese Berechtigung kann eine
Android-App nichts senden — das verhindert das Betriebssystem, nicht eine Zusage des
Herstellers. Ihre Fotos, Ihre Maße und die erzeugten PDFs verlassen Ihr Gerät nicht.

### Was die App verarbeitet

| Was | Wo | Wie lange |
|---|---|---|
| Das Foto, das Sie aufnehmen oder auswählen | nur auf Ihrem Gerät | bis Sie die App schließen |
| Die Maße, die Sie eintragen | nur auf Ihrem Gerät | bis Sie die App schließen |
| Das erzeugte PDF | dorthin, wohin **Sie** es speichern oder teilen | von Ihnen bestimmt |

Es gibt **keine** Benutzerkonten, **keine** Werbung, **keine** Analyse- oder
Absturzberichte, **keine** Google-Play-Dienste, **keine** Tracker und **keine** Cookies.

### Berechtigungen und wofür

- **Kamera** (`android.permission.CAMERA`) — für den Sucher, der die Marker schon im
  laufenden Bild findet, und für das Aufnehmen des Fotos. Das Bild wird im Gerät
  verarbeitet. Sie können die Berechtigung verweigern und stattdessen ein vorhandenes
  Foto auswählen; die Berechnung funktioniert genauso.

Die App fordert **keine** Berechtigung für Netz, Standort, Kontakte, Mikrofon oder den
allgemeinen Speicher an. Gelesen wird über die Systemauswahl
(`ACTION_OPEN_DOCUMENT`), geschrieben über den Systemdialog (`ACTION_CREATE_DOCUMENT`) —
beide geben der App nur die eine Datei, die Sie ausgewählt haben.

### Kinder

Die App richtet sich nicht an Kinder und erhebt von niemandem Daten, also auch von Kindern
keine.

### Ihre Rechte

Da keine personenbezogenen Daten erhoben, gespeichert oder übermittelt werden, entstehen
keine Auskunfts-, Berichtigungs- oder Löschansprüche gegenüber dem Anbieter. Alle Daten
liegen ausschließlich auf Ihrem Gerät und werden mit dem Deinstallieren der App entfernt.

### Verantwortlich

Leo Bischof · leo@bischof-snowboards.com
Quelltext: https://github.com/leobischof/aruco-homography

---

## English

### Short

**This app collects no data. It cannot.**

The app holds **no permission to access the network** (`android.permission.INTERNET` is
not requested). Without it, an Android app cannot send anything — that is enforced by the
operating system, not promised by the developer. Your photos, your measurements and the
PDFs you generate never leave your device.

### What the app processes

| What | Where | How long |
|---|---|---|
| The photo you take or pick | on your device only | until you close the app |
| The measurements you enter | on your device only | until you close the app |
| The generated PDF | wherever **you** save or share it | your choice |

There are **no** user accounts, **no** advertising, **no** analytics or crash reporting,
**no** Google Play Services, **no** trackers and **no** cookies.

### Permissions, and what for

- **Camera** (`android.permission.CAMERA`) — for the viewfinder that locates the markers
  in the live image, and for taking the photo. The image is processed on the device. You
  may deny the permission and pick an existing photo instead; the computation works the
  same way.

The app requests **no** permission for network, location, contacts, microphone or general
storage. Files are read through the system picker (`ACTION_OPEN_DOCUMENT`) and written
through the system dialog (`ACTION_CREATE_DOCUMENT`) — both hand the app only the single
file you chose.

### Children

The app is not directed at children, and collects no data from anyone, children included.

### Your rights

Because no personal data is collected, stored or transmitted, there is nothing for the
provider to disclose, correct or delete. All data stays on your device and is removed when
you uninstall the app.

### Contact

Leo Bischof · leo@bischof-snowboards.com
Source code: https://github.com/leobischof/aruco-homography

---

> **Für Entwickler:** Google Play verlangt diese Erklärung unter einer **öffentlichen,
> direkt erreichbaren Adresse**. Diese Datei auf GitHub genügt dafür:
> `https://github.com/leobischof/aruco-homography/blob/master/docs/publishing/privacy-policy.md`
>
> Jede Änderung an den Berechtigungen im `AndroidManifest.xml` macht diesen Text
> **falsch**, bis er nachgezogen ist. Das ist der einzige Grund, warum er im Repo liegt
> und nicht auf einer Webseite: hier liegt er neben dem Manifest, das er beschreibt.
