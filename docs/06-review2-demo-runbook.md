# Review-II demo runbook — 3 October 2026

Everything below has been run and verified on 28 Sep 2026. Follow it top to bottom.

---

## PART 0 — The night before

1. Charge the laptop. Carry the charger. Docker plus two Python processes will drain it.
2. **Record a backup video** of the whole demo (Win + Alt + R, or OBS). If Docker misbehaves
   in the room you play the video and keep talking. Do not skip this.
3. Take screenshots of: the two chat windows side by side, the Ops Console with the
   graphs, the green CI run on GitHub, and `docker compose ps` showing four healthy
   containers. Put them in the slide deck as backup slides at the end.
4. Do one full dry run of Part 1 and Part 2 end to end, timed. It should take under three
   minutes of setup.

---

## PART 1 — Setup in the room (do this while the previous team presents)

### Step 1 — Start Docker Desktop

Open Docker Desktop from the Start menu. Wait until the whale icon in the system tray
stops animating and the dashboard's bottom-left **Engine** indicator is green. This takes
30–60 seconds on a cold boot. Nothing below works until it is green.

### Step 2 — Free port 5000

Your 2-tier mini-project container auto-starts with Docker and holds port 5000.

```powershell
docker stop flask-app
```

If it says "No such container", fine — it is already gone. To put it back after the
review: `docker start flask-app`.

### Step 3 — Bring the stack up

```powershell
cd D:\major-project-3-tier-app\docker
docker compose up -d
```

**No `--build`.** The images are already built; building takes several minutes and you do
not have them. `up -d` starts the existing images in about 15 seconds.

### Step 4 — Confirm everything is healthy

```powershell
docker compose ps
```

Expected — four services, all `Up ... (healthy)`:

```
NAME             STATUS                   PORTS
docker-app-1     Up 20 seconds (healthy)  0.0.0.0:5000->5000/tcp
docker-app2-1    Up 20 seconds (healthy)  0.0.0.0:5001->5000/tcp
docker-db-1      Up 25 seconds (healthy)  0.0.0.0:5432->5432/tcp
docker-redis-1   Up 25 seconds (healthy)  0.0.0.0:6379->6379/tcp
```

If `app` or `app2` says `starting`, wait 10 seconds and run it again. They wait for the
database healthcheck before booting.

### Step 5 — Prove the tiers are up from the terminal

```powershell
curl http://localhost:5000/health
curl http://localhost:5000/ready
curl http://localhost:5001/ready
```

Expected:

```json
{"service":"three-tier-chat","status":"healthy"}
{"database":"healthy","redis":"healthy","status":"healthy"}
{"database":"healthy","redis":"healthy","status":"healthy"}
```

That third response is worth pausing on in the demo — it is one instance confirming it can
reach both the other two tiers.

### Step 6 — Open the two browser windows

- **Window A (normal Chrome):** `http://localhost:5000`
- **Window B (Chrome incognito, Ctrl+Shift+N):** `http://localhost:5001`

They must be different browser profiles. The same browser shares the session cookie, and
both windows would log in as the same user.

Log in (or register, first time only):

| Window | URL | Username | Note |
|---|---|---|---|
| A | localhost:5000 | `rohit` | must be exactly this — it is the admin allow-list, it unlocks the Ops Console buttons |
| B | localhost:5001 | `sai` | any name |

Password: anything you will remember. Both join the **general** room.

Arrange the two windows side by side so both are visible at once. Enter the room in both.

### Step 7 — Smoke test before you present

Type one message in each window and confirm it appears in the other, with a different
`via <id>` tag under each. If that works, the demo works. Clear the messages or just leave
them; they are harmless.

---

## PART 2 — What to show, in order

Total: 6–8 minutes. Keep the terminal and Docker Desktop on one virtual desktop and the
two browsers on another, or use Alt+Tab — decide before you start.

### Demo 1 — The architecture is really three tiers (45 s)

Show **Docker Desktop → Containers**. Four containers: two application, one PostgreSQL,
one Redis.

> "This is the three-tier architecture running locally — web tier, two application
> instances, and the data tier. On AWS these become the load balancer, the Auto Scaling
> Group in private subnets, and RDS plus ElastiCache in isolated subnets. The topology is
> identical; only the substrate differs."

### Demo 2 — Cross-instance message delivery (2 min) ← **the centrepiece**

Point at the two browser windows and say which port each is on.

Type in Window A: **"hello from instance one"**. It appears in both windows.

> "Two independent application instances. They share no memory. The message went from
> instance one, into Redis, out to instance two. That `via` tag under each message is the
> container ID that served it — different in each window, which is how you know these are
> genuinely separate processes."

Type a reply in Window B. It crosses back.

> "This is the problem stateless examples hide. A WebSocket chat breaks the moment you put
> a second instance behind a load balancer, because the connection lives on one instance
> and the message arrives on another. Solving it is why we chose this workload."

Then the number:

> "We measured it: 30 of 30 probe messages delivered, mean 18.45 ms, and a 200-message
> burst delivered 200 of 200 at 288 messages per second with no loss."

### Demo 3 — The Ops Console (2 min)

In Window A (logged in as `rohit`), open the Ops Console panel.

Show, in this order:

1. **Live telemetry** — CPU, memory, uptime, connections, messages per minute. Real values
   read from the process, updating every 3 seconds.
2. **The two graphs** — CPU per server with the 70 % scale-out and 30 % scale-in threshold
   lines drawn on it, and the traffic/latency chart.
3. **Press "Spike CPU."** Watch the CPU line climb toward the 70 % line.
4. **Press "Burst messages."** Watch the traffic line jump and messages flood both chat
   windows.

> "The panel reads real telemetry. Where it needs AWS — the Auto Scaling Group view, the
> scale and heal buttons — it says the data is unavailable rather than inventing a number.
> That was deliberate. On AWS those same buttons drive the real Auto Scaling Group."

If they ask about the CPU spike: it runs as a **child process**, because burning CPU
inside the eventlet worker would block the event loop, drop every WebSocket and fail the
health check — the Auto Scaling Group would then kill the very instance you are
demonstrating.

### Demo 4 — Dependency failure, live (1.5 min) ← **the strongest moment**

In the terminal:

```powershell
docker stop docker-redis-1
```

Now type a message in Window A. It appears in Window A. **It does not reach Window B.**

```powershell
curl http://localhost:5000/health
curl http://localhost:5000/ready
```

`/health` returns 200. `/ready` returns 503.

> "The load balancer matches only 200, so the instances stay in service — a cache blip
> does not cause the Auto Scaling Group to replace the whole fleet. `/ready` reports the
> degradation to operators instead. That split was one of the defects we found and fixed.
>
> But measuring it taught us something we did not expect. With Redis down, `/health`
> answers 200 — after 7.5 seconds. The load balancer's health-check timeout is 5 seconds,
> and a probe that exceeds it is a failure whatever status it would eventually return. So
> the fix is necessary but not sufficient. We have recorded that as an open defect."

Bring it back:

```powershell
docker start docker-redis-1
```

Messages cross again after a few seconds — and that delay is defect D8, the readiness
probe reporting success before the subscriber has re-subscribed. Measured at 1.2 s after a
5 s outage and 14.5 s after a 45 s outage.

### Demo 5 — The engineering behind it (1 min)

```powershell
cd D:\major-project-3-tier-app
git log --oneline -8
```

Then open GitHub Actions in a browser tab and show the green run.

> "168 tests, all passing — 28 for the application and 140 asserting over the Terraform
> modules. Checkov runs enforcing, not soft-fail: 96 passed, 0 failed, 32 skips each with
> a written justification. Every commit runs all of it."

---

## PART 3 — Saying the honest part well

You are showing the application, not the AWS deployment. Say so plainly and early — do
not let them discover it.

> "What you are seeing runs on Docker locally. The AWS deployment is Stage-II. The
> infrastructure is fully written — eight Terraform modules, `terraform validate` and
> `terraform plan` both clean, policy scan enforcing and green — but we have not applied
> it to a live account yet.
>
> We made that choice deliberately. Running the application locally first found three
> defects, two of which stopped it from starting at all. Those would have cost us days of
> debugging against live infrastructure, on the meter. Finding them on a laptop cost an
> evening."

That reframes the missing piece as a decision rather than a gap. It is also true.

### Questions they will ask

**"Why haven't you deployed to AWS?"**
> Cost and sequence. The infrastructure code is complete and verified; applying it is
> Stage-II. We chose to validate the application against real dependencies first, and that
> decision paid for itself — see the three defects.

**"How do you know the Terraform actually works?"**
> `terraform validate` and `plan` are clean, 140 unit tests assert over the module
> configuration, and Checkov runs enforcing. We are also explicit in the paper that none of
> that proves it will run — that is the paper's central claim, and eleven defects that
> passed every gate are the evidence.

**"Is this just the 2-tier project again?"**
> No. That one was two tiers with a simulated panel. This is three tiers with routing-level
> database isolation, security-group chaining that survives Auto Scaling, runtime credential
> injection, and a panel reading real telemetry — and real measurements behind every number.

**"What if the demo fails?"**
> Play the backup video. Keep narrating over it as if live.

---

## PART 4 — After the review

```powershell
cd D:\major-project-3-tier-app\docker
docker compose down          # stops the stack, keeps the database volume
docker start flask-app       # put the 2-tier mini-project back on port 5000
```

Use `docker compose down -v` only if you want to wipe the database and start clean —
you will have to register the users again.

---

## PART 5 — What is left, and what comes next

### Before 3 October

| # | Item | Status |
|---|---|---|
| 1 | Apply the corrections in [05-document-corrections.md](05-document-corrections.md) to the paper | **not started** |
| 2 | Tell the professor the paper's figures have changed, before submission | **not started** |
| 3 | Same corrections to report Chapter 5 and PPT slides 3, 10, 11, 13 | **not started** |
| 4 | Change the "D3 fix verified" slide to "necessary but not sufficient" | **not started** |
| 5 | Commit `docs/02-research-paper-review2.md` and the new docs | **not started** |
| 6 | Full timed dry run + backup video + screenshots | **not started** |
| 7 | Paper submission proof (deadline 25-09-2026 — confirm where this stands) | **check** |

Items 1–4 are the ones with a real deadline attached, because the paper is with the
professor now and the figures in it were never measured.

### Stage-II — the AWS deployment

1. **Deploy.** `terraform apply` into a real account: VPC across two availability zones,
   ALB, Auto Scaling Group, RDS, ElastiCache, Secrets Manager.
2. **Fix the three open defects.**
   - **D6** — enable detailed monitoring so the 120 s alarm period and the metric
     resolution agree, otherwise scale-out fires late or not at all.
   - **D7** — publish the container image from the pipeline and pin it by commit SHA, so
     the launch template references something that exists.
   - **D8** — make the readiness probe publish a token to a self-addressed channel and
     require it back, so readiness tracks the subscriber rather than the socket.
   - **D11** — bound the dependency check inside `/health` so it answers within the load
     balancer's 5 s timeout whatever the dependency is doing.
3. **Measure on AWS what was measured locally** — cross-instance latency over real
   network hops, scale-out time under the CPU spike, failover time when an instance is
   terminated, and actual cost against the Table III estimates.
4. **Harden.** TLS on the load balancer, deployment credentials moved to OIDC federated
   identity instead of long-lived keys, and the 32 justified Checkov skips reduced.
5. **Replace static module assertions with behavioural tests** — apply the modules into a
   throwaway environment in CI and assert on what actually came up. This is the direct
   answer to the paper's own finding: static tests over configuration cannot catch the
   defects that matter.
6. **Final artefacts** — Stage-II report, the deployed-system paper, and the Review-III
   presentation.

The measurement work in item 3 is what turns the Stage-II paper from a description into a
result. Everything else supports it.
