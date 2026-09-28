# PROJECT HANDOFF — for a new Claude chat on claude.ai

> Paste or upload this file at the start of a new chat. It is self-contained: the new
> chat has no memory of earlier sessions. Snapshot date: **17-09-2026**.

---

## 1. Who and what

- **Students:** B.Tech CSE, IV-I semester, R22 regulation, 2023 batch, **CVR College of
  Engineering**, Hyderabad. Lead: Rohit Kiran P. (GitHub `Rohit-Kiran24`).
  Other team members, roll numbers, supervisor name and batch number: *not yet provided*.
- **Project title:** *Architecture and Automation of a Production-Grade Three-Tier Web
  Application on AWS Using Terraform and DevSecOps*
- **Repository (public):** https://github.com/Rohit-Kiran24/major-project-3-tier-app
- **Predecessor:** a 2-tier mini project (Flask + MySQL on EKS),
  https://github.com/Rohit-Kiran24/mini-project-2-tier-app. Different faculty evaluate
  the two projects.

---

## 2. The system in one page

**Workload:** real-time multi-room chat app (Flask 3.0, Flask-SocketIO, eventlet,
Gunicorn, PostgreSQL, Redis). Chosen because WebSocket state makes horizontal scaling
hard, unlike stateless CRUD apps.

**AWS design (region ap-south-1, 2 AZs: 1a / 1b), VPC 10.0.0.0/16**

| Tier | Subnets | Contents | Internet |
|------|---------|----------|----------|
| Presentation (public) | 10.0.1.0/24, 10.0.2.0/24 | Application Load Balancer, NAT instance | in + out |
| Application (private) | 10.0.3.0/24, 10.0.4.0/24 | EC2 Auto Scaling Group (t2.micro, min 2 / desired 2 / max 3), ElastiCache Redis 7 | out only, via NAT |
| Data (isolated) | 10.0.5.0/24, 10.0.6.0/24 | RDS PostgreSQL 15 (db.t3.micro, encrypted, gp3) | **none — no route exists** |

**Key design claims**
1. **Routing-level isolation:** the data tier's route table has no default route, so no
   security-group mistake can expose the database. A firewall permits traffic on a
   path; it cannot create one.
2. **Zero-trust security-group chain:** each tier admits only the previous tier's
   security-group ID, never a CIDR range — stays correct as auto scaling changes IPs.
3. **Runtime secrets:** random DB password → AWS Secrets Manager → fetched at container
   start via the EC2 IAM role. No password in code, config or image.
4. **Stateful scaling:** ALB sticky sessions + Redis pub/sub backplane so messages reach
   users connected to different servers.
5. **Cost as a design parameter:** `use_nat_gateway` (NAT instance ~$8.50/mo vs gateway
   ~$33/mo) and `rds_multi_az` toggles. Demo config ≈ $63/month; production ≈ $125.
   *(Indicative — must be re-checked on the AWS Pricing Calculator.)*

**Scaling:** CloudWatch alarm adds a server at CPU > 70% (2 × 120 s periods), removes one
at CPU < 30% (5 × 120 s).

**Infrastructure as Code:** 8 Terraform modules — `vpc`, `security-groups`,
`secrets-manager`, `rds`, `elasticache`, `alb`, `asg`, `monitoring` (6 alarms + SNS +
dashboard).

**Database:** 3 tables — `users`, `rooms`, `messages`. `messages.user_id` ON DELETE SET
NULL (history survives account deletion), `messages.room_id` ON DELETE CASCADE. Indexes
on `messages(room_id)`, `messages(created_at DESC)`, `(room_id, created_at DESC)`.

**CI (GitHub Actions, every push):** terraform fmt → init → validate → **Checkov
(enforcing)**; pytest (all tests) → Docker multi-stage build → Trivy scan.
**CD:** manual `deploy.yml` with plan / apply / destroy.

---

## 3. What is DONE (verified)

| Date | Work |
|------|------|
| 11–12 Jul 2026 | Full architecture, 8 modules, Flask app, Docker, CI |
| 01 Aug | 140 infrastructure unit tests; 5 deployment defects fixed |
| 04 Aug | Review-I documents written (report, paper draft, PPT guide, progress/ERP report) |
| 13 Aug | **Review-I completed** |
| 23 Aug | All tests run in CI; ASG default set to 2 servers |
| 31 Aug | Checkov made enforcing: 39 findings → 10 code fixes + 32 justified skips → **96 passed, 0 failed, 32 skipped** |
| 17 Sep | **Ops Console panel** added (commit `c27b048`) |

**Current numbers:** 168 automated tests passing (28 application + 140 infrastructure).
CI green (run #15). Checkov 96 / 0 / 32.

### Ops Console (the demo panel)
Right-hand panel on the chat page, modelled on the 2-tier project's sidebar but with
**real** data (the 2-tier panel animated fake CPU numbers):
- Tier health rows with live RDS / Redis latency; stat tiles; CPU and memory bars
- Chart 1: CPU per server with 70% / 30% threshold lines + stepped server count
- Chart 2: messages/min with DB and Redis latency
- Server cards with AWS lifecycle state; real Auto Scaling activity and alarm state
- Controls: cluster-wide CPU spike (3/5/8 min), scale ±1, self-heal, message burst
- Each live chat message shows which server handled it ("via i-0ab… · 1a")
- Light / dark toggle
- Safety: exists only when `DEMO_MODE=true`; login required; buttons only for
  `ADMIN_USERS`; spike capped at 10 min; burst capped at 200
- Spike runs in a separate process (so it can't freeze the eventlet server) and is
  broadcast to all servers via Redis (one server at 100% only averages ~50%, which never
  triggers scaling)
- docker-compose runs **two** app containers (ports 5000 and 5001) to show
  cross-server delivery locally

### Defect analysis (a key finding for the report and paper)
Defects that passed **every** automated check (fmt, validate, Checkov, all tests) but
would have broken the real deployment:

| # | Defect | Status |
|---|--------|--------|
| D1 | NAT instance used interface `enX0` (Nitro naming) on t2.micro (Xen, `eth0`); packages missing on Amazon Linux 2023 → no internet for app servers | ✅ fixed |
| D2 | Windows CRLF line endings in the EC2 boot script → "bad interpreter" | ✅ fixed |
| D3 | `/health` failed when Redis blipped → ASG would kill healthy servers | ✅ fixed (split into `/health` + `/ready`) |
| D4 | Gunicorn `preload_app` with eventlet → unpatched sockets, hangs | ✅ fixed |
| D5 | Elastic IP always allocated but unused → silent charge | ✅ fixed |
| D6 | Alarms use 120 s periods but servers have only 5-minute basic monitoring → scaling alarm fires late or never | ⚠️ **found, NOT fixed** |
| D7 | App image `rohitkiran24/three-tier-chat:latest` never published anywhere (that Docker Hub account doesn't exist) → servers can't download the app | ⚠️ **found, NOT fixed** |

**Thesis:** automated IaC tooling proves *configurational correctness* but not
*operational viability* (supports Guerriero et al., ICSME 2019).

---

## 4. What is NOT done

- **AWS never deployed** (deploy workflow run 0 times; no Terraform state).
- **App + Ops Console never run in Docker locally.**
- D6 and D7 not fixed.
- AWS-only panel features (scale, self-heal, scaling timeline) written but never
  executed against AWS; need IAM permissions and `ASG_NAME` passed to the container.
- S3 state bucket `rohit-3tier-tfstate` and DynamoDB table `terraform-lock` don't exist.
- Alert email still `alerts@example.com`.
- HTTPS not enabled; CD uses static AWS keys (OIDC planned).

---

## 5. REVIEW-II — circular requirements (Dr. M. Swami Das, project coordinator)

**Review-II: 1–3 October 2026.**

1. **Presentation:** 30 minutes, **12–15 slides maximum**.
2. **Documentation:** **Chapter 4 — Design**; **Chapter 5 — Database and Technology /
   Partial Implementation**.
3. **Project report and ERP status report signed by the supervisor.**
4. **Research paper communication proof:** paper submitted to a **Scopus-indexed journal
   or Scopus-indexed IEEE conference**, in the IEEE template, plagiarism-free.
   **Proof due to section coordinator by Friday 25-09-2026. No proof → not allowed to
   attend Review-II.**

### Status of each requirement

| Requirement | Status | Gap |
|-------------|--------|-----|
| Paper submission proof (25-09) | ❌ not started | Draft exists in markdown only; not in IEEE template; references unverified; no venue; not submitted |
| Chapter 4 Design | 🟡 partial | Architecture content exists; **no UML diagrams** |
| Chapter 5 DB & Technology / Implementation | 🟡 partial | Current chapter is outdated (says 153 tests, no Ops Console) |
| Signed report + ERP status | ❌ | Needs Review-II update, placeholders filled, signatures |
| PPT 12–15 slides | ❌ | New deck needed |
| Demo | ❌ | Local Docker run not done |

---

## 6. TO-DO checklist

### A. Research paper — HARD DEADLINE 25-09
- [ ] Meet supervisor: approve paper direction, get suggested venue
- [ ] Confirm venue is genuinely Scopus-indexed (Scopus Sources list; IEEE Xplore
      proceedings). Avoid "guaranteed publication" agents and cloned journal sites
- [ ] Update content: 168 tests, Ops Console, **7 defects (5 fixed, 2 identified)** —
      do not claim D6/D7 fixed
- [ ] Add **real measured results** from a local Docker run (latency, burst throughput,
      cross-container delivery, CPU chart screenshot)
- [ ] **Rewrite in the team's own words.** The existing draft was AI-assisted; the
      circular demands plagiarism-free work, and IEEE requires disclosing AI-generated
      content in the acknowledgements — follow the venue's policy
- [ ] Verify all 15 references by opening each one
- [ ] Put into the **IEEE conference template** (two-column) with figures
- [ ] Plagiarism check (college tool)
- [ ] **Submit by ~23-09**; save submission ID email + screenshot
- [ ] **Give proof to section coordinator by 25-09**

### B. Chapter 4 — Design
- [ ] Keep architecture, network, security, module, pipeline content
- [ ] Add UML: use case, class, sequence (cross-server message; spike → alarm → scale-out),
      activity (register/login), component (8 modules), deployment (AWS tiers/AZs), DFD

### C. Chapter 5 — Database & Technology / Partial Implementation
- [ ] 5.1 Database: ER diagram, table schemas, constraints, indexes, why PostgreSQL/RDS
- [ ] 5.2 Technology stack with justification for each choice
- [ ] 5.3 Implementation done: modules, app, Ops Console, CI; 168 tests; Checkov 96/0/32;
      screenshots
- [ ] 5.4 Defect analysis (7 found, 5 fixed, 2 in progress)
- [ ] 5.5 Pending work

### D. Signatures
- [ ] Fill all `[[placeholders]]` (names, roll numbers, supervisor, batch)
- [ ] Update ERP status report for Review-II
- [ ] Supervisor signs project report and ERP status report

### E. PPT (12–15 slides, 30 min)
1 Title · 2 Review-I recap · 3 Architecture · 4 Network & security · 5 Use case +
sequence · 6 Component + deployment · 7 Database (ER + schema) · 8 Technology stack ·
9 Implementation status · 10 CI/CD + results · 11 Ops Console + live demo ·
12 Defect analysis · 13 Paper status (venue + submission ID) · 14 Remaining work ·
15 Conclusion / Q&A
- [ ] ~20 min talk + ~10 min demo / questions; record a backup demo video

### F. Engineering (done in Claude Code, not the web chat)
- [ ] Run app locally in Docker (2 containers) → collect measurements for the paper
- [ ] Fix D6 (detailed monitoring + ASG group metrics) and D7 (publish image via CI,
      proposed: GitHub Container Registry, pinned by commit)
- [ ] IAM + `demo_mode` / `admin_users` Terraform variables for the panel
- [ ] AWS deploy — **optional before Review-II**; don't let it endanger 25-09

---

## 7. Schedule

| Dates | Work |
|-------|------|
| 17–18 Sep | Meet supervisor (venue + approval); get guidelines + IEEE template |
| 18–19 Sep | Local Docker run; collect real numbers + screenshots |
| 19–22 Sep | Rewrite paper in IEEE template; verify references; plagiarism check; supervisor review |
| by 23 Sep | **Submit paper**, save proof |
| **by 25 Sep (Fri)** | **Proof to section coordinator** |
| 26–28 Sep | Chapter 4 + Chapter 5; fix D6 / D7 |
| 29–30 Sep | PPT, 30-min rehearsal, supervisor signatures |
| 1–3 Oct | Review-II |

---

## 8. Decisions already made

- Keep the 70% / 30% scaling rule (report already describes it); "Scale now" button for speed
- Server tags on live messages only (no database migration)
- Admin access by username list (`ADMIN_USERS`)
- No database/Redis outage buttons on AWS (single-node Redis, single-AZ RDS)
- UI: dark theme with light toggle
- Image registry: GitHub Container Registry proposed (not yet confirmed)
- AWS deploy comes after local testing; budget alarm must be set first

## 9. Working preferences

- All git commits authored by Rohit only; **no AI co-author lines** in commits
- Be honest about what is verified vs. not; never overclaim novelty or results
- Cost-conscious: student budget, destroy AWS resources after demos
- References and cost figures must be verified before submission

## 10. Existing documents in the repo (`docs/`)

| File | Contents | Stale parts |
|------|----------|-------------|
| `01-project-report-stage1.md` | Ch1 Intro, Ch2 Literature survey, Ch3 Requirements, Ch4 Architecture design, Ch5 Stage-I status, Ch6 Plan, 15 references | 153 tests, 5 defects, no Ops Console, no UML |
| `02-research-paper-ieee.md` | IEEE-style paper draft | Same as above; no measured results; not in template |
| `03-presentation-guide.md` | Review-I deck plan + viva Q&A bank | Review-I format (16 slides / 15 min) |
| `04-progress-report-and-erp.md` | Progress report + ERP message drafts | Review-I dates, 153 tests |

## 11. Open questions (still needed)

1. College **Project Guidelines** and the **IEEE template** attached to the circular
2. Team member names, roll numbers, supervisor name, batch number
3. Paper venue suggested by the supervisor
4. AWS account: personal or college

---

## Suggested first message in the new chat

> I'm continuing my B.Tech major project. The attached handoff file describes the
> project, what's done, and the Review-II requirements. My most urgent deadline is
> submitting the research paper to a Scopus-indexed IEEE venue by 25-09-2026. Please
> start by helping me [restructure the paper for the IEEE template / write Chapter 4
> with UML diagrams / plan the 15-slide PPT]. The paper draft is attached as
> 02-research-paper-ieee.md.
