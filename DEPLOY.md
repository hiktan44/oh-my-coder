# Coolify'a Deploy Etme

Bu repo zaten Coolify için hazır. Tek yapman gereken Coolify panelinde aşağıdaki 5 adımı izlemek.

## Hazır olan şeyler
- ✅ `Dockerfile` — multi-stage, PORT env var destekli
- ✅ `.dockerignore` — gereksiz dosyalar build'e girmiyor
- ✅ FastAPI uygulaması: `src.web.app:app` portu `$PORT` veya `8080`'den dinler
- ✅ Healthcheck: `GET /` üzerinden
- ✅ GitHub repo: `https://github.com/hiktan44/oh-my-coder` (branch: `tr-full-translation`)

## Adımlar — Coolify UI

1. **Yeni Resource → Public Repository (veya Private with PAT)**
2. Repository URL: `https://github.com/hiktan44/oh-my-coder`
3. Branch: `tr-full-translation`
4. Build Pack: **Dockerfile** (otomatik tespit edilir)
5. **Environment Variables** (Settings → Environment):
   ```
   GLM_API_KEY=76d29fcdb04e405fa43b3880bf174753.JtR3J6oqxtcP4va6
   DEFAULT_MODEL=glm
   PORT=8080
   # Opsiyonel (ücretli):
   # GEMINI_API_KEY=<aistudio.google.com/apikey adresinden al>
   ```
6. **Port**: `8080` (Coolify otomatik proxy'ler)
7. **Deploy** → bir kahve ☕

## Adımlar — API üzerinden (Coolify URL'in `$COOLIFY_URL` olsun)

```bash
TOKEN="12|G4tKL4H7Pm09iUsjRnhAL29YoMP7C32XI0vrNuHGed786d33"
COOLIFY_URL="https://coolify.senin-domain.tld"  # ← buraya kendi panel adresin

# 1) Mevcut server'ı bul
curl -sS -H "Authorization: Bearer $TOKEN" "$COOLIFY_URL/api/v1/servers" | jq

# 2) Mevcut project'i bul (veya yenisini oluştur)
curl -sS -H "Authorization: Bearer $TOKEN" "$COOLIFY_URL/api/v1/projects" | jq

# 3) Yeni public-repo uygulaması oluştur
curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "$COOLIFY_URL/api/v1/applications/public" -d '{
    "project_uuid": "<projectten alacağın uuid>",
    "server_uuid":  "<serverdan alacağın uuid>",
    "environment_name": "production",
    "git_repository": "https://github.com/hiktan44/oh-my-coder",
    "git_branch": "tr-full-translation",
    "build_pack": "dockerfile",
    "ports_exposes": "8080",
    "name": "oh-my-coder",
    "instant_deploy": true
  }'

# 4) Env'leri ekle (application uuid'sini yanıttan al)
APP_UUID="<uygulamadan dönen uuid>"
for KV in "GLM_API_KEY=76d29fcdb04e405fa43b3880bf174753.JtR3J6oqxtcP4va6" \
          "DEFAULT_MODEL=glm" "PORT=8080"; do
  K=${KV%%=*}; V=${KV#*=}
  curl -sS -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    "$COOLIFY_URL/api/v1/applications/$APP_UUID/envs" \
    -d "{\"key\":\"$K\",\"value\":\"$V\",\"is_preview\":false}"
done

# 5) Deploy tetikle
curl -sS -X POST -H "Authorization: Bearer $TOKEN" \
  "$COOLIFY_URL/api/v1/deploy?uuid=$APP_UUID"
```

## Deploy sonrası

- Web UI: `https://<coolify-uygulamasının-domaini>/`
- API dokümanı: `https://<domain>/docs` (FastAPI Swagger)
- Healthcheck: `GET /` → 200 OK

## Notlar

- **GLM anahtarı zaten env'de** — Coolify'a koyduğun anda hazır.
- **Gemini opsiyonel**: ücretli, eklemek için `GEMINI_API_KEY` ekle.
- **Branch `main`'e merge**: hazır olunca `gh pr create --base main --head tr-full-translation` ile PR aç, merge et, Coolify'da branch'i `main` yap.
- **Volume mount önerisi**: persistent state için `/app/.omc` ve `/root/.omc` dizinlerini Coolify volume'a bağla.
