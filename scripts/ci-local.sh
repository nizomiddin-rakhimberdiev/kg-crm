#!/usr/bin/env bash
#
# CI ni LOKAL takrorlaydi — GitHub Actions'dagi bilan AYNAN bir xil qadamlar.
#
# Nega kerak: bu hisobdagi PRIVATE repozitoriyalarda GitHub Actions
# `startup_failure` beradi (P0-004 — sabab hisob darajasida, workflow
# faylida emas). Ya'ni `.github/workflows/` to'g'ri yozilgan bo'lsa ham,
# bugun hech qanday avtomatik darvoza YO'Q. Bu skript — o'sha darvozaning
# qo'lda ishga tushiriladigan o'rnini bosuvchisi.
#
# Ishlatish:
#   ./scripts/ci-local.sh              # hammasi
#   ./scripts/ci-local.sh backend      # faqat backend
#   ./scripts/ci-local.sh frontend     # faqat frontend
#
# Push oldidan avtomatik ishlashi uchun:
#   ln -s ../../scripts/ci-local.sh .git/hooks/pre-push
#
# Chiqish kodi: birorta darvoza yiqilsa — nol emas.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCOPE="${1:-all}"

# CI bazasi ATAYLAB alohida: dev bazangizga tegmaydi va har safar
# noldan migratsiya qilinadi — aynan CI'dagidek.
CI_DB="kg_crm_ci_local"

RED=$'\033[31m'; GREEN=$'\033[32m'; DIM=$'\033[2m'; BOLD=$'\033[1m'; OFF=$'\033[0m'
FAILED=()

step() {
  local label="$1"; shift
  printf '%s▸ %s%s\n' "$BOLD" "$label" "$OFF"
  if "$@" > /tmp/ci-local-step.log 2>&1; then
    printf '  %s✓ PASS%s\n' "$GREEN" "$OFF"
  else
    printf '  %s✗ FAIL%s\n' "$RED" "$OFF"
    printf '%s' "$DIM"; tail -25 /tmp/ci-local-step.log; printf '%s' "$OFF"
    FAILED+=("$label")
  fi
}

# --- Backend ---
run_backend() {
  cd "$ROOT/backend" || exit 1
  # shellcheck disable=SC1091
  source venv/bin/activate || { echo "venv topilmadi"; exit 1; }

  export DJANGO_SETTINGS_MODULE=config.settings.test

  step "backend · zaifliklar"        pip-audit -r requirements/production.txt --progress-spinner off
  step "backend · ruff check"        ruff check .
  step "backend · ruff format"       ruff format --check .
  step "backend · mypy"              mypy apps api config
  step "backend · deploy check"      env \
      DJANGO_SECRET_KEY=ci-secret-key-long-enough-to-pass-the-entropy-check-0123456789 \
      DJANGO_ALLOWED_HOSTS=example.com \
      python manage.py check --deploy --fail-level WARNING \
      --settings=config.settings.production
  step "backend · migratsiya yetishmaydimi" python manage.py makemigrations --check --dry-run

  # Toza bazada: migratsiyalar haqiqatan RLS qo'yadimi?
  dropdb --if-exists "$CI_DB" 2>/dev/null
  createdb "$CI_DB" 2>/dev/null
  step "backend · migrate + check_rls" env POSTGRES_DB="$CI_DB" bash -c \
      'python manage.py migrate --noinput && python manage.py check_rls'
  dropdb --if-exists "$CI_DB" 2>/dev/null

  step "backend · testlar"           pytest --cov=apps --cov=api --cov-report=term-missing
  step "backend · tenant izolyatsiyasi" pytest -m tenancy --tb=short
}

# --- Frontend ---
run_frontend() {
  cd "$ROOT/frontend" || exit 1
  step "frontend · npm ci"           npm ci
  step "frontend · zaifliklar"       npm audit --omit=dev --audit-level=high
  step "frontend · lint"             npm run lint
  step "frontend · typecheck"        npm run typecheck
  step "frontend · testlar"          npm test
  step "frontend · build"            npm run build
}

case "$SCOPE" in
  backend)  run_backend ;;
  frontend) run_frontend ;;
  all)      run_backend; run_frontend ;;
  *) echo "Noma'lum: $SCOPE (backend | frontend | all)"; exit 2 ;;
esac

echo
if [ ${#FAILED[@]} -eq 0 ]; then
  printf '%sBARCHA DARVOZALAR O'\''TDI%s\n' "$GREEN$BOLD" "$OFF"
  exit 0
fi
printf '%sYIQILGAN DARVOZALAR (%d):%s\n' "$RED$BOLD" "${#FAILED[@]}" "$OFF"
printf '  · %s\n' "${FAILED[@]}"
exit 1
