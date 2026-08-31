# PRESENTATION & VIVA GUIDE — Review-I, 13-08-2026

Everything you need to walk in prepared: slide-by-slide deck plan, what to say on each
slide, how to map answers to the five evaluation parameters, and a question bank with
model answers.

---

## PART 1 — HOW YOU ARE BEING MARKED

The circular lists five parameters. Read them as *five questions the evaluator will
ask*, and make sure a specific slide answers each one.

| # | Parameter (CO) | The evaluator is really asking | Slide that answers it |
|---|----------------|-------------------------------|----------------------|
| 1 | Clarity of aim, motivation, novelty, innovation (CO1) | "Why does this project exist, and what is new about it?" | 3, 4, 6 |
| 2 | Problem statement, objectives, scope (CO1) | "Can you state the problem in one sentence and bound the work?" | 5, 7 |
| 3 | Literature review, gaps, requirements, documentation (CO2, CO5) | "What did you read, what was missing, and how did that shape your design?" | 8, 9, 10 |
| 4 | **Individual** motivation on problem statement (CO1) | "Why do *you personally* care about this problem?" | Asked individually — Part 4 |
| 5 | **Individual** contribution in problem formulation and identifying gaps (CO2) | "What did *you* specifically figure out?" | Asked individually — Part 4 |

**Critical:** parameters 4 and 5 are *individual*. The circular explicitly states every
member must explain the project independently. Marks are lost here more than anywhere
else, because teams rehearse the deck collectively and freeze when asked personally.
Part 4 of this document addresses that directly.

---

## PART 2 — SLIDE DECK (16 slides, 12–15 minutes)

Rule of thumb: **one idea per slide, ≤ 6 lines of text, ≥ 24 pt font.** The evaluator
reads the slide in 3 seconds and then listens to you. Slides are not the report.

---

### Slide 1 — Title
Project title · team members with roll numbers · supervisor · department · date.
**Say:** "Good morning. We are presenting Stage-I of our major project on architecting
and automating a production-grade three-tier web application on AWS."
*(15 seconds. Do not linger.)*

---

### Slide 2 — Agenda
Motivation → Problem → Objectives → Literature & Gaps → Architecture → Implementation
→ Results → Stage-II plan.
**Say:** one sentence. Move on. *(10 seconds)*

---

### Slide 3 — Motivation: where we came from
Show a small diagram of the 2-tier mini project (EKS) beside the new 3-tier design.
Four bullets — the limitations you personally hit.

**Say:** "This project didn't start from a textbook. It started from our own two-tier
mini project on EKS. Running it exposed four concrete problems: the app and database
shared one trust boundary, credentials sat in environment variables and in git history,
most of the infrastructure was created by hand in the console so we could never
recreate it identically, and nothing in our workflow checked whether a change had
exposed something publicly. Those four problems became this project."

> This slide wins parameter 1. Lived motivation always outscores generic motivation.

---

### Slide 4 — Motivation: the cost constraint
One table: NAT Gateway ≈ $33/mo vs NAT instance ≈ $8.50/mo.

**Say:** "There's a fifth motivation that's specific to being students. Reference AWS
architectures assume production budgets. A managed NAT Gateway alone is about four
times the cost of a NAT instance doing the same job for our traffic. An architecture
we can't afford to build is an architecture we can't measure or demonstrate. So we
made cost a design parameter, not an afterthought."

---

### Slide 5 — Problem Statement
The single boxed paragraph from the report, Section 1.3. Nothing else on the slide.

**Say it slowly, close to verbatim.** Then pause. This is the sentence they will grade
you on.

---

### Slide 6 — Novelty & Innovation
Four points:
1. Isolation enforced at the **routing** layer, not the firewall layer
2. Zero-trust SG chaining — no CIDR ranges between tiers
3. Runtime credential injection — nothing stored
4. Cost-parameterised: one codebase, two cost points

**Say:** "We want to be precise about what's novel. We are not claiming a new
algorithm. What is new is the *combination* and specifically the isolation argument —
most three-tier designs protect the database with security-group rules. We remove the
route entirely, so no firewall mistake can expose it. That's a strictly stronger
guarantee at zero extra cost."

> ⚠️ **Do not oversell novelty.** Claiming research novelty for an engineering project
> invites hostile questioning. Claiming a well-reasoned design contribution and
> defending it precisely scores better. Evaluators reward honesty about scope.

---

### Slide 7 — Objectives & Scope
Left column: objectives O1–O9 (condense to 6 lines). Right column: **out of scope** —
Kubernetes, multi-region, custom domain, mobile client.

**Say:** "Nine objectives, each with a verifiable outcome — we deliberately wrote them
so each one can be checked, not just claimed. And here's what we explicitly excluded.
We left out Kubernetes on purpose: our mini project used EKS, and we wanted to isolate
the network architecture as the variable rather than add orchestration complexity."

> Stating what you excluded, *with a reason*, signals maturity. Teams that claim
> everything is in scope get punished.

---

### Slide 8 — Literature Survey
Table with 5–6 rows: Author/year · Contribution · Relevance to us. Pull from report
Chapter 2. Keep to six references on screen; the report has 15.

**Say:** highlight two specifically —
"Rahman et al. at ICSE 2019 analysed over fifteen thousand Infrastructure-as-Code
scripts and found hardcoded secrets and permissive `0.0.0.0/0` rules among the most
common security smells. That directly shaped two of our design decisions. And Guerriero
et al. at ICSME 2019 interviewed industry practitioners and found IaC *testing* is
largely absent — people rely on deployment failures to find problems. That finding
turned out to describe our own experience exactly, which I'll come back to."

> That forward-reference to Slide 13 makes the deck feel designed rather than assembled.

---

### Slide 9 — Comparative Analysis
The comparison table from report Section 2.5 (Monolithic / 2-tier / PaaS / Kubernetes /
Reference AWS / This work).

---

### Slide 10 — Research Gaps
The five gaps, one line each. **This slide is worth the most marks in the literature
section — parameter 3 names gap identification explicitly.**

**Say:** "Five gaps. Isolation asserted at the firewall rather than routing. CIDR-based
tier rules that break under auto scaling. IaC validation that stops at syntax. Cost
treated as an afterthought. And stateful workloads being under-represented — almost
every three-tier example uses a stateless CRUD app, where scaling is trivial. We chose
a WebSocket chat app precisely because it makes scaling hard."

---

### Slide 11 — System Architecture
**Your most important diagram.** Redraw the README ASCII art properly in draw.io.
Three coloured horizontal bands (public / private / isolated), 2 AZs, arrows showing
request flow, and a clear "NO ROUTE" marker on the isolated tier.

**Say:** walk the request path top to bottom — "Internet hits the ALB in the public
subnets. ALB forwards on port 5000 to EC2 instances in the private subnets. Those
instances reach RDS in the isolated subnets. The isolated route table has no default
route at all — so there is no path to the internet in either direction, and critically,
that holds even if someone later misconfigures a security group. A firewall permits
traffic on a path; it cannot create a path."

*(Spend 2 minutes here. This is the centre of the presentation.)*

---

### Slide 12 — Security Design
The SG chain diagram from report Section 4.3, plus the credential flow.

**Say:** "Each tier's rule references the previous tier's security group *ID*, not an
IP range. The reason matters: instances get new private IPs every time the Auto Scaling
Group scales. A CIDR rule would either break or have to be widened to the whole subnet
— which is exactly the permissive-rule smell from the Rahman paper. An SG reference
says 'trust this role', not 'trust this address', so it stays correct through any number
of scale events."

Then credentials: "A random 24-character password is generated at apply time, written
to Secrets Manager, and fetched at container start by the instance's IAM role. No
password in source, in tfvars, or in the image."

---

### Slide 13 — Implementation Status & Verification
CI badge screenshot · 8 modules · 153 tests · the 6-layer verification table.

**Say:** "153 automated tests pass on every push — 13 application, 140 infrastructure.
Six verification layers from formatting through container scanning."

---

### Slide 14 — Defect Analysis ⭐ *your strongest slide*
Table of the five defects (D1–D5) with root cause and impact.

**Say:** "This is the finding we're most proud of. After everything above was green, we
did a manual architectural review and found five defects that would each have broken
the deployment — and every one of them passed all six automated layers.

The clearest example: our NAT instance bound its iptables rule to interface `enX0`,
which is Nitro-generation naming, but we run t2.micro, which is Xen and exposes `eth0`.
So NAT silently wouldn't forward. No internet in the private subnet, the Docker pull
fails, the app never starts, and the Auto Scaling Group replaces instances forever —
while Terraform reports a completely successful apply.

Another one only reproduces on Windows: Git's autocrlf rewrote our bootstrap script to
CRLF, so the rendered user-data started with `#!/bin/bash\r`, which Linux rejects as a
bad interpreter. It's invisible in CI because the CI runner is Linux.

Our conclusion is that `terraform validate` proves *configurational correctness* — it
parses and type-checks — but says nothing about *operational viability*. That's exactly
the gap Guerriero et al. reported, and we hit it ourselves."

> **This is the single best answer to parameter 5 (individual contribution to
> identifying technical gaps). It shows engineering judgement, not tool operation.**

---

### Slide 15 — Stage-II Plan
The 9-phase table from report Section 6.2, plus a Gantt-style timeline.

---

### Slide 16 — Conclusion
3 bullets on what Stage-I delivered · repository URL · "Questions?"

---

## PART 3 — DEMONSTRATION STRATEGY

You have **not deployed to AWS yet**, and that is completely fine for Stage-I — the
circular asks for architecture and design, not a running system. Do not apologise for
it, and do not fake it.

**If asked "can you show it running?"** answer:

> "Not on AWS yet — that's Stage-II, and it's deliberate. We wanted the architecture
> and the pipeline verified before spending on live resources. What we can show you
> right now is the full Terraform codebase, the CI pipeline green on every push, and
> the application running locally through docker-compose."

**Have these ready in browser tabs, in this order:**
1. GitHub repo — the 8 modules under `terraform/modules/`
2. GitHub Actions — green CI run, expanded to show the test count
3. `docker-compose up` running locally, chat app open in two browser windows showing
   real-time messaging *(rehearse this — have it already running before you walk in)*
4. `terraform validate` output in a terminal

**Backup:** record a 60-second screen capture of the local demo the night before. If
Wi-Fi or Docker fails in the room, you play the video. Never let a live demo failure
consume your slot.

---

## PART 4 — INDIVIDUAL PREPARATION (parameters 4 & 5)

**This is where teams lose marks.** Every member will be asked separately. Do not
divide the project so that only one person understands the architecture.

### Non-negotiable: every member must be able to
1. State the problem statement from memory
2. Draw the three-tier diagram on a whiteboard, unaided
3. Explain why the isolated tier has no route
4. Explain why security groups reference SG IDs instead of CIDRs
5. Name at least two papers from the literature survey and what each contributed
6. Describe at least one defect from Slide 14 in detail

### Each member should own a distinct area
Agree these now and put them in the progress report:

| Member | Suggested ownership | Their "individual gap" answer |
|--------|--------------------|-------------------------------|
| `[[Name 1]]` | Network architecture + VPC/routing/security groups | Gaps 1 & 2 — firewall-layer isolation and CIDR brittleness |
| `[[Name 2]]` | Application + stateful scaling (WebSocket, Redis backplane) | Gap 5 — stateful workloads under-represented in tiering literature |
| `[[Name 3]]` | CI/CD, DevSecOps pipeline, defect analysis | Gap 3 — IaC validation stops at syntax |
| `[[Name 4]]` | Cost modelling, monitoring, Well-Architected mapping | Gap 4 — cost not a design parameter |

*(Adjust to your actual team size. If you are fewer, distribute — but every gap needs
an owner who can defend it.)*

### Answering "what was YOUR individual motivation?" (parameter 4)

Do **not** say "I was interested in cloud computing." That scores near zero. Use this
structure:

> **[Concrete experience] → [what frustrated me] → [what I wanted to prove]**

Worked example:
> "In our two-tier mini project I was the one who set up the database. I put the
> password in an environment variable in a manifest file, and later realised it was
> sitting in our git history permanently — anyone who cloned the repo had our
> credentials. There was no way to rotate it without redeploying by hand. That
> bothered me enough that when we scoped this project I specifically wanted to prove
> you can run a real application where the password exists nowhere in the repository at
> all. That's why I took ownership of the Secrets Manager and IAM design."

Every member writes their own version of this, in their own words, about something they
actually did. **Rehearse saying it out loud.** Memorised paragraphs sound memorised;
a real story doesn't.

### Answering "what was YOUR individual contribution?" (parameter 5)

Structure: **[what I investigated] → [what I found] → [what changed as a result]**

Worked example:
> "I took the verification pipeline. After I got CI green, I wasn't convinced green
> actually meant working, so I read through the modules line by line against the AWS
> docs. I found that our NAT instance bound its iptables rule to interface `enX0`,
> which is the Nitro naming convention, but we launch t2.micro, which is Xen and uses
> `eth0`. It would have silently failed to forward any traffic. That made me realise
> our 140 module tests were all static string matching — they check that a resource is
> *declared*, not that it *works*. So the gap I identified is that IaC validation
> proves configurational correctness but not operational viability, and I've proposed
> behavioural testing for Stage-II."

---

## PART 5 — QUESTION BANK WITH MODEL ANSWERS

### Architecture

**Q: Why three tiers and not two?**
> Fault isolation and blast-radius containment. In two-tier, compromising the app gives
> you the database, because they share a trust boundary. With three tiers the data
> layer sits in subnets with no internet route, so an application compromise doesn't
> automatically become a data breach. It also lets us scale the application tier
> independently of the data tier.

**Q: Why two Availability Zones? Why not one, or three?**
> Two is the minimum for high availability — an ALB requires at least two subnets in
> different AZs, and it means a single AZ failure doesn't take the system down. Three
> would add cost without adding much for a demonstration workload. It's a deliberate
> cost/availability trade-off, and it's parameterised, so adding a third AZ is a
> variable change.

**Q: What exactly makes your database secure?**
> Three independent layers. First, routing: the isolated subnets' route table has no
> default route, so no internet path exists in either direction. Second, security
> groups: only the application tier's security group can reach port 5432. Third, RDS
> itself has `publicly_accessible = false` and storage encryption at rest. The routing
> layer is the strongest, because it holds even if the other two are misconfigured.

**Q: What if someone misconfigures the security group to allow 0.0.0.0/0?**
> Nothing happens — and that's the point of the design. A security group permits or
> denies traffic along a path that routing provides; it cannot create a path. With no
> route to an internet gateway, there is no path for that rule to permit traffic on.

**Q: Isn't `module.secrets → module.rds → module.secrets` a circular dependency?**
> It looks circular at module level, but Terraform resolves dependencies at *resource*
> granularity, not module granularity. The actual chain is: `random_password` generates
> the password with no dependencies, `aws_db_instance` consumes it, and then
> `secret_version` writes the secret including the resulting hostname. We verified this
> with `terraform graph`, which builds without a cycle.

### Application & scaling

**Q: Why a chat application? Isn't that trivial?**
> The opposite — we chose it because it's hard to scale. Most three-tier examples use
> stateless CRUD apps where horizontal scaling is trivial: any instance can serve any
> request. A WebSocket chat app holds long-lived connections and shared broadcast
> state. If you naively put two instances behind a load balancer, users on different
> instances can't see each other's messages. That forced us to solve a real distributed
> systems problem.

**Q: So how *do* you solve it?**
> Two mechanisms. ALB sticky sessions pin a client to one instance for the life of its
> WebSocket connection so it doesn't migrate mid-connection. And ElastiCache Redis acts
> as a pub/sub backplane — Flask-SocketIO publishes every emit to Redis, every instance
> subscribes, and each delivers to its own connected clients. So delivery is independent
> of which instance originated the message.

**Q: What happens if Redis goes down?**
> Cross-instance broadcast stops — users on the same instance still see each other, but
> not across instances. Messages still persist to PostgreSQL, so nothing is lost and
> history is intact. Our `/ready` endpoint reports Redis as degraded and a CloudWatch
> alarm fires. Deliberately, our `/health` endpoint does *not* fail on this — I can
> explain why if useful. *(→ next question)*

**Q: Why doesn't your health check verify the database?**
> That was one of our five defects. Originally `/health` checked both RDS and Redis and
> returned 503 if either was down. But the ALB matches on 200 and the ASG uses ELB
> health checks — so a thirty-second Redis blip would have marked every instance
> unhealthy and the ASG would have terminated all of them, turning a small dependency
> problem into a total outage loop. We split it: `/health` is a shallow liveness probe
> for the load balancer, `/ready` is the deep dependency check for humans and
> dashboards. It's the standard liveness/readiness distinction.

### Infrastructure as Code

**Q: Why Terraform and not CloudFormation?**
> Terraform is cloud-agnostic, so the skills and much of the module structure transfer.
> It has a stronger module ecosystem, and the plan/apply workflow gives a clear preview
> of changes before they happen. CloudFormation would work — this is a portability and
> tooling preference, not a technical necessity.

**Q: Why did you write eight modules instead of one file?**
> Reusability, blast-radius control and testability. Each module has a defined
> interface of variables and outputs, so we can reason about one tier without holding
> the whole system in our heads, and we can unit-test them independently. It also means
> the VPC module could be reused unchanged in a different project.

**Q: What does `terraform validate` actually check?**
> Syntax, type correctness and that references resolve. What it explicitly does *not*
> do is contact AWS — so it cannot tell you whether the configuration will actually
> work. That's precisely the gap our defect analysis exposed.

**Q: How do you know your infrastructure is correct?**
> Honestly — we don't yet, fully, and that's an important distinction we make in the
> report. We know it's *configurationally correct*: it formats, validates, passes
> policy scanning and 153 tests. We know it is not yet proven *operationally viable*,
> because we found five defects that passed all of that. Stage-II's deployment is what
> establishes operational viability.

> ⚠️ This answer scores very well. Evaluators respect a student who states the limits
> of their own evidence. Do not claim the system is proven working.

### Security & DevSecOps

**Q: Where is the database password stored?**
> Generated at apply time by Terraform's `random_password`, written to AWS Secrets
> Manager, and fetched at container start via the EC2 instance profile's IAM role. It
> is not in source, tfvars, user-data or the container image.

**Q: But isn't it in Terraform state?**
> Yes — and that's an inherent property of Terraform-managed secrets, not something we
> overlooked. It's why our state backend is an encrypted S3 bucket with restricted
> access and DynamoDB locking. If you need secrets never to touch state, you'd generate
> the password outside Terraform and reference it by ARN only.

> Answering this well is a strong signal. Most teams don't know the answer.

**Q: What do Checkov and Trivy do?**
> Checkov is policy-as-code for infrastructure — it scans Terraform for misconfiguration
> like unencrypted storage or open security groups. Trivy scans the built container
> image for known CVEs. Both run on every push, and Checkov is **enforcing** — it fails
> the build, it doesn't just warn. We started with 39 findings. We fixed 10 in code —
> IMDSv2 enforcement, encrypted root volumes, dropping invalid HTTP headers, restricting
> the VPC default security group to zero rules, SNS encryption and RDS hardening — and
> we documented the remaining 32 as justified skips with an inline reason on each.
> Current state is 96 passed, 0 failed, 32 skipped.

**Q: Why no SSH keys?**
> We use AWS Systems Manager Session Manager instead. It gives shell access through the
> AWS API with IAM authorisation and audit logging, so there's no SSH port open, no key
> pair to distribute, and no key to leak. The bastion host is available behind a toggle
> but defaults to off.

### Cost

**Q: What does this cost to run?**
> About $63/month for the demonstration configuration, and roughly $125 for the
> production configuration with a NAT Gateway, Multi-AZ RDS and two instances. Because
> everything is code, we destroy it between demonstrations, so actual spend is a small
> fraction of that.

**Q: Is the NAT instance a good idea in production?**
> No, and we say so explicitly. It's a single point of failure for egress and it's
> capped at t2.micro bandwidth. We chose it for cost during development. It's a Boolean
> variable — flipping `use_nat_gateway = true` switches to the managed gateway with no
> code change. Making that trade-off explicit and reversible was the design goal.

### Awkward questions — be ready

**Q: What's actually novel here? This is a standard AWS architecture.**
> Fair challenge. We're not claiming a new algorithm — it's an engineering project. What
> we'd defend as contributions are: the routing-level isolation argument, which is
> stronger than the firewall-based isolation in most reference designs; SG chaining
> that stays correct under auto scaling; making cost a first-class parameter so one
> codebase produces two cost points; and our empirical finding about the IaC validation
> gap. We'd rather state that precisely than overclaim.

**Q: You haven't deployed anything. What have you actually done?**
> We've built the complete architecture as code — 8 modules, 153 passing tests, a full
> CI pipeline — and we've done a defect analysis that found five deployment-blocking
> problems before spending anything on AWS. Stage-I is specified as design and
> architecture; deploying before the design was verified would have been the wrong
> order.

**Q: Could you have just used Elastic Beanstalk / App Runner?**
> For getting an app online, yes, and faster. But then AWS makes the network topology
> decisions and we'd have learned nothing about tiering — which is the actual subject of
> the project. We'd also lose the ability to demonstrate the isolation property, because
> we wouldn't control the routing tables.

---

## PART 6 — PRACTICAL CHECKLIST

### One week before (by 06-08)
- [ ] Report printed and bound per college guidelines
- [ ] Research paper in IEEE template, converted to PDF
- [ ] **All 15 references personally verified** — open each one
- [ ] Two ERP communications with supervisor completed and signed (see doc 04)
- [ ] All `[[placeholders]]` replaced in every document
- [ ] Architecture diagram redrawn properly in draw.io (not ASCII art)

### Three days before (by 10-08)
- [ ] Full deck rehearsed end-to-end, timed under 15 minutes
- [ ] Each member individually rehearsed parameters 4 and 5 out loud
- [ ] Backup demo video recorded
- [ ] Deck exported to PDF as fallback (fonts break across machines)
- [ ] Deck on a pen drive **and** emailed to yourself

### Night before
- [ ] Laptop charged, charger packed
- [ ] Browser tabs prepared and bookmarked
- [ ] docker-compose verified running
- [ ] Printed documents in a folder

### On the day
- [ ] Arrive 15 minutes early
- [ ] Open all tabs before your slot starts
- [ ] Phone silent

---

## PART 7 — DELIVERY ADVICE

**Do:**
- Say "we don't know yet, that's Stage-II" when true. Confidence about verified things
  and honesty about unverified things reads as competence.
- Use the whiteboard if offered — drawing the three tiers live is more convincing than
  any slide.
- Attribute work accurately when asked who did what. Evaluators cross-check between
  members.
- Pause after the problem statement. Let it land.

**Don't:**
- Read slides aloud.
- Claim research novelty. Claim engineering contribution.
- Say "it's fully working" — it isn't deployed, and a follow-up question will expose it.
- Let one member answer everything. Actively hand off: "that's the network design, and
  `[[Name 1]]` owns that."
- Argue with an evaluator. If corrected, say "that's a fair point, we'll verify that" —
  and note it down.

**If you don't know an answer:**
> "I don't have that detail memorised — can I confirm and get back to you?"

That costs you far less than guessing wrong. Guessing wrong on a technical detail
invites three more questions probing whether you understand anything.
