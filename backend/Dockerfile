# syntax=docker/dockerfile:1

# --- Build bosqichi: g'ildiraklarni alohida yig'amiz ---
FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels
COPY requirements/ requirements/
ARG REQUIREMENTS=requirements/production.txt
RUN pip wheel --wheel-dir /wheels -r ${REQUIREMENTS}


# --- Runtime bosqichi ---
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Root bo'lmagan foydalanuvchi: konteyner buzilsa ham zarar doirasi tor.
RUN useradd --create-home --uid 1000 app

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements/ requirements/
ARG REQUIREMENTS=requirements/production.txt
RUN pip install --no-index --find-links=/wheels -r ${REQUIREMENTS} \
    && rm -rf /wheels

COPY --chown=app:app . .

# Statik va media kataloglari TASVIR ICHIDA, `app` nomiga yaratiladi.
#
# Ular `.dockerignore` da chiqarib tashlangan, ya'ni `COPY` ularni
# keltirmaydi. Ularsiz Docker named volume'ni ulaganda ilova
# jarayoni root emas (uid 1000), volume esa ROOT nomiga yaratiladi —
# va `collectstatic` "Permission denied" bilan yiqiladi.
#
# Docker bo'sh named volume'ni tasvirdagi mavjud katalog ustiga
# ulaganda uning MAZMUNINI VA EGASINI ko'chiradi. Shuning uchun
# kataloglarni shu yerda yaratish muammoni butunlay yo'q qiladi —
# konteynerni root qilib qo'yish yoki volume egasini qo'lda
# tuzatish kerak emas.
RUN mkdir -p /app/staticfiles /app/mediafiles \
    && chown app:app /app/staticfiles /app/mediafiles

USER app

EXPOSE 8000

# Migratsiyalar bu yerda ISHLAMAYDI — ular deploy'ning alohida qadami
# (docs/06 §9). Boot paytida migratsiya bir nechta konteyner bir vaqtda
# ko'tarilganda poyga holatiga olib keladi.
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
