# Deployment

The reviewed deployment path of [ADR-005](../architecture/adr-005-deployment.md): one Oracle
Cloud Always Free VM in Saudi Arabia running `deploy/compose.yaml`. CI never deploys; a
person runs these steps on the VM. Commands that start with `sudo` or `docker` run on the
VM over SSH.

## 1. Account and VM (Oracle Cloud console, once)

1. Sign up for Oracle Cloud Free Tier. Choose the home region **Saudi Arabia Central
   (Riyadh)**, or **Saudi Arabia West (Jeddah)** if Riyadh is not offered. The home region
   cannot change later, and Always Free compute exists only there
   ([Free Tier](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm)).
2. Upgrade the account to Pay As You Go, and create a budget with an alert at $1
   (Billing & Cost Management → Budgets). Always Free resources stay free; the alert
   catches anything that is not.
3. Networking → Virtual cloud networks → Start VCN Wizard → "Create VCN with Internet
   Connectivity". In the public subnet's default security list, add ingress rules from
   `0.0.0.0/0` for TCP 80, TCP 443 and UDP 443 (TCP 22 is already there).
4. Compute → Instances → Create instance:
   - Image: Canonical Ubuntu 24.04, the aarch64 build.
   - Shape: `VM.Standard.A1.Flex`, 2 OCPUs, 12 GB memory (the whole Always Free A1
     allowance). If the console reports no capacity, try another availability domain or
     try again later.
   - Networking: the VCN's public subnet, with a public IPv4 address.
   - Boot volume: 100 GB.
   - SSH keys: paste your public key.
5. Note the instance's public IP address.

## 2. Hostname

Until a domain is bought, use a free DuckDNS subdomain, which has its own Let's Encrypt
limits (ADR-005). Sign in at [duckdns.org](https://www.duckdns.org/), add a subdomain, and
set its address to the instance's public IP. With a bought domain, create an `A` record
for the host instead. If the public IP ever changes, update the record.

## 3. Host setup (on the VM, once)

Oracle's Ubuntu images ship host firewall rules that reject everything but SSH. Open the
web ports before Docker is installed, so the saved rules hold only the host's own rules:

```bash
sudo iptables -I INPUT 1 -p tcp -m multiport --dports 80,443 -m conntrack --ctstate NEW -j ACCEPT
sudo iptables -I INPUT 1 -p udp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

Install Docker Engine and the Compose plugin from Docker's apt repository
([Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)):

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"   # then log out and back in
```

Get the code and block container traffic to the instance metadata service (ADR-005):

```bash
sudo mkdir -p /srv/saudi-api && sudo chown "$USER": /srv/saudi-api
git clone https://github.com/malsabbagh05/saudi-api.git /srv/saudi-api/app
sudo cp /srv/saudi-api/app/deploy/saudi-api-egress.service /etc/systemd/system/
sudo systemctl enable --now saudi-api-egress
sudo iptables -S DOCKER-USER   # shows: -A DOCKER-USER -d 169.254.0.0/16 -j DROP
```

Create the settings file from the example and fill in `SITE_ADDRESS`, `ACME_EMAIL`,
`POSTGRES_PASSWORD` (`openssl rand -hex 32`) and `CHECK_REGION`:

```bash
install -m 600 /srv/saudi-api/app/deploy/env.production.example /srv/saudi-api/.env.production
nano /srv/saudi-api/.env.production
```

## 4. Deploy or update

Deploy a commit of `main`, and note its SHA:

```bash
cd /srv/saudi-api/app
git fetch origin && git checkout --detach origin/main && git rev-parse --short HEAD
docker compose --env-file /srv/saudi-api/.env.production -f deploy/compose.yaml up -d --build
```

The first build on the VM takes several minutes. `release` applies the migrations and syncs
the catalogue before `api` and `worker` start (ADR-002); Caddy obtains the certificate on
the first request to the hostname. An update is the same three commands: a short outage
while the containers restart. Migrations only move forward, so a bad release is fixed by
deploying a corrected commit, not by checking out an older one.

## 5. Verify

Replace `HOST` with `SITE_ADDRESS`:

```bash
curl -fsS https://HOST/healthz
curl -fsS https://HOST/readyz
curl -fsS "https://HOST/v1/search?q=gastat" | head -c 300; echo
curl -fsS https://HOST/llms.txt | head -5
curl -fsS -X POST https://HOST/mcp -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | head -c 300; echo
docker compose --env-file /srv/saudi-api/.env.production -f deploy/compose.yaml ps
```

Open `https://HOST/en` and `https://HOST/ar` in a browser. `/v1/stats` shows the latest job
runs once the worker has run them.

## 6. Operate

- Logs: `docker compose --env-file /srv/saudi-api/.env.production -f deploy/compose.yaml logs -f --tail 100 api`
  (or `worker`, `web`, `caddy`, `db`). Each service keeps at most three 10 MB files.
- Run a job now: `docker compose --env-file /srv/saudi-api/.env.production -f deploy/compose.yaml exec api saudi-api jobs run all`.
- Database diagnosis starts from `pg_stat_statements` (`docs/development/database.md`):
  `docker compose --env-file /srv/saudi-api/.env.production -f deploy/compose.yaml exec db psql -U saudi_api -d saudi_api`.
- Idle reclamation: Oracle can stop an Always Free instance that stays idle for 7 days
  ([Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)).
  If the instance shows as stopped, start it in the console; every service restarts on
  its own (`restart: unless-stopped`).
- Recovery: the database holds no state of its own (ADR-005). If its volume is lost, run
  the deploy command again (release rebuilds the catalogue projection), then run the jobs.
- Never run `docker compose down -v` here: it deletes the database and certificate volumes
  (`AGENTS.md`, "Development environment").
