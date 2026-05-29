# Needle in a Haystack — raccourcis pour les étudiants
# Usage : make <cible>

-include .env
export

.PHONY: help setup up reload down eval eval-medical app

help:
	@echo "Cibles disponibles :"
	@echo "  make setup         Génère les données de test (Python)"
	@echo "  make up            Démarre le viewer Promptfoo  → http://localhost:15500"
	@echo "  make reload        Recrée le container (après un changement de .env)"
	@echo "  make down          Arrête le viewer"
	@echo "  make eval          Lance les 20 tests synthétiques"
	@echo "  make eval-medical  Lance les 20 tests médicaux"
	@echo "  make app           Démarre l'interface web Vue  → http://localhost:5173"

setup:
	python generate_tests.py
	python generate_medical_tests.py

up:
	docker compose up -d

reload:
	docker compose up -d --force-recreate

down:
	docker compose down

eval: up
	docker exec -it promptfoo_local sh /app/eval.sh

eval-medical: up
	docker exec -it promptfoo_local sh /app/eval.sh /app/promptfooconfig.medical.yaml

app:
	@echo "→  Ouvre http://localhost:5173"
	cd app && npm install --silent && npm run dev
