/**
 * TLS sertifikati oʻzi yangilanadi — zanjirning har bir halqasi.
 *
 * 2026-11-13 da topildi: sertifikat 15.12.2026 da tugaydi, yangilash
 * esa hech qachon ishlamagan. Ikki sabab: `certbot` konteyneri server
 * qayta yuklanganda qaytib turmagan (`restart` yoʻq edi), va turganida
 * ham yangi sertifikat `letsencrypt` volume'ida qolib ketardi — nginx
 * esa boshqa volume'dagi (`certs`) nusxani oʻqiydi.
 *
 * Zanjir: certbot `renew` → deploy-hook nusxani `certs` ga koʻchiradi →
 * nginx yangi faylni sezib `reload` qiladi → deploy certbot'ni har safar
 * koʻtaradi. Bitta halqa uzilsa, sayt bir kun ogohlantirishsiz yopiladi.
 */

import { execFileSync } from 'node:child_process'
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../../..')
const read = (path: string) => readFileSync(join(ROOT, path), 'utf8')

/** `compose.prod.yaml` dagi `certbot:` xizmati — keyingi xizmat yoki `volumes:` gacha. */
function certbotService(): string {
  const text = read('compose.prod.yaml')
  const start = text.indexOf('\n  certbot:\n')
  if (start < 0) throw new Error('compose.prod.yaml: certbot xizmati topilmadi')
  const rest = text.slice(start + 1)
  const end = rest.search(/\n(?: {2}[a-z_-]+:\n|[a-z_]+:\n)/)
  return end < 0 ? rest : rest.slice(0, end)
}

describe('TLS sertifikatini yangilash', () => {
  it('deploy-hook yangi sertifikatni nginx oʻqiydigan joyga koʻchiradi', () => {
    const work = mkdtempSync(join(tmpdir(), 'kg-tls-'))
    const lineage = join(work, 'live', 'radix-crm.uz')
    const out = join(work, 'out')
    mkdirSync(lineage, { recursive: true })
    mkdirSync(out)
    writeFileSync(join(lineage, 'fullchain.pem'), 'YANGI-ZANJIR')
    writeFileSync(join(lineage, 'privkey.pem'), 'YANGI-KALIT')

    execFileSync('sh', [join(ROOT, 'deploy/certbot/copy-to-nginx.sh')], {
      env: { ...process.env, RENEWED_LINEAGE: lineage, CERTS_OUT: out },
    })

    expect(readFileSync(join(out, 'fullchain.pem'), 'utf8')).toBe('YANGI-ZANJIR')
    expect(readFileSync(join(out, 'privkey.pem'), 'utf8')).toBe('YANGI-KALIT')
  })

  it('certbot qayta yuklanishdan keyin ham turadi va hook bilan yangilaydi', () => {
    const service = certbotService()
    expect(service).toMatch(/restart: unless-stopped/)
    expect(service).toMatch(/- certs:\/out\b/)
    expect(service).toMatch(/- \.\/deploy\/certbot:\/hooks:ro/)
    expect(service).toMatch(/renew[^\n]*--deploy-hook 'sh \/hooks\/copy-to-nginx\.sh'/)
  })

  it('nginx yangi sertifikatni sezib qayta yuklaydi', () => {
    const entrypoint = read('deploy/nginx/entrypoint.sh')
    const tls = entrypoint.slice(entrypoint.indexOf('HTTPS rejim'))
    expect(tls).toMatch(/-nt/)
    expect(tls).toMatch(/nginx -s reload/)
  })

  it('deploy sertifikat bor boʻlsa certbot ni ham koʻtaradi', () => {
    expect(read('scripts/deploy.sh')).toMatch(/--profile tls up -d certbot/)
  })
})
