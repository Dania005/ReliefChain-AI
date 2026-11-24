.PHONY: demo api web seed scenario
demo:
	@echo "Starting ReliefChain API on :8000 and web UI on :3000"
	@start "ReliefChain API" cmd /c "cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
	@start "ReliefChain Web" cmd /c "cd web && npm run dev"
api:
	cd backend && python -m uvicorn app.main:app --reload --port 8000
web:
	cd web && npm run dev
seed:
	python scripts/generate_synthetic.py
scenario:
	python scripts/run_scenario.py
