# Live access

## Public demo (Cloudflare tunnel)

While the local server + tunnel are running:

**https://poem-hampton-scientific-bosnia.trycloudflare.com**

- UI: `/`
- Swagger: `/docs`
- Health: `/health`

> Quick tunnels are temporary. If the URL stops working, re-run:
>
> ```bash
> uvicorn app.main:app --host 0.0.0.0 --port 8000
> cloudflared tunnel --url http://127.0.0.1:8000
> ```

## Permanent hosting options

1. **Render** — click New → Blueprint with `render.yaml` in this repo  
2. **Docker** — `docker build -t ai-quality-lab . && docker run -p 8000:8000 ai-quality-lab`

## Local

http://127.0.0.1:8000
