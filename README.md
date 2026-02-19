# WhatsApp AI Agent Manager — SaaS

SaaS multi-tenant para gerenciar e configurar Agentes de IA para WhatsApp usando a WhatsApp Cloud API oficial e OpenRouter.

---

## Estrutura de Diretórios

```
emme-tech/
├── public/                    # Web root (Nginx aponta aqui)
│   ├── index.php              # Front controller
│   └── assets/
│       ├── css/app.css
│       └── js/app.js
├── app/
│   ├── Config/config.php      # Carrega .env e constantes
│   ├── Core/
│   │   ├── App.php            # Router / dispatcher
│   │   ├── DB.php             # PDO wrapper
│   │   ├── Auth.php           # Autenticação (admin/tenant)
│   │   ├── CSRF.php           # Proteção CSRF
│   │   ├── Session.php        # Gerenciamento de sessão
│   │   ├── Request.php        # Wrapper HTTP request
│   │   └── Response.php       # Helpers de response
│   ├── Lib/
│   │   ├── OpenRouter.php     # Cliente OpenRouter (cURL)
│   │   ├── WhatsApp.php       # Cliente WhatsApp Cloud API
│   │   ├── Stripe.php         # Integração Stripe
│   │   ├── Crypto.php         # AES-256-GCM encrypt/decrypt
│   │   ├── Chunker.php        # Chunking de documentos
│   │   ├── Retriever.php      # FULLTEXT retrieval RAG
│   │   ├── Logger.php         # Logger de arquivo
│   │   └── AuditLog.php       # Audit trail
│   ├── Controllers/
│   │   ├── Admin/             # Painel superadmin
│   │   ├── App/               # Dashboard do cliente/tenant
│   │   └── Webhook/           # WhatsApp + Stripe webhooks
│   ├── Views/
│   │   ├── layouts/           # Layouts HTML (admin, app, auth)
│   │   ├── admin/             # Views admin
│   │   └── app/               # Views cliente
│   └── Jobs/
│       └── ProcessInbound.php # Job de processamento de mensagens
├── bin/
│   ├── cron-runner.php        # Executa jobs da fila
│   ├── cron-scheduler.php     # Gera jobs para cron_jobs
│   ├── outbox-sender.php      # Envia mensagens do outbox
│   └── create-admin.php       # Cria superadmin inicial
├── storage/
│   ├── logs/                  # Logs da aplicação
│   ├── uploads/               # Documentos enviados
│   └── cache/
├── database/
│   └── schema.sql             # Schema completo do banco
├── .env.example
└── README.md
```

---

## Instalação no VPS Hostinger (Nginx + PHP-FPM + MySQL)

### 1. Requisitos

- Ubuntu 22.04 LTS (ou similar)
- Nginx 1.18+
- PHP 8.1+ com extensões: `pdo_mysql`, `curl`, `mbstring`, `json`, `openssl`, `fileinfo`
- MySQL 8.0+ ou MariaDB 10.5+

### 2. Clonar o repositório

```bash
cd /var/www
git clone https://github.com/seu-usuario/emme-tech.git
cd emme-tech
```

### 3. Configurar permissões

```bash
chown -R www-data:www-data /var/www/emme-tech
chmod -R 755 /var/www/emme-tech
chmod -R 775 /var/www/emme-tech/storage
```

### 4. Configurar .env

```bash
cp .env.example .env
nano .env
```

Preencha todos os valores. Para gerar a MASTER_KEY:

```bash
php -r "echo bin2hex(random_bytes(32));"
```

### 5. Criar banco de dados

```sql
CREATE DATABASE whatsapp_saas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'whatsapp_user'@'localhost' IDENTIFIED BY 'SuaSenhaForte';
GRANT ALL PRIVILEGES ON whatsapp_saas.* TO 'whatsapp_user'@'localhost';
FLUSH PRIVILEGES;
```

```bash
mysql -u whatsapp_user -p whatsapp_saas < /var/www/emme-tech/database/schema.sql
```

### 6. Configurar Nginx

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    root /var/www/emme-tech/public;
    index index.php;

    client_max_body_size 20M;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/run/php/php8.1-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        include fastcgi_params;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Bloquear acesso direto fora de public/
    location ~ /\. { deny all; }
}
```

```bash
nginx -t && systemctl reload nginx
```

### 7. Criar superadmin

```bash
php /var/www/emme-tech/bin/create-admin.php
```

Ou passe argumentos:

```bash
php /var/www/emme-tech/bin/create-admin.php --email=admin@seu.com --password=SenhaForte123 --name="Admin"
```

---

## Configurar Webhook WhatsApp Cloud API

1. No [Meta Developer Console](https://developers.facebook.com), acesse seu App → WhatsApp → Configuration.
2. Em **Webhook URL**, coloque: `https://yourdomain.com/webhook/whatsapp`
3. Em **Verify Token**, coloque o valor de `WA_VERIFY_TOKEN` do seu `.env`.
4. Assine o campo **messages**.
5. No `.env`, configure `WA_APP_SECRET` com o App Secret do seu Meta App.

Cada agente tem seu próprio `phone_number_id` e `access_token` que são configurados no dashboard do cliente.

---

## Configurar OpenRouter Token (tenant)

1. O cliente acessa o dashboard: **Configurações → OpenRouter Token**.
2. Cola o token `sk-or-v1-...` obtido em [openrouter.ai/keys](https://openrouter.ai/keys).
3. O token é criptografado com AES-256-GCM antes de ser salvo no banco.
4. O Admin pode visualizar modelos disponíveis em **Admin → Modelos**.

---

## Configurar Stripe

1. No [Stripe Dashboard](https://dashboard.stripe.com), crie os Products e Prices para seus planos.
2. Configure no `.env`:
   - `STRIPE_SECRET_KEY` — chave secreta (sk_live_...)
   - `STRIPE_PUBLISHABLE_KEY` — chave pública (pk_live_...)
   - `STRIPE_WEBHOOK_SECRET` — segredo do webhook (whsec_...)
3. No Stripe, configure um Webhook endpoint apontando para: `https://yourdomain.com/webhook/stripe`
4. Selecione os eventos:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. No painel Admin → Planos, vincule cada plano ao respectivo `stripe_price_id`.

---

## Configurar Cron (3 entradas)

Edite o crontab do sistema:

```bash
crontab -e -u www-data
```

Adicione:

```cron
# Executa jobs da fila (ProcessInbound, etc.) — a cada minuto
* * * * * php /var/www/emme-tech/bin/cron-runner.php >> /var/www/emme-tech/storage/logs/cron-runner.log 2>&1

# Gera execuções dos cron_jobs configurados pelos clientes — a cada minuto
* * * * * php /var/www/emme-tech/bin/cron-scheduler.php >> /var/www/emme-tech/storage/logs/cron-scheduler.log 2>&1

# Envia mensagens do outbox — a cada minuto
* * * * * php /var/www/emme-tech/bin/outbox-sender.php >> /var/www/emme-tech/storage/logs/outbox-sender.log 2>&1
```

---

## Como criar Planos, Modelos e liberar ao cliente

### Planos
1. Admin → Planos → Novo Plano.
2. Configure `max_agents`, `max_crons`, `max_docs`, features, preço.
3. Vincule o `stripe_price_id` ao plano.

### Modelos (catálogo)
1. Admin → Modelos → Novo Modelo.
2. Informe o `model_id` do OpenRouter (ex: `openai/gpt-4o-mini`).
3. Ative o modelo (`is_active = 1`).
4. O cliente poderá selecionar o modelo ao criar/editar um agente.

---

## Como o cliente assina e cria agentes

1. Cliente acessa `/app/login` e se registra (ou é criado pelo admin).
2. Em **Assinatura**, clica em "Assinar" e escolhe o plano.
3. É redirecionado ao Stripe Checkout.
4. Após pagamento, o webhook Stripe atualiza o status do tenant.
5. Cliente acessa **Agentes → Novo Agente**.
6. Configura: nome, modelo, persona, tokens WhatsApp.
7. Segue o checklist de onboarding: WhatsApp → Persona → Docs → Testar.

---

## Segurança

- Senhas com `password_hash(PASSWORD_BCRYPT)`
- Tokens criptografados com AES-256-GCM (`MASTER_KEY`)
- CSRF em todos os formulários POST
- Sessões com cookie `HttpOnly; Secure; SameSite=Strict`
- Validação de assinatura no webhook WhatsApp (`X-Hub-Signature-256`)
- PDO com prepared statements em todas as queries
- Upload restrito a extensões permitidas + validação MIME

---

## Variáveis de ambiente obrigatórias

| Variável | Descrição |
|---|---|
| `MASTER_KEY` | Chave AES-256 (64 hex chars) |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS` | Banco de dados |
| `WA_VERIFY_TOKEN` | Token de verificação do webhook WA |
| `WA_APP_SECRET` | App Secret Meta para validar assinatura |
| `STRIPE_SECRET_KEY` | Chave secreta Stripe |
| `STRIPE_WEBHOOK_SECRET` | Segredo do webhook Stripe |
| `APP_URL` | URL pública da aplicação |
