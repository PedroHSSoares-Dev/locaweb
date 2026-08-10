# Autenticação com Microsoft Entra ID

O Predictfy usa o Entra apenas para comprovar a identidade. Não existem roles nesta fase:

1. a SPA React autentica a conta Microsoft com MSAL e PKCE;
2. a SPA solicita um access token destinado à API Predictfy;
3. o FastAPI valida assinatura, emissor, audiência, versão, cliente e scope;
4. o e-mail validado pelo Entra precisa existir em `ALLOWED_EMAILS`;
5. a API emite uma sessão curta usada pela dashboard e pelo chatbot.

Atualmente a allowlist inclui `pedrohssoares@live.com`.

## 1. Registrar a API

No portal Microsoft Entra, abra **App registrations → New registration**:

- nome: `Predictfy API`;
- tipos de conta: **Accounts in any organizational directory and personal Microsoft accounts**;
- Redirect URI: deixe vazio.

Copie o **Application (client) ID**. Em **Expose an API**:

- defina o Application ID URI como `api://<API_CLIENT_ID>`;
- crie o scope delegado `access_as_user`;
- permita consentimento de administradores e usuários;
- confirme no Manifest que os access tokens aceitos são v2 (`requestedAccessTokenVersion: 2`).

## 2. Registrar a SPA

Crie outro App registration:

- nome: `Predictfy Web`;
- mesmos tipos de conta, incluindo contas Microsoft pessoais;
- plataforma: **Single-page application (SPA)**;
- Redirect URI local, do tipo SPA: `http://localhost:5173/auth-redirect.html`.

Em **API permissions**, adicione a permissão delegada:

```text
Predictfy API / access_as_user
```

Não crie client secret: uma SPA é um cliente público e usa Authorization Code + PKCE.

## 3. Preencher a configuração local

Na raiz, em `.env`:

```dotenv
CHAT_ALLOW_LOCAL_DEV=false
ALLOWED_EMAILS=pedrohssoares@live.com
ENTRA_TENANT_ID=common
ENTRA_API_CLIENT_ID=<client-id-do-Predictfy-API>
ENTRA_SPA_CLIENT_ID=<client-id-do-Predictfy-Web>
ENTRA_REQUIRED_SCOPE=access_as_user
```

Em `frontend/.env.local`:

```dotenv
VITE_API_URL=http://localhost:8000/api
VITE_ENTRA_CLIENT_ID=<client-id-do-Predictfy-Web>
VITE_ENTRA_AUTHORITY=https://login.microsoftonline.com/common
VITE_ENTRA_REDIRECT_URI=http://localhost:5173/auth-redirect.html
VITE_ENTRA_API_SCOPE=api://<client-id-do-Predictfy-API>/access_as_user
```

`common` é necessário neste MVP porque a conta autorizada `@live.com` é uma conta Microsoft pessoal. A allowlist no backend impede que outras contas autenticadas obtenham acesso.

## 4. Produção

Adicione a URL publicada como Redirect URI do tipo SPA e substitua `VITE_ENTRA_REDIRECT_URI`. Configure todas as variáveis no serviço de deploy. Os IDs de aplicação são públicos; segredos da API e `CHAT_SESSION_SECRET` permanecem somente no backend.

Para restringir tenants no futuro, preencha `ENTRA_ALLOWED_TENANT_IDS` com IDs separados por vírgula. Isso só deve ser feito depois de remover contas pessoais da allowlist ou incluir explicitamente o tenant Microsoft de consumidores.

## Verificações implementadas

- `/api/health` permanece público para healthcheck;
- `POST /api/chat/session` aceita somente access token Entra válido;
- os demais endpoints `/api/*` exigem sessão Predictfy;
- a allowlist é reavaliada em toda requisição, permitindo revogação imediata;
- tokens de outro público, outro aplicativo cliente, sem scope ou fora da validade são rejeitados.
