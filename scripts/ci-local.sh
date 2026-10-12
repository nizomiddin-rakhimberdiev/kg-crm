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
#   ./scripts/ci-local.sh              # hammasi (bir necha daqiqa)
#   ./scripts/ci-local.sh backend      # faqat backend
#   ./scripts/ci-local.sh frontend     # faqat frontend
#   ./scripts/ci-local.sh fast         # ~35 soniya — push oldidagi darvoza
#
# `fast` — `pre-push` ilgagi ishlatadigan qism (scripts/hooks/pre-push).
# Unga FAQAT arzon va yuqori qiymatli tekshiruvlar kiradi. Sabab oddiy:
# har bir push'ni bir necha daqiqaga uzaytiradigan ilgak bir hafta ichida
# `--no-verify` bilan chetlab o'tila boshlaydi, ya'ni umuman yo'q ilgakka
# aylanadi. To'liq to'plam — merge va deploy oldidan, qo'lda.
#
# Ilgakni o'rnatish:
#   ln -s ../../scripts/hooks/pre-push .git/hooks/pre-push
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

# Virtualenv'ni yoqadi VA uning to'liqligini tekshiradi.
#
# Ikkinchisi bekorga emas: `venv` bir marta `cryptography` siz qolib
# ketgandi va u holda `pytest -m tenancy` 214 ta xato berardi — biror
# darvoza buzilgani uchun emas, import yiqilgani uchun. Bunday natija
# eng yomoni: u haqiqiy nosozlikka o'xshaydi va skriptga ishonchni
# o'ldiradi. Shuning uchun muhit nuqsoni TEST nuqsonidan ajratib
# aytiladi.
activate_backend() {
  cd "$ROOT/backend" || exit 1
  # shellcheck disable=SC1091
  source venv/bin/activate || { echo "venv topilmadi — python -m venv venv"; exit 1; }

  if ! python -c 'import cryptography, django, pytest' 2>/dev/null; then
    printf '%svenv to'\''liq emas%s — bog'\''liqliklar yetishmayapti.\n' "$RED$BOLD" "$OFF"
    printf 'Tuzatish:  backend/venv/bin/pip install -r requirements/development.txt\n'
    exit 1
  fi

  export DJANGO_SETTINGS_MODULE=config.settings.test
}

# --- Backend ---
run_backend() {
  activate_backend

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

# --- Tez darvoza (pre-push) ---
#
# Tanlov o'lchovga asoslangan, didga emas. Har bir qadam vaqti bilan
# birga yozilgan; yig'indi ~35 soniya. Bundan qimmatroq hamma narsa —
# pip-audit (tarmoq), npm ci, vite build, to'liq pytest va `-m tenancy`
# (50 s) — ataylab TASHQARIDA qoldirilgan.
run_fast() {
  activate_backend

  step "tez · ruff check"              ruff check .          # 0.1 s
  step "tez · ruff format"             ruff format --check . # 0.1 s
  step "tez · migratsiya yetishmaydimi" python manage.py makemigrations --check --dry-run  # 1 s
  step "tez · tarjima to'liqligi"      pytest apps/core/tests/test_i18n.py -q              # 10 s
  # Loyihaning ikkita eng og'ir invarianti — RLS qoplami (8) va yozuv
  # darvozasi (11) — ikkalasi ham ro'yxat testi: yangi jadval yoki yangi
  # viewset qo'shilganda qizaradi. Aynan shu xato turi ko'zdan qochadi.
  step "tez · qo'riqchilar (RLS, yozuv darvozasi)" \
      pytest apps/core/tests/test_rls.py apps/subscriptions/tests/test_gate_coverage.py -q # 10 s

  cd "$ROOT/frontend" || exit 1
  step "tez · lint"                    npm run lint      # 2 s
  step "tez · typecheck"               npm run typecheck # 6 s
  # src/__tests__ — brend, a11y, format, parol, nginx yo'llari, marshrutlar.
  step "tez · qo'riqchilar + tarjima"  npx vitest run src/__tests__ src/lib/i18n # 3 s
}

# --- Tenant izolyatsiyasi alohida ---
#
# 50 soniya — har bir push uchun qimmat, lekin `main` ga push uchun
# arzon. Cross-tenant sizish bu loyihada qaytarib bo'lmaydigan yagona
# xato (CLAUDE.md), shuning uchun u hech bo'lmaganda eng muhim
# push'da tekshiriladi.
run_tenancy() {
  activate_backend
  step "tenant izolyatsiyasi"          pytest -m tenancy -q --tb=short
}

case "$SCOPE" in
  backend)  run_backend ;;
  frontend) run_frontend ;;
  fast)     run_fast ;;
  tenancy)  run_tenancy ;;
  all)      run_backend; run_frontend ;;
  *) echo "Noma'lum: $SCOPE (fast | tenancy | backend | frontend | all)"; exit 2 ;;
esac

echo
if [ ${#FAILED[@]} -eq 0 ]; then
  printf '%sBARCHA DARVOZALAR O'\''TDI%s\n' "$GREEN$BOLD" "$OFF"
  exit 0
fi
printf '%sYIQILGAN DARVOZALAR (%d):%s\n' "$RED$BOLD" "${#FAILED[@]}" "$OFF"
printf '  · %s\n' "${FAILED[@]}"
exit 1
