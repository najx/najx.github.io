---
title: "L'odyssée d'une requête : Lorsque vous tapez une URL"
date: 2026-09-03 10:00:00 +02:00
modified: 2026-09-03 10:00:00 +02:00
tags: [Architecture 🏛️]
description: >-
  Entre le moment où votre doigt enfonce la touche Entrée et celui où la page s'affiche,
  il s'écoule environ trois cents millisecondes — et à peu près toute l'informatique moderne.
  Un voyage chronologique à travers la pile complète, du clavier au pixel :
  matériel, système d'exploitation, DNS, TCP, TLS, HTTP, routage, serveurs et moteur de rendu.
lang: fr
comments: false
ai_assisted: true
---

<style>
.odyssee-fig{--bg:#fff;--muted:#6b7886;--accent:#ff0000;--accent-soft:rgba(255,0,0,.06);border:1px solid #ececec;border-radius:4px;padding:18px 18px 10px;margin:2em 0;overflow-x:auto}
.odyssee-fig svg{display:block;width:100%;height:auto;min-width:600px}
.odyssee-fig figcaption{margin-top:12px;text-align:left;font-style:italic;line-height:1.6}
body[data-theme="dark"] .odyssee-fig{--bg:#131418;--muted:#767f87;--accent-soft:rgba(255,0,0,.12);border-color:#2a2c35}
</style>

Ce geste, vous le faites cent fois par jour. Une adresse, la touche **Entrée**, une page. Rien de plus banal — et pourtant, sous ce clic se cache l'une des plus belles cathédrales que l'ingénierie ait jamais construites : des dizaines de machines, des milliers de kilomètres de fibre optique, une cinquantaine d'années de protocoles empilés les uns sur les autres, et du silicium cadencé à plusieurs milliards de battements par seconde.

Cet article raconte ce voyage **dans l'ordre chronologique**, de la pression physique sur la touche jusqu'aux pixels allumés à l'écran. À chaque étape, on descendra ou remontera dans la pile : tantôt dans le matériel (clavier, processeur, mémoire, carte réseau), tantôt dans le logiciel (système d'exploitation, navigateur), tantôt dans ce qui les relie — DNS, TCP, TLS, HTTP, serveurs web. Les durées indiquées en tête de chapitre sont des ordres de grandeur réalistes pour une connexion fibre en France vers un site correctement hébergé ; elles servent de fil conducteur, pas de chronomètre.

<figure class="odyssee-fig">
<svg viewBox="0 0 960 262" role="img" aria-label="Vue d'ensemble du trajet : votre machine, la box, le réseau du fournisseur d'accès, Internet, puis le serveur ; la requête part dans un sens, la réponse revient dans l'autre.">
<defs>
<marker id="o-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker>
<marker id="o-arrA" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<g font-family="monospace">
<g stroke="currentColor" stroke-opacity="0.45" fill="var(--bg)">
<rect x="20" y="52" width="152" height="64" rx="9"/>
<rect x="216" y="52" width="126" height="64" rx="9"/>
<rect x="386" y="52" width="136" height="64" rx="9"/>
<rect x="566" y="52" width="150" height="64" rx="9"/>
<rect x="760" y="52" width="180" height="64" rx="9"/>
</g>
<g fill="currentColor" font-size="12.5" font-weight="600" text-anchor="middle">
<text x="96" y="78">Votre machine</text>
<text x="279" y="78">Box · routeur</text>
<text x="454" y="78">Réseau du FAI</text>
<text x="641" y="78">Internet</text>
<text x="850" y="78">CDN · Serveur</text>
</g>
<g fill="var(--muted)" font-size="10" text-anchor="middle">
<text x="96" y="98">navigateur · OS · NIC</text>
<text x="279" y="98">Wi-Fi · NAT</text>
<text x="454" y="98">OLT · collecte fibre</text>
<text x="641" y="98">AS · BGP · câbles</text>
<text x="850" y="98">edge · proxy · app</text>
</g>
<g stroke="currentColor" stroke-opacity="0.5" marker-end="url(#o-arr)">
<line x1="172" y1="84" x2="209" y2="84"/>
<line x1="342" y1="84" x2="379" y2="84"/>
<line x1="522" y1="84" x2="559" y2="84"/>
<line x1="716" y1="84" x2="753" y2="84"/>
</g>
<line x1="60" y1="172" x2="896" y2="172" stroke="var(--accent)" stroke-width="1.6" marker-end="url(#o-arrA)"/>
<circle cx="60" cy="172" r="4" fill="var(--accent)"/>
<text x="60" y="156" fill="var(--accent)" font-size="10.5" font-weight="600">aller — la requête HTTP (quelques centaines d'octets)</text>
<line x1="896" y1="216" x2="64" y2="216" stroke="var(--accent)" stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#o-arrA)"/>
<circle cx="896" cy="216" r="4" fill="var(--accent)"/>
<text x="896" y="244" fill="var(--accent)" font-size="10.5" font-weight="600" text-anchor="end">retour — la réponse : HTML, CSS, scripts, images (des dizaines de kilo-octets)</text>
</g>
</svg>
<figcaption>Le trajet en une image. Chaque tronçon correspond à un ou plusieurs chapitres : la machine (00 à 02), la résolution DNS et les poignées de main (03 à 05), le voyage des paquets (06 et 07), le serveur (08), puis le retour et le rendu (09).</figcaption>
</figure>

Le voyage se lit en onze étapes : [le prologue](#ch0) (la machine était déjà prête), [la frappe](#ch1), [l'analyse de l'URL](#ch2), [le DNS](#ch3), [TCP](#ch4), [TLS](#ch5), [HTTP](#ch6), [le voyage des paquets](#ch7), [le serveur](#ch8), [le rendu](#ch9) et [l'épilogue](#outro).

---

## 00 — Prologue : la machine était prête
{: #ch0}

*t − quelques minutes · matériel, firmware, système*

Avant même que l'histoire commence, un travail colossal a déjà eu lieu : celui de l'allumage. Quand vous avez pressé le bouton d'alimentation, le processeur s'est réveillé dans un état minimal et est allé exécuter le **firmware** de la carte mère — le **BIOS** historique, remplacé depuis quinze ans par son successeur **UEFI**, mais tout le monde continue de dire « BIOS ». Ce petit programme gravé dans une mémoire flash a une mission : transformer un tas de composants inertes en une machine capable de charger un système d'exploitation.

Il commence par le **POST** (*Power-On Self-Test*) : recenser et tester le matériel. L'étape la plus délicate est l'initialisation de la RAM — le fameux *memory training*, où le contrôleur mémoire calibre les tensions et les délais de chaque barrette à la nanoseconde près. Puis l'UEFI énumère les périphériques (SSD NVMe, carte réseau, GPU), applique éventuellement *Secure Boot* pour vérifier les signatures cryptographiques de ce qu'il s'apprête à lancer, trouve le **chargeur d'amorçage** (Windows Boot Manager, GRUB, systemd-boot…) sur la partition EFI, et lui passe la main.

Le chargeur charge le **noyau** du système d'exploitation en mémoire. Le noyau prend alors le contrôle total : il active la **mémoire virtuelle** (chaque processus croira disposer de la machine entière), configure le contrôleur d'interruptions, monte les systèmes de fichiers, charge les pilotes — dont celui de la carte réseau — puis démarre l'espace utilisateur : services, session graphique, et, quelque part dans tout ça, votre navigateur.

Un navigateur moderne n'est d'ailleurs pas *un* programme mais une petite constellation : un **processus principal** qui orchestre, un **processus réseau**, un **processus GPU**, et un **processus de rendu** par site, enfermé dans un bac à sable. Nous les recroiserons. Au moment où notre histoire commence, tout ce monde tourne déjà, paisiblement, en attendant un événement. Le voici.

---

## 01 — La frappe : une touche, une interruption
{: #ch1}

*t = 0 · matériel, système*

Votre doigt enfonce la touche Entrée. Sous le capuchon, deux contacts se touchent et ferment un circuit. Le clavier n'est pas passif : il embarque son propre microcontrôleur, qui scanne la **matrice** de touches plusieurs centaines de fois par seconde, élimine les rebonds électriques du contact (*debouncing* — sans quoi une pression produirait dix caractères), et encode l'événement au format **HID**, le standard des périphériques d'entrée. Pour Entrée, c'est le code `0x28`.

Sur un clavier USB, ce rapport est déposé dans une file que le contrôleur hôte de la machine vient relever jusqu'à mille fois par seconde. À la réception, le contrôleur lève une **interruption** : un signal électrique qui force le processeur à suspendre ce qu'il faisait, sauvegarder son état, et sauter dans une routine du noyau. C'est le mécanisme fondamental par lequel le matériel se fait entendre du logiciel — nous le reverrons à l'identique avec la carte réseau.

Le pilote clavier du noyau traduit le code HID en code de touche générique, l'estampille et le publie comme événement d'entrée. Le serveur d'affichage (WindowServer sous macOS, Wayland ou X11 sous Linux, DWM sous Windows) détermine quelle fenêtre a le focus — le navigateur — et lui transmet l'événement. Là, il atterrit dans la **boucle d'événements** du processus principal, qui le dispatche au champ actif : la barre d'adresse. Touche `Enter`, champ validé. L'odyssée commence.

<figure class="odyssee-fig">
<svg viewBox="0 0 940 150" role="img" aria-label="Chaîne de la frappe : le clavier envoie un code via USB, le contrôleur lève une interruption vers le noyau, qui publie un événement transmis par le serveur d'affichage au navigateur.">
<defs><marker id="o-arr2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>
<g font-family="monospace">
<g stroke="currentColor" stroke-opacity="0.45" fill="var(--bg)">
<rect x="14" y="44" width="120" height="56" rx="9"/>
<rect x="200" y="44" width="140" height="56" rx="9"/>
<rect x="406" y="44" width="130" height="56" rx="9"/>
<rect x="602" y="44" width="140" height="56" rx="9"/>
<rect x="806" y="44" width="120" height="56" rx="9"/>
</g>
<g fill="currentColor" font-size="12" font-weight="600" text-anchor="middle">
<text x="74" y="68">Clavier</text>
<text x="270" y="68">Contrôleur USB</text>
<text x="471" y="68">Noyau</text>
<text x="672" y="68">Serveur</text>
<text x="672" y="82">d'affichage</text>
<text x="866" y="68">Navigateur</text>
</g>
<g fill="var(--muted)" font-size="10" text-anchor="middle">
<text x="74" y="86">matrice · HID</text>
<text x="270" y="86">hôte xHCI</text>
<text x="471" y="86">pilote · évén.</text>
<text x="866" y="86">boucle d'évén.</text>
</g>
<g stroke="currentColor" stroke-opacity="0.5" marker-end="url(#o-arr2)">
<line x1="134" y1="72" x2="193" y2="72"/>
<line x1="340" y1="72" x2="399" y2="72"/>
<line x1="536" y1="72" x2="595" y2="72"/>
<line x1="742" y1="72" x2="799" y2="72"/>
</g>
<g font-size="10" text-anchor="middle">
<text x="164" y="60" fill="var(--accent)" font-weight="600">0x28</text>
<text x="370" y="60" fill="var(--accent)" font-weight="600">IRQ</text>
<text x="565" y="60" fill="var(--muted)">keycode</text>
<text x="770" y="60" fill="var(--muted)">event</text>
</g>
<text x="470" y="132" fill="var(--muted)" font-size="10.5" text-anchor="middle">durée totale : quelques centaines de microsecondes</text>
</g>
</svg>
<figcaption>Du contact électrique à l'événement logiciel. Le code HID <code>0x28</code> (Entrée) remonte du clavier au navigateur en traversant une interruption matérielle (IRQ), le pilote du noyau et le serveur d'affichage.</figcaption>
</figure>

> **Sous la loupe — ce que « exécuter » veut dire : CPU, caches, RAM**
>
> Chaque étape logicielle de cet article se ramène à la même mécanique : le processeur lit des instructions en mémoire, les décode et les exécute, à plusieurs milliards de cycles par seconde, sur une douzaine de cœurs, avec un pipeline qui traite plusieurs instructions en parallèle et un prédicteur de branchement qui parie sur la suite du programme.
>
> Son goulot d'étranglement, c'est la mémoire. D'où une hiérarchie : des caches **L1/L2** minuscules et ultra-rapides collés à chaque cœur, un **L3** partagé, puis la **RAM**. Et la RAM elle-même est virtualisée : chaque adresse manipulée par un programme est traduite par la **MMU** via des tables de pages (accélérées par un cache dédié, le TLB). Si la page n'est pas en RAM, le noyau la charge depuis le disque — c'est un défaut de page.

Les ordres de grandeur ci-dessous expliquent toute l'architecture du reste de l'article : *le réseau est un million de fois plus lent que la RAM*, donc tout le monde cache tout, à tous les étages.

| Opération | Durée typique | À l'échelle humaine* |
|---|---|---|
| Cycle CPU (≈ 4 GHz) | 0,25 ns | 1 seconde |
| Accès cache L1 | ≈ 1 ns | 4 secondes |
| Accès RAM | ≈ 100 ns | 7 minutes |
| Lecture SSD NVMe | ≈ 100 µs | 4,6 jours |
| Aller-retour réseau (Paris–Francfort) | ≈ 10 ms | 15 mois |
| Aller-retour transatlantique | ≈ 75 ms | 9 ans et demi |

<small>* si un cycle CPU durait une seconde.</small>

---

## 02 — Le navigateur décortique l'URL
{: #ch2}

*t + 1 ms · navigateur*

Première question que se pose le navigateur : *qu'est-ce que vous venez de taper ?* La barre d'adresse est une « omnibox » : si le texte ne ressemble pas à une adresse, il part vers un moteur de recherche. Ici, `www.example.com` a la tête d'un nom de domaine ; le navigateur le canonise en une URL complète et la découpe : le **schéma** (`https`), l'**hôte** (`www.example.com`), le **port** implicite (443 pour HTTPS), le **chemin** (`/`).

Petit détail savoureux : il a probablement commencé *avant* que vous finissiez de taper. À chaque caractère, l'omnibox interroge l'historique et les suggestions, et si elle est suffisamment confiante sur votre destination, elle lance une **préconnexion spéculative** — résolution DNS, voire connexion TCP — en douce. Une partie du travail des chapitres suivants est parfois déjà faite au moment où vous appuyez sur Entrée.

Suivent quelques vérifications éclair. La liste **HSTS** d'abord : si le domaine y figure (elle est préchargée dans le navigateur), toute tentative en `http://` sera convertie en `https://` avant même de toucher le réseau. Les **caches** ensuite : une copie fraîche de la page existe-t-elle dans le cache mémoire de l'onglet, ou dans le cache disque ? Un service worker est-il enregistré pour ce site ? Si une réponse valide est trouvée, le voyage s'arrête presque ici. Supposons que non : il faut aller chercher la page. Le processus principal confie l'affaire au **processus réseau**, qui rassemble les cookies du domaine et les en-têtes à envoyer.

Dernier point d'architecture, invisible mais crucial : le futur contenu de la page sera confié à un **processus de rendu** isolé, sans droit d'accès direct à vos fichiers ni au réseau — le *sandbox*. Depuis les failles Spectre, chaque site a même droit à son propre processus (*site isolation*). Si une page malveillante compromet son moteur de rendu, elle reste enfermée dans une pièce vide.

---

## 03 — DNS : l'annuaire planétaire
{: #ch3}

*t + 2 ms · réseau, système, protocole*

Le réseau ne connaît pas les noms, seulement les adresses IP. Avant toute connexion, il faut donc traduire `www.example.com` en quelque chose comme `203.0.113.7`. C'est le rôle du **DNS** (*Domain Name System*), une base de données distribuée sur toute la planète, hiérarchique, et sans doute l'infrastructure la plus sollicitée du monde — des milliers de milliards de requêtes par jour.

La quête suit une chaîne de caches. Le navigateur a le sien. Le système d'exploitation aussi, plus le vénérable fichier `hosts`. Si personne n'a la réponse, la machine — via son *stub resolver*, le client DNS minimal intégré à l'OS — envoie la question à un **résolveur récursif** : celui de votre box ou de votre FAI par défaut, ou un résolveur public comme `1.1.1.1` (Cloudflare), `8.8.8.8` (Google) ou `9.9.9.9` (Quad9). Historiquement, la question part en clair en UDP sur le port 53 ; de plus en plus souvent, elle est chiffrée (**DoH**, DNS sur HTTPS, ou **DoT**, DNS sur TLS).

Si le récursif n'a pas la réponse en cache, il remonte la hiérarchie depuis le sommet. Les **serveurs racine** — 13 adresses logiques, démultipliées en plus d'un millier d'instances physiques par la magie de l'*anycast* (une même IP annoncée depuis des dizaines d'endroits ; le routage vous amène à la plus proche) — ne connaissent pas `example.com`, mais savent qui gère `.com`. Les serveurs du **TLD** `.com` savent quels serveurs font autorité pour `example.com`. Et le serveur **autoritatif**, enfin, détient la réponse.

<figure class="odyssee-fig">
<svg viewBox="0 0 920 330" role="img" aria-label="Résolution DNS : la machine interroge un résolveur récursif, qui questionne successivement un serveur racine, le serveur du TLD .com et le serveur autoritatif, puis renvoie l'adresse IP.">
<defs>
<marker id="o-arr3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker>
<marker id="o-arr3A" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<g font-family="monospace">
<g stroke="currentColor" stroke-opacity="0.45" fill="var(--bg)">
<rect x="20" y="118" width="168" height="66" rx="9"/>
<rect x="330" y="118" width="188" height="66" rx="9"/>
<rect x="700" y="28" width="200" height="52" rx="9"/>
<rect x="700" y="126" width="200" height="52" rx="9"/>
<rect x="700" y="224" width="200" height="52" rx="9"/>
</g>
<g fill="currentColor" font-size="12" font-weight="600" text-anchor="middle">
<text x="104" y="143">Votre machine</text>
<text x="424" y="143">Résolveur récursif</text>
<text x="800" y="50">Serveur racine</text>
<text x="800" y="148">Serveur TLD « .com »</text>
<text x="800" y="246">Serveur autoritatif</text>
</g>
<g fill="var(--muted)" font-size="10" text-anchor="middle">
<text x="104" y="161">stub resolver</text>
<text x="104" y="174">caches locaux</text>
<text x="424" y="161">FAI · 1.1.1.1 · 8.8.8.8</text>
<text x="424" y="174">+ son propre cache</text>
<text x="800" y="66">13 identités · &gt;1000 instances</text>
<text x="800" y="164">délégué par la racine</text>
<text x="800" y="262">détient la zone example.com</text>
</g>
<g font-size="10">
<line x1="188" y1="138" x2="323" y2="138" stroke="currentColor" stroke-opacity="0.55" marker-end="url(#o-arr3)"/>
<text x="255" y="128" fill="var(--muted)" text-anchor="middle">1 · www.example.com ?</text>
<g stroke="currentColor" stroke-opacity="0.55" marker-end="url(#o-arr3)">
<line x1="518" y1="132" x2="693" y2="62"/>
<line x1="518" y1="148" x2="693" y2="150"/>
<line x1="518" y1="166" x2="693" y2="242"/>
</g>
<text x="596" y="84" fill="var(--muted)" text-anchor="middle">2 · qui gère .com ?</text>
<text x="596" y="142" fill="var(--muted)" text-anchor="middle">3 · qui gère example.com ?</text>
<text x="596" y="222" fill="var(--muted)" text-anchor="middle">4 · adresse de www ?</text>
<line x1="330" y1="180" x2="188" y2="180" stroke="var(--accent)" stroke-width="1.5" marker-end="url(#o-arr3A)"/>
<text x="258" y="196" fill="var(--accent)" font-weight="600" text-anchor="middle">5 · 203.0.113.7 (TTL 300 s)</text>
</g>
<text x="460" y="312" fill="var(--muted)" font-size="10.5" text-anchor="middle">chaque réponse est mise en cache : la plupart du temps, les étapes 2–4 sont évitées</text>
</g>
</svg>
<figcaption>La résolution récursive. Le résolveur descend la hiérarchie — racine, TLD, autoritatif — puis renvoie l'adresse avec un TTL : la durée pendant laquelle chaque cache de la chaîne a le droit de resservir la réponse sans reposer la question.</figcaption>
</figure>

La réponse est un **enregistrement** parmi la petite grammaire du DNS :

| Type | Contenu | Exemple d'usage |
|---|---|---|
| `A` / `AAAA` | Adresse IPv4 / IPv6 | `www → 203.0.113.7` |
| `CNAME` | Alias vers un autre nom | `www → site.cdn-fournisseur.net` |
| `NS` | Serveurs de noms de la zone | la délégation elle-même |
| `MX` | Serveurs de courrier | où livrer les e-mails du domaine |
| `TXT` | Texte libre | anti-spam (SPF, DKIM), preuves de propriété |
| `HTTPS` | Indications de service | « ce site parle HTTP/3 » — gain d'un aller-retour |

> **Sous la loupe — le DNS comme levier d'architecture**
>
> Parce qu'il est le premier maillon, le DNS est devenu bien plus qu'un annuaire : c'est un instrument de pilotage. Un TTL court permet de basculer un site vers d'autres serveurs en quelques minutes (déploiements, pannes). Les CDN s'en servent pour vous répondre avec l'adresse du point de présence le plus proche de *votre résolveur* — c'est en partie pour cela que la page que vous voyez à Paris et celle vue à Tokyo ne sortent pas du même bâtiment. Revers de la médaille : c'est aussi un point de défaillance spectaculaire. Les grandes pannes d'Internet — Dyn en 2016, Facebook en 2021 — furent avant tout des pannes de DNS.

Notre machine détient désormais une adresse : `203.0.113.7`, gardée en cache pour les 300 prochaines secondes. Une vingtaine de millisecondes se sont écoulées. Il est temps d'établir le contact.

---

## 04 — TCP : fabriquer un canal fiable sur un réseau qui ne l'est pas
{: #ch4}

*t + 22 ms · protocole, système, matériel*

Internet, à sa base, ne promet presque rien. Le protocole **IP** achemine des paquets indépendants, en « meilleur effort » : ils peuvent se perdre, arriver en double, en désordre, ou pas du tout. Construire là-dessus quelque chose d'utilisable, c'est le travail de **TCP** (*Transmission Control Protocol*, 1981) : un flux d'octets fiable et ordonné, simulé au-dessus d'un service qui ne l'est pas.

Le processus réseau du navigateur demande au noyau une prise de communication — une **socket** — via un appel système, puis `connect()` vers `203.0.113.7`, port `443`. Le noyau choisit un port source éphémère (disons `51646`) : le quadruplet *(IP source, port source, IP destination, port destination)* identifiera cette connexion parmi toutes les autres. Puis s'engage la fameuse **poignée de main en trois temps** : la machine envoie un segment `SYN` (« je veux ouvrir, je numérote mes octets à partir de X »), le serveur répond `SYN-ACK` (« reçu, moi je numérote à partir de Y »), la machine conclut par `ACK`. Un aller-retour complet — nos ~15 ms — avant le moindre octet utile : c'est le prix d'entrée, et la raison pour laquelle navigateurs et serveurs recyclent leurs connexions autant que possible.

Ces numéros de séquence sont le cœur du mécanisme : chaque octet émis est numéroté et doit être acquitté. Non acquitté à temps ? Retransmis. Arrivé en désordre ? Réordonné. TCP gère aussi deux régulations : le **contrôle de flux** (ne pas noyer le destinataire, qui annonce sa fenêtre de réception) et le **contrôle de congestion** (ne pas noyer le réseau). Une connexion démarre prudemment — le *slow start*, une dizaine de segments — puis accélère à chaque aller-retour sans perte, et ralentit dès que ça frotte. Des algorithmes comme CUBIC ou BBR passent leur vie à chercher le débit maximal que le chemin peut porter. C'est grâce à eux qu'Internet ne s'effondre pas sur lui-même — il l'a fait, une fois, en 1986.

> **Sous la loupe — le trajet d'un segment dans votre machine**
>
> Quand le noyau émet ce `SYN`, que se passe-t-il physiquement ? La pile TCP/IP du noyau construit le segment dans une structure en RAM, y ajoute l'en-tête IP, choisit l'interface de sortie d'après sa table de routage, et le dépose dans une file de l'émetteur : l'anneau de transmission de la **carte réseau** (NIC). Celle-ci lit alors le paquet *directement en RAM*, sans déranger le processeur — c'est le **DMA**, l'accès direct à la mémoire — puis le sérialise sur le support : impulsions électriques sur du cuivre, symboles radio en Wi-Fi, lumière sur la fibre. À la réception, symétrie parfaite : la carte dépose les paquets en RAM par DMA et lève une interruption, exactement comme le clavier au chapitre 01. À haut débit, le noyau bascule même en mode sondage (NAPI) pour ne pas mourir sous les interruptions — un serveur chargé en reçoit des millions par seconde.

---

## 05 — TLS : sceller l'enveloppe
{: #ch5}

*t + 37 ms · protocole, cryptographie*

Le canal TCP existe, mais tout ce qui y passerait serait lisible — et falsifiable — par chaque routeur, chaque Wi-Fi public, chaque intermédiaire du chemin. Le `s` de `https`, c'est **TLS** (*Transport Layer Security*), qui apporte trois garanties : la **confidentialité** (chiffrement), l'**intégrité** (toute altération est détectée) et l'**authenticité** (vous parlez bien à `example.com`, pas à un imposteur).

En TLS 1.3 (2018), la négociation tient en un seul aller-retour. Le navigateur ouvre avec un `ClientHello` : les suites cryptographiques qu'il sait parler, le nom du site demandé (le **SNI**, nécessaire car un même serveur héberge souvent des centaines de sites), l'extension **ALPN** (« sais-tu parler HTTP/2 ? »), et — l'astuce qui économise un aller-retour par rapport à TLS 1.2 — sa **part d'un échange de clés Diffie-Hellman** sur courbe elliptique, envoyée d'office. Le serveur répond avec sa propre part, son **certificat**, et une signature prouvant qu'il détient la clé privée associée. Dès cet instant, les deux parties dérivent les mêmes clés de session sans jamais les avoir transmises — c'est la beauté de Diffie-Hellman — et tout le reste de la conversation est chiffré (AES-GCM ou ChaCha20-Poly1305).

Reste la question de confiance : pourquoi croire ce certificat ? Parce qu'il est signé par une **autorité de certification** (Let's Encrypt, DigiCert…), elle-même signée par une autorité racine dont la clé publique est pré-installée dans votre OS et votre navigateur — le *magasin de confiance*, une centaine d'organisations qui portent, littéralement, la confiance du web. Le navigateur vérifie la chaîne complète, le nom, les dates, et la présence du certificat dans les journaux publics de *Certificate Transparency*. Bonus élégant : les clés de session étant éphémères, même un attaquant qui volerait plus tard la clé privée du serveur ne pourrait pas déchiffrer les conversations passées — la **confidentialité persistante** (*forward secrecy*).

<figure class="odyssee-fig">
<svg viewBox="0 0 760 470" role="img" aria-label="Diagramme de séquence : poignée de main TCP en trois messages, puis poignée de main TLS 1.3 en un aller-retour, puis envoi de la requête HTTP chiffrée.">
<defs>
<marker id="o-arr4" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker>
<marker id="o-arr4A" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<g font-family="monospace">
<g fill="currentColor" font-size="12.5" font-weight="600" text-anchor="middle">
<text x="170" y="30">Votre machine</text>
<text x="550" y="30">Serveur</text>
</g>
<g stroke="currentColor" stroke-opacity="0.3" stroke-dasharray="4 5">
<line x1="170" y1="44" x2="170" y2="440"/>
<line x1="550" y1="44" x2="550" y2="440"/>
</g>
<g font-size="10.5">
<line x1="170" y1="74" x2="543" y2="90" stroke="currentColor" stroke-opacity="0.6" marker-end="url(#o-arr4)"/>
<text x="352" y="70" fill="currentColor" text-anchor="middle">SYN — « j'ouvre, seq = X »</text>
<line x1="550" y1="112" x2="177" y2="128" stroke="currentColor" stroke-opacity="0.6" marker-end="url(#o-arr4)"/>
<text x="360" y="110" fill="currentColor" text-anchor="middle">SYN-ACK — « reçu, seq = Y »</text>
<line x1="170" y1="150" x2="543" y2="166" stroke="currentColor" stroke-opacity="0.6" marker-end="url(#o-arr4)"/>
<text x="352" y="147" fill="currentColor" text-anchor="middle">ACK</text>
</g>
<g font-size="10.5">
<line x1="170" y1="212" x2="543" y2="228" stroke="currentColor" stroke-opacity="0.6" marker-end="url(#o-arr4)"/>
<text x="352" y="196" fill="currentColor" text-anchor="middle">ClientHello</text>
<text x="352" y="209" fill="var(--muted)" text-anchor="middle">SNI · ALPN · part de clé</text>
<line x1="550" y1="252" x2="177" y2="268" stroke="currentColor" stroke-opacity="0.6" marker-end="url(#o-arr4)"/>
<text x="360" y="240" fill="currentColor" text-anchor="middle">ServerHello</text>
<text x="360" y="253" fill="var(--muted)" text-anchor="middle">part de clé · certificat · signature</text>
<text x="150" y="292" fill="var(--muted)" text-anchor="end">clés dérivées —</text>
<text x="150" y="305" fill="var(--muted)" text-anchor="end">canal chiffré</text>
</g>
<g font-size="10.5">
<line x1="170" y1="330" x2="543" y2="346" stroke="var(--accent)" stroke-width="1.6" marker-end="url(#o-arr4A)"/>
<text x="352" y="326" fill="var(--accent)" font-weight="600" text-anchor="middle">Finished + GET / HTTP/2 (chiffré)</text>
<line x1="550" y1="386" x2="177" y2="402" stroke="var(--accent)" stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#o-arr4A)"/>
<text x="360" y="382" fill="var(--accent)" font-weight="600" text-anchor="middle">200 OK + HTML (chiffré)</text>
</g>
<g stroke="currentColor" stroke-opacity="0.45" fill="none">
<path d="M 620 74 h 14 v 88 h -14"/>
<path d="M 620 212 h 14 v 130 h -14"/>
</g>
<g fill="var(--muted)" font-size="10.5">
<text x="646" y="114">1 RTT — TCP</text>
<text x="646" y="272">1 RTT — TLS 1.3</text>
<text x="646" y="286">(2 en TLS 1.2)</text>
</g>
<g fill="var(--muted)" font-size="10">
<text x="34" y="80">t+22 ms</text>
<text x="34" y="218">t+37 ms</text>
<text x="34" y="336">t+52 ms</text>
<text x="34" y="408">t+130 ms</text>
</g>
<text x="360" y="452" fill="var(--muted)" font-size="10.5" text-anchor="middle">le temps s'écoule vers le bas · chaque flèche traverse ~1500 km de réseau</text>
</g>
</svg>
<figcaption>Deux poignées de main, deux allers-retours. TCP établit le canal, TLS 1.3 le chiffre — et la requête HTTP part accolée au dernier message du client. HTTP/3 fusionne ces deux étages en un seul aller-retour grâce à QUIC.</figcaption>
</figure>

---

## 06 — HTTP : enfin, la requête
{: #ch6}

*t + 52 ms · protocole, navigateur*

Cinquante millisecondes de préparatifs pour en arriver là : demander la page. **HTTP** (*HyperText Transfer Protocol*) est un protocole d'une simplicité désarmante — c'est son génie. Un client demande une ressource par un **verbe** et un chemin, un serveur répond par un **code de statut** et un contenu. Conceptuellement, notre requête ressemble à ceci :

```http
GET / HTTP/2
host: www.example.com
user-agent: Mozilla/5.0 (Macintosh…) Chrome/143.0
accept: text/html,application/xhtml+xml,…
accept-encoding: gzip, deflate, br, zstd
accept-language: fr-FR,fr;q=0.9
cookie: session=k7Jq2…
if-none-match: "a1b9c"
```

Chaque en-tête est une petite négociation : les formats acceptés, les compressions comprises (`br`, c'est Brotli, qui divise le poids du HTML par cinq), la langue préférée, les cookies qui portent votre session. Et `if-none-match` illustre l'obsession du cache : il signifie « j'ai déjà une copie, version a1b9c » — si le serveur constate que cette copie est encore la bonne, il répondra `304 Not Modified`, sans corps, quelques octets au lieu de quelques dizaines de kilo-octets.

La réponse aura la même forme : un statut (`200 OK`, `301` redirection, `404` introuvable, `500` erreur serveur — les 2xx disent « succès », les 3xx « allez voir ailleurs », les 4xx « c'est vous », les 5xx « c'est moi »), des en-têtes (type de contenu, directives de cache `cache-control`, en-têtes de sécurité), puis le corps : le HTML.

Le protocole, lui, a beaucoup évolué sous cette surface stable :

| Version | Année | Apport décisif |
|---|---|---|
| `HTTP/1.1` | 1997 | Connexions réutilisées ; mais une seule requête à la fois par connexion — d'où les files d'attente. |
| `HTTP/2` | 2015 | **Multiplexage** : des dizaines de requêtes entrelacées sur une seule connexion TCP ; en-têtes compressés (HPACK). |
| `HTTP/3` | 2022 | Abandonne TCP pour **QUIC** (sur UDP) : poignées de main transport et chiffrement fusionnées en 1 aller-retour, plus de blocage en tête de file, et la connexion survit au passage du Wi-Fi à la 4G. |

Notre navigateur, prévenu par l'ALPN du chapitre précédent, parle ici HTTP/2. La requête — quelques centaines d'octets une fois compressée et chiffrée — est remise au noyau, qui la découpe en segments TCP. Elle quitte la machine. Suivons-la.

---

## 07 — Le voyage : routeurs, câbles et lumière
{: #ch7}

*t + 53 ms · réseau, matériel*

Ce qui circule sur le câble n'est pas « une requête » : c'est une **poupée russe**. La requête HTTP est chiffrée dans un enregistrement TLS, découpé en segments TCP, chacun glissé dans un paquet IP, lui-même emballé dans une trame adaptée au support physique. Chaque couche a son en-tête, ses adresses, son rôle — et chaque équipement du chemin ne lit que la couche qui le concerne.

<figure class="odyssee-fig">
<svg viewBox="0 0 900 290" role="img" aria-label="Encapsulation : la requête HTTP est enveloppée dans TLS, puis TCP, puis IP, puis une trame Ethernet ou Wi-Fi, chaque couche ajoutant son en-tête.">
<g font-family="monospace" font-size="11">
<text x="20" y="46" fill="var(--muted)" font-size="10.5">APPLICATION</text>
<rect x="620" y="30" width="260" height="26" rx="5" fill="var(--accent-soft)" stroke="var(--accent)"/>
<text x="750" y="47" fill="var(--accent)" font-weight="600" text-anchor="middle">requête HTTP</text>
<text x="20" y="100" fill="var(--muted)" font-size="10.5">CHIFFREMENT</text>
<rect x="530" y="84" width="86" height="26" rx="5" fill="var(--bg)" stroke="currentColor" stroke-opacity="0.5"/>
<text x="573" y="101" fill="currentColor" text-anchor="middle">TLS</text>
<rect x="620" y="84" width="260" height="26" rx="5" fill="var(--accent-soft)" stroke="var(--accent)" stroke-dasharray="4 3"/>
<text x="750" y="101" fill="var(--accent)" text-anchor="middle">⋯ chiffrée ⋯</text>
<text x="20" y="154" fill="var(--muted)" font-size="10.5">TRANSPORT</text>
<rect x="404" y="138" width="122" height="26" rx="5" fill="var(--bg)" stroke="currentColor" stroke-opacity="0.5"/>
<text x="465" y="155" fill="currentColor" text-anchor="middle">en-tête TCP</text>
<text x="465" y="177" fill="var(--muted)" font-size="9.5" text-anchor="middle">ports · seq · ack</text>
<rect x="530" y="138" width="350" height="26" rx="5" fill="var(--bg)" stroke="currentColor" stroke-opacity="0.35"/>
<text x="705" y="155" fill="var(--muted)" text-anchor="middle">← tout ce qui précède</text>
<text x="20" y="208" fill="var(--muted)" font-size="10.5">RÉSEAU</text>
<rect x="278" y="192" width="122" height="26" rx="5" fill="var(--bg)" stroke="currentColor" stroke-opacity="0.5"/>
<text x="339" y="209" fill="currentColor" text-anchor="middle">en-tête IP</text>
<text x="339" y="231" fill="var(--muted)" font-size="9.5" text-anchor="middle">IP src · IP dst · TTL</text>
<rect x="404" y="192" width="476" height="26" rx="5" fill="var(--bg)" stroke="currentColor" stroke-opacity="0.35"/>
<text x="642" y="209" fill="var(--muted)" text-anchor="middle">← segment TCP</text>
<text x="20" y="262" fill="var(--muted)" font-size="10.5">LIAISON</text>
<rect x="152" y="246" width="122" height="26" rx="5" fill="var(--bg)" stroke="currentColor" stroke-opacity="0.5"/>
<text x="213" y="263" fill="currentColor" text-anchor="middle">trame Eth/Wi-Fi</text>
<rect x="278" y="246" width="602" height="26" rx="5" fill="var(--bg)" stroke="currentColor" stroke-opacity="0.35"/>
<text x="580" y="263" fill="var(--muted)" text-anchor="middle">← paquet IP (≤ 1500 octets, le MTU)</text>
<g stroke="currentColor" stroke-opacity="0.22">
<line x1="620" y1="56" x2="620" y2="84"/>
<line x1="880" y1="56" x2="880" y2="84"/>
<line x1="530" y1="110" x2="530" y2="138"/>
<line x1="880" y1="110" x2="880" y2="138"/>
<line x1="404" y1="164" x2="404" y2="192"/>
<line x1="880" y1="164" x2="880" y2="192"/>
<line x1="278" y1="218" x2="278" y2="246"/>
<line x1="880" y1="218" x2="880" y2="246"/>
</g>
</g>
</svg>
<figcaption>L'encapsulation. Chaque couche traite celle du dessus comme une cargaison opaque et y accole son en-tête. Les routeurs ne lisent que l'étage IP ; votre box réécrit l'étage IP ; seuls les deux bouts peuvent ouvrir l'étage TLS. Si le tout dépasse le MTU (~1500 octets), c'est découpé en plusieurs paquets.</figcaption>
</figure>

Premier bond : la trame part en **Wi-Fi** vers la box — modulée en symboles radio sur un canal partagé, acquittée trame par trame, retransmise en cas de collision — ou en Ethernet sur cuivre. La **box** joue alors trois rôles : commutateur, routeur, et surtout **NAT**. Votre machine porte une adresse privée (`192.168.1.24`) invisible d'Internet ; la box substitue sa propre adresse publique, note la correspondance dans sa table (`192.168.1.24:51646 ↔ 88.x.x.x:29104`), et fera la traduction inverse au retour. Puis le paquet file sur la fibre : converti en lumière, il traverse le réseau de collecte du FAI jusqu'à un cœur de réseau régional.

À partir de là, le paquet saute de routeur en routeur — quinze à vingt-cinq bonds typiquement, visibles avec l'outil `traceroute`. Chaque routeur fait une seule chose, des millions de fois par seconde : lire l'adresse IP de destination, consulter sa table de routage (plus d'un million de préfixes aujourd'hui), décrémenter le champ **TTL** (à zéro, le paquet meurt — c'est l'anti-boucle), et réémettre sur la bonne interface. Mais qui remplit ces tables ? Personne ne « dirige » Internet : c'est une fédération d'environ cent mille **systèmes autonomes** (AS) — FAI, hébergeurs, universités, géants du cloud — qui s'annoncent mutuellement leurs routes via le protocole **BGP**, se connectent en direct sur des points d'échange (à Paris : France-IX) ou achètent du transit aux opérateurs de dorsales. La route de votre paquet est le produit de milliers d'accords commerciaux — et d'aucun plan d'ensemble.

Si le serveur est loin, le paquet empruntera l'un des ~500 **câbles sous-marins** qui tissent les continents — des fibres de la taille d'un tuyau d'arrosage qui portent chacune des centaines de térabits par seconde. Dans le verre, la lumière avance à ~200 000 km/s, les deux tiers de sa vitesse dans le vide : Paris–New York coûte incompressiblement ~30 ms l'aller. C'est la seule limite que l'ingénierie ne négociera jamais — d'où, précisément, l'invention des CDN : si on ne peut pas accélérer la lumière, on rapproche le serveur.

---

## 08 — Côté serveur : la remontée de la pile, en miroir
{: #ch8}

*t + 65 ms · serveur, réseau, système*

« Le serveur » est une commodité de langage. Pour un site sérieux, votre requête atterrit d'abord sur un **point de présence** (PoP) d'un CDN — Cloudflare, Fastly, Akamai, CloudFront — situé à quelques millisecondes de chez vous, sélectionné par la magie du DNS géographique ou de l'anycast croisés au chapitre 03. C'est lui qui a répondu aux poignées de main : la **terminaison TLS** se fait en périphérie, précisément pour que ces allers-retours restent courts.

Là, premier verdict : le **cache**. Si la ressource est statique et présente sur le PoP, la réponse repart immédiatement — la majorité du trafic mondial se règle ainsi, sans jamais toucher le serveur d'origine. Notre page d'accueil est dynamique : direction l'origine, via une connexion longue distance que le CDN maintient ouverte et réutilise (encore des poignées de main économisées).

À l'origine, la requête traverse une petite chaîne de tri. Un **répartiteur de charge** la distribue vers l'une des machines saines du parc — il les sonde en permanence et écarte celles qui toussent. Sur la machine élue, le noyau vit le chapitre 04 en miroir : le port 443 est en écoute, la connexion sort de la file d'accept, et un **reverse proxy** comme nginx la prend en charge. Son architecture mérite une phrase : un processus par cœur, chacun surveillant des dizaines de milliers de connexions via `epoll` — le mécanisme du noyau qui dit « préviens-moi quand l'une d'elles a du nouveau » — sans jamais bloquer. C'est la réponse moderne au vieux « problème des 10 000 connexions ».

nginx transmet enfin à l'**application** — du code Node.js, Python, Go, PHP, Java… — qui fait le vrai travail métier : valider la session portée par le cookie, interroger la **base de données** (elle-même précédée d'un cache mémoire type Redis, car même 5 ms de requête SQL sont une éternité à cette échelle), assembler le HTML. Puis tout redescend : compression Brotli, chiffrement TLS, segments TCP, paquets IP — la pile entière, dans l'autre sens.

<figure class="odyssee-fig">
<svg viewBox="0 0 940 250" role="img" aria-label="Chaîne côté serveur : le point de présence CDN sert les caches immédiatement ; sinon la requête traverse répartiteur de charge, reverse proxy, application et base de données.">
<defs>
<marker id="o-arr5" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker>
<marker id="o-arr5A" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<g font-family="monospace">
<g stroke="currentColor" stroke-opacity="0.45" fill="var(--bg)">
<rect x="14" y="96" width="96" height="60" rx="9"/>
<rect x="170" y="96" width="150" height="60" rx="9"/>
<rect x="380" y="96" width="130" height="60" rx="9"/>
<rect x="570" y="96" width="120" height="60" rx="9"/>
<rect x="750" y="96" width="80" height="60" rx="9"/>
<rect x="864" y="96" width="62" height="60" rx="9"/>
</g>
<g fill="currentColor" font-size="11.5" font-weight="600" text-anchor="middle">
<text x="62" y="122">Vous</text>
<text x="245" y="122">PoP CDN</text>
<text x="445" y="122">Répartiteur</text>
<text x="630" y="122">nginx</text>
<text x="790" y="122">App</text>
<text x="895" y="122">BD</text>
</g>
<g fill="var(--muted)" font-size="9.5" text-anchor="middle">
<text x="62" y="138">navigateur</text>
<text x="245" y="138">TLS · cache edge</text>
<text x="445" y="138">L4/L7 · santé</text>
<text x="630" y="138">epoll · workers</text>
<text x="790" y="138">métier</text>
<text x="895" y="138">+ Redis</text>
</g>
<g stroke="currentColor" stroke-opacity="0.55" marker-end="url(#o-arr5)">
<line x1="110" y1="118" x2="163" y2="118"/>
<line x1="320" y1="118" x2="373" y2="118"/>
<line x1="510" y1="118" x2="563" y2="118"/>
<line x1="690" y1="118" x2="743" y2="118"/>
<line x1="830" y1="118" x2="857" y2="118"/>
</g>
<g fill="var(--muted)" font-size="9.5" text-anchor="middle">
<text x="136" y="106">~10 ms</text>
<text x="346" y="106">MISS</text>
<text x="536" y="106">choisit</text>
<text x="716" y="106">proxifie</text>
</g>
<path d="M 225 96 C 210 40, 110 40, 72 88" fill="none" stroke="var(--accent)" stroke-width="1.5" stroke-dasharray="5 4" marker-end="url(#o-arr5A)"/>
<text x="148" y="34" fill="var(--accent)" font-size="10" font-weight="600" text-anchor="middle">HIT : réponse servie depuis la périphérie</text>
<path d="M 790 156 C 790 208, 140 208, 68 160" fill="none" stroke="var(--accent)" stroke-width="1.5" marker-end="url(#o-arr5A)"/>
<text x="470" y="228" fill="var(--accent)" font-size="10" font-weight="600" text-anchor="middle">MISS : HTML assemblé, compressé, chiffré — et renvoyé (TTFB ~75 ms après l'envoi)</text>
</g>
</svg>
<figcaption>Deux issues. En cache HIT, la périphérie répond en quelques millisecondes. En MISS, la requête traverse toute la chaîne d'origine ; chaque maillon existe pour absorber la charge, tolérer les pannes, ou gagner des millisecondes.</figcaption>
</figure>

Le premier octet de la réponse atteint votre machine autour de `t + 130 ms` — c'est le **TTFB** (*time to first byte*) des outils de mesure. Le reste du HTML suit, cadencé par le contrôle de congestion, en quelques dizaines de millisecondes. La partie réseau de l'odyssée s'achève. Reste à transformer ces octets en page.

---

## 09 — Le rendu : de l'octet au pixel
{: #ch9}

*t + 130 ms · navigateur, matériel*

Les octets déchiffrés et décompressés sont poussés vers le processus de rendu sandboxé du chapitre 02. Commence la dernière métamorphose, la plus étrange : transformer du texte en géométrie, puis en couleurs.

Le **parseur HTML** lit le document et construit le **DOM**, l'arbre des éléments. Il n'attend pas la fin : dès les premières lignes, un *préchargeur* balaie le reste du fichier à la recherche de ressources à télécharger — feuilles de style, scripts, polices, images — et lance ces requêtes en parallèle. *Chacune rejoue une mini-odyssée* : cache, DNS éventuel, la connexion HTTP/2 existante, le CDN. Une page moyenne embarque ainsi 70 sous-ressources ; c'est le vrai coût du web moderne, bien plus que le HTML lui-même.

Le CSS, parsé de son côté, devient le **CSSOM** : l'ensemble des règles, résolues selon la cascade et la spécificité. Le JavaScript, lui, passe au moteur **V8** : d'abord compilé en bytecode et interprété, puis — pour les fonctions chaudes — recompilé à la volée en code machine optimisé par les étages supérieurs du JIT, avec des paris sur les types qui seront annulés si le code se met à mentir. Attention au piège historique : un `<script>` sans attribut `defer`/`async` *bloque le parseur*, car il a le droit de réécrire le document en plein vol. C'est la raison d'être de la moitié des conseils de performance web.

DOM et CSSOM fusionnent en **arbre de rendu** (les éléments visibles, avec leurs styles calculés). Le **layout** résout alors le système de contraintes — flexbox, grilles, flux de texte — et assigne à chaque boîte une position et une taille au pixel près. Le **paint** convertit ces boîtes en listes d'instructions de dessin, rastérisées par couches. Enfin le **compositeur** — sur son propre fil d'exécution, aidé du processus GPU — assemble les couches à l'écran. C'est lui qui rend le défilement fluide : faire glisser des couches déjà peintes ne coûte presque rien au **GPU**, pendant que le fil principal reste libre.

<figure class="odyssee-fig">
<svg viewBox="0 0 940 280" role="img" aria-label="Pipeline de rendu : HTML vers DOM, CSS vers CSSOM, JavaScript pouvant modifier les deux ; fusion en arbre de rendu, puis layout, paint, compositing GPU et affichage.">
<defs>
<marker id="o-arr6" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker>
<marker id="o-arr6A" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--accent)"/></marker>
</defs>
<g font-family="monospace">
<g stroke="currentColor" stroke-opacity="0.45" fill="var(--bg)">
<rect x="20" y="34" width="84" height="44" rx="8"/>
<rect x="20" y="120" width="84" height="44" rx="8"/>
<rect x="20" y="206" width="84" height="44" rx="8"/>
<rect x="170" y="34" width="96" height="44" rx="8"/>
<rect x="170" y="120" width="96" height="44" rx="8"/>
<rect x="330" y="77" width="120" height="44" rx="8"/>
<rect x="510" y="77" width="96" height="44" rx="8"/>
<rect x="660" y="77" width="90" height="44" rx="8"/>
<rect x="800" y="77" width="126" height="44" rx="8"/>
</g>
<g fill="currentColor" font-size="11.5" font-weight="600" text-anchor="middle">
<text x="62" y="60">HTML</text>
<text x="62" y="146">CSS</text>
<text x="62" y="232">JS</text>
<text x="218" y="60">DOM</text>
<text x="218" y="146">CSSOM</text>
<text x="390" y="94">Arbre de</text>
<text x="390" y="108">rendu</text>
<text x="558" y="102">Layout</text>
<text x="705" y="102">Paint</text>
<text x="863" y="94">Composite</text>
<text x="863" y="108">GPU → écran</text>
</g>
<g stroke="currentColor" stroke-opacity="0.55" marker-end="url(#o-arr6)">
<line x1="104" y1="56" x2="163" y2="56"/>
<line x1="104" y1="142" x2="163" y2="142"/>
<line x1="266" y1="56" x2="330" y2="88"/>
<line x1="266" y1="142" x2="330" y2="110"/>
<line x1="450" y1="99" x2="503" y2="99"/>
<line x1="606" y1="99" x2="653" y2="99"/>
</g>
<line x1="750" y1="99" x2="793" y2="99" stroke="var(--accent)" stroke-width="1.6" marker-end="url(#o-arr6A)"/>
<g fill="var(--muted)" font-size="9.5" text-anchor="middle">
<text x="134" y="46">parseur</text>
<text x="134" y="132">parseur</text>
<text x="478" y="88">géométrie</text>
<text x="630" y="88">dessin</text>
</g>
<g stroke="var(--accent)" stroke-opacity="0.85" stroke-dasharray="4 4" marker-end="url(#o-arr6A)">
<line x1="104" y1="222" x2="212" y2="170"/>
<line x1="104" y1="234" x2="330" y2="234"/>
</g>
<text x="150" y="196" fill="var(--accent)" font-size="9.5">modifie le DOM</text>
<text x="220" y="224" fill="var(--accent)" font-size="9.5">V8 : bytecode → JIT (peut bloquer le parseur)</text>
<text x="470" y="268" fill="var(--muted)" font-size="10.5" text-anchor="middle">tout changement ultérieur (interaction, animation) rejoue une partie de cette chaîne — idéalement 120 fois par seconde</text>
</g>
</svg>
<figcaption>Le chemin critique du rendu. Deux arbres construits en parallèle, un troisième acteur (JavaScript) capable de modifier les deux premiers, puis une chaîne géométrie → dessin → composition dont la dernière étape vit sur le GPU.</figcaption>
</figure>

Dernier maillon, purement matériel : le compositeur livre ses images au rythme du **VSync** de l'écran. Le contrôleur d'affichage lit la mémoire vidéo et pilote la dalle, qui ajuste ses cristaux liquides ou ses OLED pixel par pixel. Autour de `t + 300 ms`, les photons partent vers votre rétine. Les métriques modernes donnent des noms à ces instants : *First Contentful Paint* pour le premier contenu, *Largest Contentful Paint* pour l'élément principal. Votre page est là.

---

## 10 — Épilogue : trois cents millisecondes
{: #outro}

*t + 300 ms*

Récapitulons le voyage, en vraie grandeur :

<figure class="odyssee-fig">
<svg viewBox="0 0 960 336" role="img" aria-label="Frise chronologique de 0 à 300 millisecondes : résolution DNS, poignée de main TCP, poignée de main TLS, attente de la réponse, téléchargement, parsing et scripts, layout et paint, premier rendu vers 300 millisecondes.">
<g font-family="monospace" font-size="10.5">
<g stroke="currentColor" stroke-opacity="0.15">
<line x1="200" y1="30" x2="200" y2="292"/>
<line x1="320" y1="30" x2="320" y2="292"/>
<line x1="440" y1="30" x2="440" y2="292"/>
<line x1="560" y1="30" x2="560" y2="292"/>
<line x1="680" y1="30" x2="680" y2="292"/>
<line x1="800" y1="30" x2="800" y2="292"/>
</g>
<g fill="var(--muted)" text-anchor="middle">
<text x="200" y="20">0</text>
<text x="320" y="20">50 ms</text>
<text x="440" y="20">100 ms</text>
<text x="560" y="20">150 ms</text>
<text x="680" y="20">200 ms</text>
<text x="800" y="20">250 ms</text>
<text x="920" y="20">300 ms</text>
</g>
<g fill="currentColor" fill-opacity="0.16" stroke="currentColor" stroke-opacity="0.45">
<rect x="205" y="44" width="48" height="24" rx="4"/>
<rect x="253" y="80" width="36" height="24" rx="4"/>
<rect x="289" y="116" width="36" height="24" rx="4"/>
<rect x="325" y="152" width="187" height="24" rx="4"/>
<rect x="512" y="188" width="96" height="24" rx="4"/>
<rect x="608" y="224" width="168" height="24" rx="4"/>
<rect x="776" y="260" width="132" height="24" rx="4"/>
</g>
<g fill="currentColor" text-anchor="end">
<text x="188" y="60">DNS</text>
<text x="188" y="96">TCP</text>
<text x="188" y="132">TLS</text>
<text x="188" y="168">attente réseau + serveur</text>
<text x="188" y="204">téléchargement HTML</text>
<text x="188" y="240">parsing + scripts</text>
<text x="188" y="276">layout + paint</text>
</g>
<g fill="var(--muted)">
<text x="261" y="60">~20 ms</text>
<text x="297" y="96">~15 ms</text>
<text x="333" y="132">~15 ms</text>
<text x="520" y="168">~78 ms</text>
<text x="616" y="204">~40 ms</text>
<text x="784" y="240">~70 ms</text>
<text x="800" y="298">~55 ms</text>
</g>
<line x1="920" y1="30" x2="920" y2="292" stroke="var(--accent)" stroke-width="1.8"/>
<circle cx="920" cy="272" r="4.5" fill="var(--accent)"/>
<text x="912" y="316" fill="var(--accent)" font-weight="600" text-anchor="end">premier rendu à l'écran</text>
</g>
</svg>
<figcaption>Le budget d'une navigation. Ordres de grandeur pour une première visite, sur fibre, vers un site bien servi. Une visite suivante saute les quatre premières barres (caches DNS, connexion réutilisée) ; un mobile en 4G sur un site négligé peut multiplier chaque barre par dix.</figcaption>
</figure>

Trois cents millisecondes, donc — un battement de paupières. Dans ce battement : un microcontrôleur de clavier, une interruption matérielle, une quinzaine de processus, quatre protocoles empilés, un annuaire distribué sur des milliers de serveurs, deux poignées de main cryptographiques, une vingtaine de routeurs appartenant à une demi-douzaine d'organisations différentes, un centre de données, une base de données, un compilateur à la volée et une carte graphique. Le noyau Linux pèse à lui seul quelque quarante millions de lignes de code, Chromium à peu près autant : *personne*, nulle part, ne comprend l'édifice en entier. Il tient parce que chaque couche offre à celle du dessus une abstraction simple — un flux fiable, un nom résolu, un canal sûr, un document structuré — et lui cache tout le reste.

Et le plus vertigineux n'est pas là. Le plus vertigineux, c'est que ce n'était que la première requête. Chaque feuille de style, chaque script, chaque image de la page a rejoué sa propre miniature de cette odyssée ; chaque lien sur lequel vous cliquerez recommencera tout. Ce ballet se produit, à l'échelle du globe, quelques millions de fois *par seconde* — sur une infrastructure sans chef d'orchestre, tenue par des accords entre cent mille réseaux et par une pile de standards ouverts dont les plus anciens ont cinquante ans. La prochaine fois que vous appuierez sur Entrée, vous saurez ce que vous venez de déclencher.

---

## Pour creuser

- [What happens when…](https://github.com/alex/what-happens-when) — la version encyclopédique et collaborative de cette question, en anglais.
- [High Performance Browser Networking](https://hpbn.co/), Ilya Grigorik — le livre de référence, libre d'accès, sur TCP, TLS, HTTP et les réseaux mobiles.
- [How DNS works](https://howdns.works/) — la résolution DNS en bande dessinée.
- [Inside look at modern web browser](https://developer.chrome.com/blog/inside-browser-part1) — l'architecture de Chrome racontée par son équipe, en quatre parties.
- Les textes canoniques, d'une lisibilité étonnante : [RFC 9293](https://www.rfc-editor.org/rfc/rfc9293) (TCP), [RFC 8446](https://www.rfc-editor.org/rfc/rfc8446) (TLS 1.3), [RFC 9114](https://www.rfc-editor.org/rfc/rfc9114) (HTTP/3).

<small>Les durées de cet article sont des ordres de grandeur, pas des mesures. Schémas SVG faits main. <code>www.example.com</code> est un domaine réservé à la documentation par la <a href="https://www.rfc-editor.org/rfc/rfc2606">RFC 2606</a>, qui vous répondra pourtant vraiment.</small>
