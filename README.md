🎮 Pygame Action Platformer with Boss Fight & Admin Panel

📌 Description

Ce projet est un jeu de plateforme 2D développé en Python avec Pygame, orienté action, mobilité avancée et combat contre un boss. Il inclut un système de combat dynamique, des mécaniques avancées de déplacement, un boss avec IA, ainsi qu’un panneau administrateur intégré en jeu permettant de modifier l’état du jeu en temps réel.

Le projet est conçu comme une base solide extensible pour un jeu complet : ajout de nouveaux niveaux, ennemis, compétences, ou systèmes (inventaire, sauvegarde, etc.).

🧠 Fonctionnalités principales

🧍 Joueur

Le joueur dispose de nombreuses mécaniques avancées :

Déplacement horizontal fluide

Saut multiple (double saut)

Saut mural + wall jump

Dash directionnel avec invulnérabilité temporaire

Cooldowns visibles (dash, attaques)

Points de vie avec barre dynamique

⚔️ Combat

Attaque basique (clic gauche)

Attaque chargée (clic droit)

Charge progressive

Dégâts variables selon le pourcentage de charge

Viseur directionnel basé sur la souris

Effets visuels évolutifs selon la puissance

Parade (parry) pour bloquer certaines attaques

👑 Boss

Le boss est une entité centrale du jeu avec :

IA personnalisée

Phases de combat

Attaques multiples :

Projectiles

Zones de feu

Invocation de sbires (minions)

Barre de vie dédiée

Conditions de victoire/défaite

👾 Ennemis & Entités

Minions : ennemis invoqués par le boss

Projectiles : attaques ennemies avec trajectoire

Orbes de soin : permettent au joueur de récupérer des PV

🌍 Environnement

Carte plus grande que l’écran (caméra dynamique)

Plateformes statiques

Murs solides et murs temporaires

Zones de feu :

Ralentissement du joueur

Dégâts progressifs

🧪 Effets & Statuts

Invulnérabilité temporaire (dash)

Brûlure (zones de feu)

Ralentissement

Cooldowns visibles

🛠️ Panneau Admin (Debug / Cheat Panel)

Un panneau administrateur intégré directement dans le jeu, accessible via la touche F2.

Fonctionnalités du panneau admin :

Console en jeu

Entrée de commandes texte

Historique des commandes

Activation / désactivation en temps réel

Exemples d’actions possibles (selon implémentation) :

Donner de la vie au joueur

Activer l’invincibilité

Tuer le boss instantanément

Se téléporter

Spawner des ennemis

Modifier la vitesse du jeu

🎯 Idéal pour le debug, les tests ou un mode "sandbox".

🎮 Contrôles

Action

Touche / Souris

Déplacement gauche

Q

Déplacement droite

D

Saut

Espace

Dash

Shift

Attaque basique

Clic gauche

Attaque chargée

Clic droit

Panneau admin

F2

⚙️ Technologies utilisées

Python 3

Pygame

Programmation orientée objet (OOP)

Gestion manuelle de la physique et des collisions

Architecture modulaire (joueur, boss, projectiles, UI)

📁 Structure du projet (exemple)

project/
│
├── game.py          # Fichier principal
├── README.md        # Documentation du projet
└── assets/          # (optionnel) sprites, sons, etc.

🚀 Lancement du jeu

Installer Python 3

Installer Pygame :

pip install pygame

Lancer le jeu :

python game.py

🔮 Améliorations possibles

Système de sauvegarde

Niveaux multiples

Arbre de compétences

Inventaire

Animations sprites

Effets sonores et musique

Support manette

Mode coop / multijoueur local

📜 Licence

Projet libre d’utilisation à des fins éducatives ou personnelles.
