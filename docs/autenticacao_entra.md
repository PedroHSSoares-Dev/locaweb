# Autenticação e autorização com Microsoft Entra ID

O Predictfy separa autenticação de autorização:

1. a SPA React autentica a conta Microsoft com MSAL e PKCE;
2. a SPA solicita um access token destinado à API Predictfy;
3. o FastAPI valida assinatura, emissor, audiência, versão, cliente e scope;
4. no primeiro login, o e-mail validado encontra um convite pendente e o
   cadastro é vinculado ao par imutável `tid + oid` da Microsoft;
5. a partir daí, o PostgreSQL/Supabase decide se o usuário está ativo e se é
   `member` ou `admin`;
6. a API emite uma sessão curta usada pela dashboard, pelo chatbot e, quando
   autorizado, pela área `/admin`.

`ALLOWED_EMAILS=pedrohssoares@live.com` é apenas o bootstrap idempotente do
proprietário inicial. Novos usuários são criados pela tela administrativa.

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

`common` é necessário neste MVP porque a conta proprietária `@live.com` é uma
conta Microsoft pessoal. Autenticar na Microsoft não concede acesso por si só:
o par `tid + oid` também precisa estar ativo no diretório do Predictfy.

## 4. Produção

Adicione a URL publicada como Redirect URI do tipo SPA e substitua `VITE_ENTRA_REDIRECT_URI`. Configure todas as variáveis no serviço de deploy. Os IDs de aplicação são públicos; segredos da API e `CHAT_SESSION_SECRET` permanecem somente no backend.

Para restringir tenants no futuro, preencha `ENTRA_ALLOWED_TENANT_IDS` com IDs separados por vírgula. Isso só deve ser feito depois de remover contas pessoais do diretório autorizado ou incluir explicitamente o tenant Microsoft de consumidores.

## Verificações implementadas

- `/api/health` permanece público para healthcheck;
- `POST /api/chat/session` aceita somente access token Entra válido;
- os demais endpoints `/api/*` exigem sessão Predictfy;
- a autorização dinâmica, o status e a `session_version` são reavaliados no
  banco em toda requisição, permitindo revogação imediata;
- alterações de papel, desativação, remoção e logout invalidam sessões emitidas;
- o proprietário bootstrap não pode ser rebaixado, desativado ou removido;
- membros recebem `403` em `/api/admin/*`, mesmo que tentem chamar a API fora da interface;
- convites e mudanças de acesso são registrados em `user_access_audit`;
- tokens de outro público, outro aplicativo cliente, sem scope ou fora da validade são rejeitados.

## Diretório e papéis

- `member`: dashboards, histórico persistente e agente AIOps;
- `admin`: tudo de `member` mais gestão de usuários e consulta da auditoria;
- `pending`: convite criado, ainda sem identidade Microsoft vinculada;
- `active`: acesso liberado;
- `disabled`: acesso e sessões bloqueados, com histórico preservado.

O e-mail é usado somente para localizar o convite inicial. Depois do binding,
uma conta guest, corporativa ou pessoal com o mesmo texto de e-mail não herda o
acesso de outra identidade Microsoft.
