# Fluxo de Dados — Autenticação

## Registro de usuário

```
POST /auth/register { email, password }
```

```mermaid
sequenceDiagram
    actor Cliente
    participant Router as auth/router.py
    participant Service as auth/service.py
    participant Repo as auth/repository.py
    participant DB as PostgreSQL

    Cliente->>Router: POST /auth/register { email, password }
    Router->>Service: register(db, email, password)
    Service->>Repo: get_by_email(db, email)
    Repo-->>Service: None (não existe)
    Service->>Repo: create(db, email, hashed_password)
    Repo->>DB: INSERT users
    DB-->>Repo: User
    Repo-->>Service: User
    Service-->>Router: User
    Router-->>Cliente: 201 { id, email }
```

## Login (JWT)

```
POST /auth/login { email, password }
```

```mermaid
sequenceDiagram
    actor Cliente
    participant Router as auth/router.py
    participant Service as auth/service.py
    participant Repo as auth/repository.py
    participant DB as PostgreSQL

    Cliente->>Router: POST /auth/login { email, password }
    Router->>Service: authenticate(db, email, password)
    Service->>Repo: get_by_email(db, email)
    Repo->>DB: SELECT users WHERE email=...
    DB-->>Repo: User
    Repo-->>Service: User
    Service->>Service: verify_password(password, user.hashed_password)
    Service-->>Router: access_token (JWT)
    Router-->>Cliente: 200 { access_token, token_type }
```

## Login via Google OAuth

O fluxo OAuth é gerenciado por `core/config/google_oauth.py`. O frontend redireciona o usuário para o endpoint do Google, que devolve um `code`. O backend troca o código pelo token e upserta o usuário.

```mermaid
sequenceDiagram
    actor Usuário
    participant Frontend
    participant Backend as auth/router.py
    participant Google

    Usuário->>Frontend: clica "Entrar com Google"
    Frontend->>Google: redirect para OAuth consent
    Google-->>Frontend: code
    Frontend->>Backend: POST /auth/google { code }
    Backend->>Google: troca code por token
    Google-->>Backend: id_token + perfil
    Backend->>Backend: upsert user (email, name)
    Backend-->>Frontend: access_token (JWT)
```

## Proteção de rotas

Rotas protegidas injetam `current_user` via `Depends(get_current_user)` definido em `core/dependencies.py`. O middleware valida o JWT e lança `401` se inválido ou expirado.
