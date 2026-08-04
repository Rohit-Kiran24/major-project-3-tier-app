# MAJOR PROJECT STAGE-I — PROJECT REPORT

> **Submission:** First Internal Evaluation, 13-08-2026 (Thursday)
> **Scope per circular:** Abstract, Introduction, Literature Survey, Requirement Analysis, System Architecture Design
>
> **⚠️ PLACEHOLDERS TO FILL BEFORE PRINTING** — search for `[[ ]]`:
> `[[STUDENT NAMES + ROLL NUMBERS]]`, `[[SUPERVISOR NAME]]`, `[[BATCH NUMBER]]`

---

## TITLE PAGE (format per college guidelines)

**Architecture and Automation of a Production-Grade Three-Tier Web Application on AWS Using Terraform and DevSecOps**

A Major Project Stage-I Report submitted in partial fulfilment of the requirements
for the award of the degree of **Bachelor of Technology** in
**Computer Science & Engineering**

Submitted by: `[[STUDENT NAMES + ROLL NUMBERS]]`
Under the guidance of: `[[SUPERVISOR NAME]]`

**Department of Computer Science & Engineering**
**CVR College of Engineering**
(Accredited by NBA, AICTE — Affiliated to JNTU Hyderabad)
Academic Year 2026–27

---

## ABSTRACT

Conventional monolithic and two-tier web deployments place application logic and
persistent data within a single trust boundary, so a compromise of the public-facing
layer yields direct network reachability to the database. They further depend on
manual, click-driven provisioning, which makes environments non-reproducible and
causes configuration drift between deployment attempts.

This project designs, implements and automates a **production-grade three-tier web
application on Amazon Web Services**, provisioned entirely through Infrastructure as
Code. The workload is a real-time multi-room chat application (Flask, Flask-SocketIO,
PostgreSQL, Redis) deliberately chosen because it is *stateful* — it holds WebSocket
connections and shared session state — and therefore stresses horizontal scaling far
harder than a stateless CRUD application would.

The architecture segments a custom Virtual Private Cloud into three subnet tiers
across two Availability Zones: a **public** tier holding the Application Load Balancer,
a **private** tier holding the auto-scaled application instances, and an **isolated**
tier holding the database. The isolated tier's route table intentionally contains no
default route, making the data tier unreachable from the internet as a property of
routing rather than of firewall configuration. Firewall rules are expressed as a
**sequential security-group chain** in which each tier references the previous tier's
security-group identifier instead of a CIDR range, so tier isolation survives any
future change of IP addressing.

Database credentials are never written into source code, environment files or
Terraform variables. A random password is generated at apply time, stored in AWS
Secrets Manager, and retrieved at container start-up by the application using the
EC2 instance's IAM role. The entire infrastructure is expressed as **eight reusable
Terraform modules** and validated by a **DevSecOps continuous-integration pipeline**
that performs format checking, configuration validation, Checkov policy-as-code
scanning of the infrastructure, unit testing of the application, container image
construction and Trivy vulnerability scanning on every push.

Stage-I delivers the complete architecture, the full Terraform codebase, the
application, a green CI pipeline comprising 153 automated tests, and a documented
defect analysis in which five latent deployment defects were identified and corrected
before any cloud resource was provisioned. Stage-II will execute the live deployment
and produce empirical measurements of availability, scaling behaviour, failover time
and cost.

**Keywords:** Cloud Computing, Infrastructure as Code, Terraform, Amazon Web Services,
Three-Tier Architecture, DevSecOps, Zero-Trust Networking, Auto Scaling, High
Availability, Policy as Code.

---

# CHAPTER 1 — INTRODUCTION

## 1.1 Background

Web application architecture has evolved through three broad stages. **Monolithic**
deployments place presentation, business logic and data storage on a single machine;
they are simple but offer no fault isolation and no independent scaling. **Two-tier
(client–server)** architectures separate the client from a combined
application-and-database server, which improves modularity but still allows a
compromised application process to reach the database directly. **Three-tier**
architecture separates presentation, application and data into distinct layers that
can be independently secured, scaled and maintained.

Cloud computing, defined by NIST [1] through the five essential characteristics of
on-demand self-service, broad network access, resource pooling, rapid elasticity and
measured service, makes the three-tier model practical at low cost: each tier maps to
a separately governed network segment with its own scaling policy.

In parallel, **Infrastructure as Code (IaC)** [2] replaced manual console-driven
provisioning with declarative, version-controlled specifications. IaC brings software
engineering discipline — review, versioning, testing, rollback — to infrastructure,
and it is the mechanism that makes an architecture *reproducible* rather than merely
*documented*.

## 1.2 Motivation

This project is a direct evolution of our earlier **two-tier mini project**, which
deployed a containerised application on Kubernetes (EKS). Building and operating that
system exposed four concrete limitations that motivated the present work:

1. **No network segmentation.** Application and database shared a trust boundary. Any
   application-level compromise (SQL injection, deserialisation flaw, leaked
   credential) yielded direct database reachability. There was no architectural layer
   that would have contained the blast radius.

2. **Credentials embedded in configuration.** Database passwords lived in environment
   variables and manifest files. They were visible in the repository history and in
   the cluster's stored state, and rotating them required a manual redeploy.

3. **Manual, non-reproducible provisioning.** Significant portions were created
   through the AWS console. The environment could not be destroyed and recreated
   identically, which made cost control risky and disaster recovery untested.

4. **No automated security verification.** Nothing in the workflow checked whether a
   change introduced a publicly-exposed resource, an unencrypted volume or a
   vulnerable base image.

A fifth motivation is economic and specific to a student context. Reference AWS
architectures assume production budgets. A managed NAT Gateway alone costs roughly
**four times** a NAT instance providing equivalent egress for this workload. An
architecture that is technically correct but unaffordable cannot actually be built,
measured or demonstrated by a student team — so cost became a first-class design
constraint rather than an afterthought.

## 1.3 Problem Statement

> Existing monolithic and two-tier deployments expose the data tier within the same
> trust boundary as the public-facing application, embed credentials in code or
> configuration, and are provisioned manually — resulting in configuration drift,
> non-reproducible environments, unverified security posture and an inability to
> recover deterministically from failure.
>
> **There is a need for a fully automated, network-segmented, zero-trust three-tier
> cloud architecture in which the data tier is unreachable from the internet by
> construction, credentials are injected at runtime rather than stored, the entire
> environment is reproducible from version-controlled code, and every change is
> automatically validated for security compliance before deployment — while remaining
> economically feasible at student scale.**

## 1.4 Objectives

| # | Objective | Verifiable Outcome |
|---|-----------|--------------------|
| O1 | Design a three-tier VPC with public, private and isolated subnets across two Availability Zones | Isolated route table demonstrably contains no `0.0.0.0/0` route |
| O2 | Enforce zero-trust tier isolation using security-group-to-security-group references rather than CIDR ranges | No ingress rule between tiers uses a CIDR block |
| O3 | Eliminate hardcoded credentials via AWS Secrets Manager with IAM-role-based runtime retrieval | No password present in source, tfvars or environment files |
| O4 | Express the complete infrastructure as reusable Terraform modules | 8 modules, `terraform validate` passes |
| O5 | Achieve high availability and elasticity via multi-AZ ALB and CPU-driven Auto Scaling | ASG scales 1→3 on sustained CPU > 70% |
| O6 | Support a *stateful* real-time workload across horizontally scaled instances | Message sent on instance A is delivered to a client on instance B |
| O7 | Build a DevSecOps pipeline performing IaC scanning, unit testing and container scanning | CI green on every push; Checkov and Trivy integrated |
| O8 | Provide observability through CloudWatch alarms, SNS alerting and a unified dashboard | 6 alarms, 6 dashboard widgets across all three tiers |
| O9 | Minimise cost without sacrificing architectural correctness | NAT instance and Multi-AZ toggles; measured saving reported |

## 1.5 Scope

**In scope (Stage-I and Stage-II):**
- Custom VPC, subnetting, routing, internet and NAT egress
- Security groups, IAM roles and policies, Secrets Manager integration
- ALB with sticky sessions, Auto Scaling Group, launch template, scaling policies
- RDS PostgreSQL with encryption and optional Multi-AZ; ElastiCache Redis
- Flask + Flask-SocketIO application with authentication and persistent chat history
- Multi-stage Docker build; GitHub Actions CI and CD workflows
- CloudWatch alarms, SNS notifications, CloudWatch dashboard

**Explicitly out of scope:**
- Kubernetes or service-mesh orchestration (deliberately: the two-tier predecessor
  used EKS; this project isolates the *network architecture* variable)
- Multi-region or cross-region disaster recovery
- Custom domain registration; TLS is designed and code is present but requires an ACM
  certificate, treated as Stage-II polish
- Production-grade load testing beyond what is required to demonstrate scaling
- Mobile or native client applications

## 1.6 Organisation of the Report

Chapter 2 surveys literature on cloud architecture, Infrastructure as Code,
zero-trust networking and DevSecOps, and identifies the gaps this work addresses.
Chapter 3 presents functional and non-functional requirements together with technical,
economic and operational feasibility. Chapter 4 details the system architecture
across network, security, component, data and deployment views. Chapter 5 reports
Stage-I implementation status including defect analysis. Chapter 6 states expected
outcomes and the Stage-II plan.

---

# CHAPTER 2 — LITERATURE SURVEY

## 2.1 Cloud Computing and Architectural Tiering

Mell and Grance [1] provide the reference definition of cloud computing used
throughout this work. The AWS Well-Architected Framework [11] organises cloud design
into six pillars — operational excellence, security, reliability, performance
efficiency, cost optimisation and sustainability — and explicitly recommends
multi-Availability-Zone deployment and network segmentation for production workloads.
This project maps its design decisions to those pillars in Section 4.9.

Pahl [15] analyses containerisation as a packaging and isolation mechanism, motivating
the use of Docker for consistent artefacts across development and production. Dragoni
et al. [14] survey microservice architectures; we note that microservices address
*application* decomposition, whereas the tiering problem addressed here concerns
*network and trust* decomposition — the two are orthogonal, and a three-tier network
can host either a monolith or microservices.

## 2.2 Infrastructure as Code

Morris [2] establishes the foundational principles of IaC: reproducibility,
disposability, idempotence and the treatment of infrastructure definitions as
first-class software artefacts subject to version control and review.

Guerriero et al. [7] interviewed practitioners across industry and report that while
IaC adoption is widespread, **testing and validation of IaC remain immature**;
practitioners rely predominantly on manual review and on failures observed during
actual deployment. Jiang and Adams [9] performed an empirical study across open-source
repositories and found that infrastructure code **co-evolves tightly with application
code** and exhibits churn comparable to production source, strengthening the argument
that it deserves equivalent engineering rigour.

Rahman and Williams [10] examined source-code properties of defective IaC scripts and
identified measurable characteristics correlated with defects, supporting automated
static analysis as a defect-reduction strategy.

## 2.3 Security: Zero-Trust and Secrets Management

NIST SP 800-207 [5] defines Zero Trust Architecture around the principle that trust is
never granted implicitly by network location and must be continuously evaluated per
request. Applying this at the network layer means a resource must not be reachable
merely because a caller resides inside the VPC.

Rahman, Parnin and Williams [6] analysed 15,000+ IaC scripts and catalogued seven
recurring **security smells**, of which *hardcoded secrets* and *overly permissive
network rules (`0.0.0.0/0`)* were among the most prevalent. This finding directly
shaped two design decisions in this project: runtime secret injection (Section 4.4)
and security-group chaining without CIDR-based inter-tier rules (Section 4.3).

## 2.4 DevOps, DevSecOps and Continuous Delivery

Humble and Farley [3] establish continuous delivery through deployment pipelines and
automated verification gates. Bass, Weber and Zhu [4] analyse DevOps from an
architectural standpoint, arguing that deployability is an architectural quality
attribute rather than a downstream operational concern. Zhu, Bass and Champlin-Scharff
[12] characterise the practices constituting DevOps in industrial settings.

Shahin, Babar and Zhu [8] present a systematic review of continuous integration,
delivery and deployment covering approaches, tools and challenges, and observe that
**security verification is frequently absent from CI/CD pipelines** — the gap that
motivates integrating Checkov and Trivy directly into this project's pipeline.

## 2.5 Comparative Analysis of Existing Approaches

| Approach | Segmentation | Provisioning | Secrets | Security in Pipeline | Cost Profile | Limitation Addressed Here |
|----------|--------------|--------------|---------|----------------------|--------------|---------------------------|
| Monolithic single-server | None | Manual | In config files | None | Low | No fault isolation; single point of failure |
| Two-tier client–server | App+DB share boundary | Mostly manual | Environment variables | None | Low–Medium | DB reachable from compromised app |
| Managed PaaS (Elastic Beanstalk / App Service) | Provider-defined, opaque | Semi-automated | Provider vault | Partial | Medium | Limited control over network topology; hard to demonstrate tiering |
| Kubernetes / EKS (our 2-tier mini project) | Namespace / NetworkPolicy | Partly IaC | Secrets objects (base64, not encrypted at rest by default) | Rare | High (control-plane cost) | Cluster complexity obscures network-tier reasoning; control plane cost |
| Reference AWS multi-tier whitepapers | Full three-tier | Full IaC | Secrets Manager | Sometimes | **High** (NAT Gateway, Multi-AZ always on) | Economically infeasible at student scale |
| **This work** | **Public / Private / Isolated, route-level** | **Full IaC (8 Terraform modules)** | **Secrets Manager + IAM role, runtime injection** | **Checkov + Trivy in CI** | **Optimised (NAT instance, toggles)** | — |

## 2.6 Research Gaps Identified

The survey exposes five gaps, each mapped to a design response in this project. *These
are the gaps to state verbally at the review — evaluation parameter 3 asks for exactly
this.*

**Gap 1 — Isolation is asserted at the firewall layer, not the routing layer.**
Most published three-tier designs isolate the database using security-group rules. A
misconfigured rule therefore re-exposes the database. *Response:* the isolated subnets'
route table contains no default route at all, so no security-group error can create an
internet path. Isolation becomes a property of routing, which is strictly stronger.

**Gap 2 — Tier isolation expressed through CIDR ranges is brittle.**
CIDR-based inter-tier rules silently break correctness when addressing changes, and
Rahman et al. [6] identify permissive CIDR rules as a top security smell. *Response:*
every inter-tier rule references the peer tier's security-group ID, so isolation is
independent of IP addressing.

**Gap 3 — IaC validation in practice stops at syntax.**
Guerriero et al. [7] report that practitioners largely lack IaC testing. `terraform
validate` confirms only that configuration parses and type-checks; it never contacts
the provider and cannot detect a semantically valid but non-functional configuration.
*Response:* a layered verification strategy — formatting, validation, policy-as-code
scanning, module-level unit tests, application unit tests and container scanning — plus
an explicit acknowledgement (Section 5.3) of what these layers still cannot catch,
evidenced by five defects that passed all automated gates.

**Gap 4 — Cost is treated as an operational afterthought rather than a design input.**
Reference architectures assume production budgets, placing faithful reproduction beyond
student or small-team means. *Response:* cost-parameterised architecture in which the
NAT strategy and RDS Multi-AZ are Boolean toggles, allowing the *same* code to produce
either an economical demonstration environment or a production-grade one.

**Gap 5 — Stateful real-time workloads are under-represented in tiering literature.**
Most three-tier examples use stateless request/response workloads, where horizontal
scaling is trivial. WebSocket workloads hold long-lived connections and shared
broadcast state, so naive scaling silently breaks message delivery between instances.
*Response:* deliberate selection of a WebSocket chat workload, with ALB sticky sessions
for connection affinity and ElastiCache Redis as a pub/sub backplane for cross-instance
delivery.

---

# CHAPTER 3 — REQUIREMENT ANALYSIS

## 3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR1 | Users shall register with a unique username and a password of minimum 6 characters | High |
| FR2 | Passwords shall be stored only as bcrypt hashes; plaintext shall never be persisted | High |
| FR3 | Registered users shall authenticate and receive a session | High |
| FR4 | Authenticated users shall create chat rooms with unique names | Medium |
| FR5 | Users shall join rooms and exchange messages in real time over WebSocket | High |
| FR6 | Messages shall persist to PostgreSQL and survive instance replacement | High |
| FR7 | Message history shall be retrievable with pagination (default 50, maximum 100) | Medium |
| FR8 | A message sent by a user connected to instance A shall be delivered to a user connected to instance B | High |
| FR9 | Unauthenticated WebSocket connections shall be rejected | High |
| FR10 | The system shall expose a liveness endpoint for load-balancer health checking | High |
| FR11 | The system shall expose a readiness endpoint reporting database and cache connectivity | Medium |

## 3.2 Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR1 | Availability | Application and load-balancer tiers span ≥ 2 Availability Zones; no single AZ failure causes total outage |
| NFR2 | Scalability | Auto Scaling from 1 to 3 instances; scale-out at CPU > 70 % over 2 periods, scale-in at CPU < 30 % over 5 periods |
| NFR3 | Security | Data tier shall have no route to the internet; inter-tier rules shall not use CIDR ranges |
| NFR4 | Security | Credentials shall not appear in source code, tfvars, or container images |
| NFR5 | Security | Data at rest in RDS shall be encrypted |
| NFR6 | Reproducibility | The complete environment shall be creatable and destroyable from version-controlled code |
| NFR7 | Maintainability | Infrastructure shall be decomposed into independently reusable modules |
| NFR8 | Observability | Alarms shall cover all three tiers with email notification |
| NFR9 | Cost | Monthly cost of the demonstration configuration shall remain within student budget |
| NFR10 | Performance | ALB target response time shall remain below 2 s under demonstration load |
| NFR11 | Recoverability | RDS automated backups retained 7 days; storage auto-scales 20 GB → 50 GB |

## 3.3 Hardware and Software Requirements

**Development environment**
- Workstation: 8 GB RAM minimum, 20 GB free disk
- OS: Windows 11 / Linux / macOS
- Docker Desktop, Git, Python 3.11, Terraform ≥ 1.5, AWS CLI v2
- Editor: VS Code

**Cloud resources (AWS, region ap-south-1 — Mumbai)**

| Component | Specification | Purpose |
|-----------|---------------|---------|
| EC2 (application) | t2.micro × 1–3, Amazon Linux 2023 | Application tier |
| EC2 (NAT) | t2.micro × 1 | Cost-optimised egress |
| RDS | PostgreSQL 15, db.t3.micro, 20 GB gp3, encrypted | Data tier |
| ElastiCache | Redis 7.0, cache.t3.micro, 1 node | Pub/sub backplane |
| ALB | Application Load Balancer, 2 subnets | Presentation tier |
| Secrets Manager | 1 secret | Credential storage |
| CloudWatch | 6 alarms + 1 dashboard | Observability |
| SNS | 1 topic, email subscription | Alerting |

**Application stack:** Python 3.11, Flask 3.0, Flask-SocketIO 5.3.6, Flask-Login,
Flask-SQLAlchemy, Flask-Bcrypt, eventlet, Gunicorn, psycopg2, boto3, redis-py.

**DevOps toolchain:** Terraform 1.5, Docker (multi-stage), GitHub Actions, Checkov
(IaC policy scanning), Trivy (container vulnerability scanning), pytest.

## 3.4 Feasibility Study

### 3.4.1 Technical Feasibility
All components are generally available managed services with mature Terraform provider
support (`hashicorp/aws ~> 5.0`). The team has prior AWS and containerisation
experience from the two-tier mini project. Technical feasibility is **confirmed by
evidence, not assumed**: the complete configuration already passes `terraform validate`
and 153 automated tests in continuous integration.

### 3.4.2 Economic Feasibility

Indicative monthly cost, ap-south-1, demonstration configuration
(`use_nat_gateway = false`, `rds_multi_az = false`, 1 application instance):

| Component | Configuration | Approx. USD / month |
|-----------|---------------|---------------------|
| EC2 application | t2.micro × 1 | ~8.50 |
| EC2 NAT instance | t2.micro × 1 | ~8.50 |
| RDS PostgreSQL | db.t3.micro, Single-AZ, 20 GB | ~13.00 |
| ElastiCache Redis | cache.t3.micro × 1 | ~12.00 |
| Application Load Balancer | 1 ALB + minimal LCU | ~18.00 |
| Secrets Manager | 1 secret | ~0.40 |
| CloudWatch + SNS | 6 alarms, 1 dashboard | ~3.00 |
| **Total (demonstration)** | | **≈ 63 USD** |

Cost of the equivalent production configuration (`use_nat_gateway = true`,
`rds_multi_az = true`, 2 instances) rises to approximately **125 USD/month**, dominated
by the NAT Gateway (~33 USD) and doubled RDS (~26 USD).

**Key economic finding:** replacing the managed NAT Gateway with a NAT instance reduces
egress cost from ~33 USD to ~8.50 USD per month — a **~74 % reduction on that line item
and ~28 % on total monthly spend** — while providing equivalent functionality for this
workload. The trade-off is explicit and documented in Section 4.2.3.

Because the environment is fully reproducible, it is destroyed via `terraform destroy`
between demonstrations, so actual incurred cost is a small fraction of the monthly
figure. Economic feasibility is therefore **confirmed**.

> ⚠️ **Before submission:** re-verify every figure against the AWS Pricing Calculator
> for ap-south-1 on the day you print. Prices change, and an evaluator may check one.

### 3.4.3 Operational Feasibility
Deployment is a single workflow invocation (`plan` / `apply` / `destroy`). Rollback is
achieved by re-applying a previous commit. Alarms deliver email notification via SNS
without requiring an operator to watch a console. Administrative access uses AWS
Systems Manager Session Manager rather than SSH, removing key management entirely.
Operational feasibility is **confirmed**.

## 3.5 System Actors and Use Cases

**Actors:** End User (register, log in, create/join room, send and read messages);
Administrator / Developer (deploy, scale, monitor, destroy); Automated Agents (ALB
health checker, Auto Scaling service, CloudWatch alarms, GitHub Actions runner).

**Principal use cases:** UC1 Register · UC2 Authenticate · UC3 Create Room ·
UC4 Join Room · UC5 Send Message (real-time broadcast) · UC6 Retrieve History ·
UC7 Provision Infrastructure · UC8 Automatic Scale-Out · UC9 Receive Alarm Notification.

> **Diagram to draw for the report:** a standard UML use-case diagram with the three
> actor groups above and these nine use cases. Draw it in draw.io and export as PNG.

---

# CHAPTER 4 — SYSTEM ARCHITECTURE DESIGN

## 4.1 Architectural Overview

The system implements three tiers, each occupying a distinct subnet class with a
distinct routing posture:

| Tier | Subnet class | Components | Internet reachability |
|------|--------------|------------|-----------------------|
| Presentation | Public | Application Load Balancer, NAT instance | Inbound and outbound |
| Application | Private | EC2 Auto Scaling Group, ElastiCache Redis | **Outbound only** (via NAT) |
| Data | Isolated | RDS PostgreSQL | **None — no route exists** |

Request flow: `Internet → ALB (public) → EC2 application instances (private) → RDS
(isolated)`. Return traffic follows the reverse path. No path exists from the internet
to the isolated tier in either direction.

## 4.2 Network Design

### 4.2.1 Address Plan

VPC CIDR **10.0.0.0/16**, distributed across two Availability Zones:

| Subnet | AZ | CIDR | Tier | Route table |
|--------|----|------|------|-------------|
| public-1a | ap-south-1a | 10.0.1.0/24 | Presentation | → Internet Gateway |
| public-1b | ap-south-1b | 10.0.2.0/24 | Presentation | → Internet Gateway |
| private-1a | ap-south-1a | 10.0.3.0/24 | Application | → NAT |
| private-1b | ap-south-1b | 10.0.4.0/24 | Application | → NAT |
| database-1a | ap-south-1a | 10.0.5.0/24 | Data | **local only** |
| database-1b | ap-south-1b | 10.0.6.0/24 | Data | **local only** |

### 4.2.2 The Isolation Argument (central design claim)

The database route table is created deliberately empty of any `0.0.0.0/0` entry. AWS
implicitly provides only a `local` route for intra-VPC communication. Consequently:

- RDS cannot initiate an outbound internet connection — there is no route to use.
- No internet host can reach RDS — no return path exists.
- **Critically, this holds even if a security group is later misconfigured to allow
  `0.0.0.0/0`.** A firewall permits or denies traffic on a path; it cannot create a
  path that routing does not provide.

This is the strongest single security property of the design and the point to
emphasise at the review.

### 4.2.3 Egress Strategy and the Cost Toggle

Application instances need outbound access for container image pulls, OS updates and
AWS API calls (Secrets Manager). Two implementations are provided behind
`var.use_nat_gateway`:

| Option | Cost / month | Availability | Bandwidth | Maintenance |
|--------|--------------|--------------|-----------|-------------|
| NAT Gateway (`true`) | ~33 USD | AWS-managed, AZ-redundant | Up to 45 Gbps | None |
| NAT Instance (`false`, default) | ~8.50 USD | Single instance, self-healing via ASG not configured | ~1 Gbps (t2.micro) | Self-managed |

The NAT instance sets `source_dest_check = false` (mandatory for a forwarding host) and
configures IP forwarding with iptables masquerading. Honest limitation to state at the
review: **the NAT instance is a single point of failure for egress**; it is chosen
deliberately for cost, and the toggle permits switching to the managed gateway for
production without any code change.

## 4.3 Security Design — The Zero-Trust Security-Group Chain

Each security group admits traffic by referencing the **security-group ID** of the
preceding tier, never a CIDR range:

```
Internet (0.0.0.0/0)
      │  :80, :443
      ▼
┌─────────────┐
│   ALB-SG    │  ingress: 0.0.0.0/0 on 80,443   (only intentional public surface)
└──────┬──────┘  egress : private CIDRs on 5000
       │ :5000  (ingress rule references ALB-SG **by ID**)
       ▼
┌─────────────┐
│   App-SG    │  ingress: source = ALB-SG
└──┬───────┬──┘  egress : 5432→DB, 6379→Redis, 80/443→internet via NAT
   │ :5432 │ :6379   (both reference App-SG **by ID**)
   ▼       ▼
┌────────┐ ┌──────────┐
│ DB-SG  │ │ Redis-SG │  ingress: source = App-SG; egress restricted to VPC CIDR
└────────┘ └──────────┘
```

**Why SG references rather than CIDRs:** a CIDR rule states "trust this address
range". A security-group reference states "trust this *role*". Instances launched by
the Auto Scaling Group receive new private IPs on every scale event; a CIDR rule would
either break or have to be widened to the whole subnet — the latter being precisely
the permissive-rule smell catalogued by Rahman et al. [6]. The SG reference remains
correct across any number of scale events and any re-addressing of the VPC.

## 4.4 Credential Management Design

```
terraform apply
   └─► random_password (24 chars, no special characters)
          ├─► aws_secretsmanager_secret_version  (JSON: username, password, host, port, dbname)
          └─► aws_db_instance.password
EC2 instance boot
   └─► container start → boto3 → GetSecretValue (authenticated by instance-profile IAM role)
          └─► SQLAlchemy connection string constructed in memory
```

Properties: no password in source, tfvars, container image or user-data; rotation
requires only a secret update and container restart; IAM policy grants
`GetSecretValue`/`DescribeSecret` scoped to the **specific secret ARN**, not `*`.

Special characters are excluded from the generated password deliberately — they would
require URL-encoding inside the PostgreSQL connection URI and are a common source of
silent connection failures.

**Honest limitation to disclose if asked:** the generated password is present in
Terraform *state*. This is why the backend is an encrypted S3 bucket with restricted
access; it is an inherent property of Terraform-managed secrets, not an oversight.

## 4.5 Component Design — Terraform Module Decomposition

| # | Module | Key resources | Principal outputs |
|---|--------|---------------|-------------------|
| 1 | `vpc` | VPC, 6 subnets, IGW, NAT instance/gateway, 3 route tables, DB & cache subnet groups | `vpc_id`, subnet IDs, subnet-group names |
| 2 | `security-groups` | 5 security groups forming the zero-trust chain | `alb_sg_id`, `app_sg_id`, `db_sg_id`, `redis_sg_id` |
| 3 | `secrets-manager` | `random_password`, secret + version, IAM role, 3 policy attachments, instance profile | `secret_name`, `db_username`, `db_password`, `app_instance_profile_name` |
| 4 | `rds` | PostgreSQL instance, parameter group | `db_host`, `db_endpoint` |
| 5 | `elasticache` | Redis cluster | `redis_endpoint` |
| 6 | `alb` | ALB, target group (sticky), HTTP listener | `alb_dns_name`, `target_group_arn` |
| 7 | `asg` | Launch template, ASG, 2 scaling policies, 2 CPU alarms | `asg_name` |
| 8 | `monitoring` | SNS topic + subscription, 6 alarms, dashboard | dashboard name |

**Dependency chain:**
`vpc → security-groups → secrets-manager → rds → elasticache → alb → asg → monitoring`

A subtle and defensible point: `secrets-manager` both *supplies* the password to `rds`
and *consumes* the resulting hostname from `rds`. This is not circular, because
Terraform resolves dependencies at resource granularity rather than module granularity.
The real ordering is `random_password → aws_db_instance → secret_version`. This was
verified with `terraform graph`, which builds without a cycle. *(Expect this question —
it looks circular at a glance.)*

## 4.6 Data Design

```
users                     rooms                       messages
─────                     ─────                       ────────
id           PK           id            PK            id          PK
username     UNIQUE,IDX   name          UNIQUE,IDX    content     NOT NULL
password_hash             description                 user_id     FK→users   (ON DELETE SET NULL)
created_at                created_by    FK→users      room_id     FK→rooms   (ON DELETE CASCADE)
                          created_at                  created_at  IDX
```

Relationships: `users 1—N messages`, `rooms 1—N messages`, `users 1—N rooms`.
`ON DELETE SET NULL` on `messages.user_id` preserves conversation history when an
account is deleted (the message renders as `[deleted]`); `ON DELETE CASCADE` on
`room_id` removes a room's messages with the room. Indexes on `messages(room_id)`,
`messages(created_at DESC)` and the composite `(room_id, created_at DESC)` serve the
paginated history query directly.

## 4.7 Real-Time Messaging Design (the stateful-scaling problem)

**Problem.** With more than one application instance behind a load balancer, clients
connected to different instances occupy different process memory. A naive
`socketio.emit()` reaches only clients on the emitting instance, so User A on
instance 1 and User B on instance 2 cannot see each other's messages.

**Solution — two mechanisms working together:**

1. **ALB sticky sessions** (`lb_cookie`, 24 h) pin a given client to one instance for
   the lifetime of its WebSocket connection, preventing mid-connection migration.
2. **ElastiCache Redis as a pub/sub backplane.** Flask-SocketIO is configured with
   `message_queue=redis://…`. Every emit is published to Redis; all instances subscribe
   and deliver to their own connected clients. Delivery therefore becomes independent
   of which instance originated the message.

Message flow: `Client A → Instance 1 → persist to RDS → publish to Redis → Instances
1..N receive → deliver to their local clients → Client B`.

## 4.8 Deployment Pipeline Design

**CI (`ci.yml`, on every push and pull request to `main`) — two parallel jobs:**

| Job | Stages |
|-----|--------|
| Terraform Validate & Scan | `fmt` → `init -backend=false` → `validate` → Checkov policy scan |
| App Test & Scan | install dependencies → pytest → Docker multi-stage build → Trivy image scan |

**CD (`deploy.yml`, manual `workflow_dispatch`)** with a `plan` / `apply` / `destroy`
choice input. Manual triggering is deliberate: automatic apply on push would make an
accidental merge capable of incurring cost or destroying state.

State is stored in an encrypted **S3** backend with **DynamoDB** state locking to
prevent concurrent applies from corrupting state.

## 4.9 Mapping to AWS Well-Architected Pillars [11]

| Pillar | Realisation in this design |
|--------|----------------------------|
| Security | Three-tier segmentation, zero-trust SG chain, no internet route to data tier, Secrets Manager, least-privilege IAM, encryption at rest, SSM instead of SSH |
| Reliability | Multi-AZ ALB and ASG, ELB health checks, RDS automated backups, optional Multi-AZ, storage auto-scaling |
| Performance Efficiency | Right-sized instances, Redis caching/backplane, gp3 storage, targeted database indexes |
| Cost Optimisation | NAT instance option, Multi-AZ toggle, scale-in policy, `terraform destroy` between demonstrations |
| Operational Excellence | Full IaC, CI/CD, 6 CloudWatch alarms, SNS alerting, unified dashboard |
| Sustainability | Scale-in on low utilisation; no idle over-provisioning |

---

# CHAPTER 5 — STAGE-I IMPLEMENTATION STATUS

## 5.1 Completed

- Eight Terraform modules; `terraform validate` passes; `terraform fmt` clean
- Complete Flask application: authentication, rooms, real-time messaging, persistence
- Multi-stage Dockerfile (non-root user, health check); docker-compose for local development
- GitHub Actions CI and CD workflows
- **153 automated tests passing** — 13 application tests and 140 infrastructure module tests
- Repository: `github.com/Rohit-Kiran24/major-project-3-tier-app` — CI badge green

## 5.2 Verification Strategy and Its Limits

| Layer | Tool | What it proves | What it cannot prove |
|-------|------|----------------|----------------------|
| Formatting | `terraform fmt` | Canonical style | Nothing about behaviour |
| Configuration | `terraform validate` | Parses, types check, references resolve | **Never contacts AWS**; cannot detect a valid-but-non-functional design |
| Policy | Checkov | Compliance against a security rule set | Only encoded rules; currently `--soft-fail` |
| Module structure | pytest (140) | Required resources, variables, outputs and security settings are declared | Static string matching — passes even if the deployed system fails |
| Application | pytest (13) | Routes, authentication, persistence logic | Runs on SQLite, not PostgreSQL |
| Container | Trivy | Known CVEs in image layers | Nothing about runtime configuration |

## 5.3 Defect Analysis — Five Latent Defects Found and Corrected

**This is the strongest content in the report. It demonstrates engineering judgement
rather than tool operation, and it is directly evidence for evaluation parameter 5
(individual contribution to identifying technical gaps).**

All five passed every automated gate above and would have surfaced only during live
deployment.

| # | Defect | Root cause | Consequence if undetected |
|---|--------|-----------|---------------------------|
| D1 | NAT instance would not forward traffic | iptables masquerade bound to interface `enX0` (Nitro-generation naming) while the instance is `t2.micro` (Xen, interface `eth0`); package `iptables-services` does not exist on Amazon Linux 2023 | Default configuration: no egress → image pull fails → application never starts → ASG replaces instances indefinitely |
| D2 | EC2 bootstrap script corrupted by line endings | Windows `core.autocrlf=true` rewrote the shell template with CRLF; `templatefile()` embeds bytes verbatim, producing `#!/bin/bash\r` | Linux rejects as "bad interpreter"; bootstrap dies silently. Reproduces **only** on local Windows apply, never in Linux CI |
| D3 | Health check could terminate healthy instances | `/health` verified RDS *and* Redis and returned 503 if either was degraded, while the ALB matches on 200 and the ASG uses ELB health checks | A transient Redis blip drains and terminates live instances — a self-amplifying replacement loop |
| D4 | Gunicorn preloaded the application under the eventlet worker | `preload_app = True` imports the app before eventlet monkey-patches the standard library | Unpatched blocking sockets inside a green-thread runtime → hangs under concurrent WebSocket load |
| D5 | Unattached Elastic IP billed continuously | `aws_eip.nat` allocated unconditionally but consumed only by the NAT *gateway* path | Silent recurring charge in the default (NAT instance) configuration |

**Finding.** Automated validation established that the configuration was *correct as
code*; it could not establish that the system was *operationally viable*. This is
concrete empirical support for the IaC-testing-maturity gap reported by Guerriero et
al. [7], and it is the principal experiential contribution of Stage-I.

## 5.4 Known Limitations Carried into Stage-II

1. HTTPS not yet enabled — ALB serves HTTP; ACM certificate required (code written, commented)
2. NAT instance is a single point of failure for egress
3. Checkov runs with `--soft-fail`; findings are reported but do not block
4. Infrastructure module tests are static string matching, not behavioural
5. CD workflow uses long-lived AWS access keys; OIDC federation is preferable
6. Live deployment not yet executed — no empirical measurements exist

---

# CHAPTER 6 — EXPECTED OUTCOMES AND STAGE-II PLAN

## 6.1 Expected Outcomes

1. A fully deployed, internet-reachable three-tier application on AWS
2. Demonstrated automatic scale-out under synthetic CPU load and scale-in on recovery
3. Demonstrated cross-instance real-time message delivery via the Redis backplane
4. Empirical evidence of data-tier isolation (attempted connection from outside the VPC fails)
5. Measured cost comparison: NAT instance versus NAT Gateway configuration
6. Complete teardown and identical recreation from code, demonstrating reproducibility

## 6.2 Stage-II Work Plan

| Phase | Activity | Deliverable |
|-------|----------|-------------|
| 1 | Bootstrap S3 backend + DynamoDB lock table; configure credentials | Working remote state |
| 2 | `terraform plan` review, then `apply` | Live environment |
| 3 | Functional validation of all use cases | Test report |
| 4 | Load testing; observe and record scaling behaviour | Scaling measurements |
| 5 | Failure injection (terminate an instance; verify ASG replacement) | Resilience report |
| 6 | Enable HTTPS via ACM; migrate CD to GitHub OIDC | Hardened deployment |
| 7 | Resolve Checkov findings; remove `--soft-fail` | Clean policy scan |
| 8 | Cost measurement and comparative analysis | Cost report |
| 9 | Final documentation and research paper completion | Stage-II report |

---

# REFERENCES

> ⚠️ **VERIFY EVERY REFERENCE BEFORE SUBMISSION.** Confirm each on IEEE Xplore, ACM DL
> or the publisher's site, and correct page numbers and years. Do not submit a citation
> you have not personally opened — evaluators do check, and an unverifiable reference
> is worse than one fewer reference.

[1] P. Mell and T. Grance, "The NIST Definition of Cloud Computing," National Institute
of Standards and Technology, Special Publication 800-145, Sept. 2011.

[2] K. Morris, *Infrastructure as Code: Managing Servers in the Cloud*, 1st ed.
Sebastopol, CA, USA: O'Reilly Media, 2016.

[3] J. Humble and D. Farley, *Continuous Delivery: Reliable Software Releases through
Build, Test, and Deployment Automation*. Boston, MA, USA: Addison-Wesley, 2010.

[4] L. Bass, I. Weber, and L. Zhu, *DevOps: A Software Architect's Perspective*.
Boston, MA, USA: Addison-Wesley, 2015.

[5] S. Rose, O. Borchert, S. Mitchell, and S. Connelly, "Zero Trust Architecture,"
National Institute of Standards and Technology, Special Publication 800-207, Aug. 2020.

[6] A. Rahman, C. Parnin, and L. Williams, "The Seven Sins: Security Smells in
Infrastructure as Code Scripts," in *Proc. 41st Int. Conf. on Software Engineering
(ICSE)*, Montreal, QC, Canada, 2019, pp. 164–175.

[7] M. Guerriero, M. Garriga, D. A. Tamburri, and F. Palomba, "Adoption, Support, and
Challenges of Infrastructure-as-Code: Insights from Industry," in *Proc. IEEE Int.
Conf. on Software Maintenance and Evolution (ICSME)*, Cleveland, OH, USA, 2019,
pp. 580–589.

[8] M. Shahin, M. A. Babar, and L. Zhu, "Continuous Integration, Delivery and
Deployment: A Systematic Review on Approaches, Tools, Challenges and Practices,"
*IEEE Access*, vol. 5, pp. 3909–3943, 2017.

[9] Y. Jiang and B. Adams, "Co-evolution of Infrastructure and Source Code: An
Empirical Study," in *Proc. 12th Working Conf. on Mining Software Repositories (MSR)*,
Florence, Italy, 2015, pp. 45–55.

[10] A. Rahman and L. Williams, "Source Code Properties of Defective Infrastructure as
Code Scripts," *Information and Software Technology*, vol. 112, pp. 148–163, 2019.

[11] Amazon Web Services, "AWS Well-Architected Framework," AWS Whitepaper, 2023.
[Online]. Available: https://docs.aws.amazon.com/wellarchitected/

[12] L. Zhu, L. Bass, and G. Champlin-Scharff, "DevOps and Its Practices," *IEEE
Software*, vol. 33, no. 3, pp. 32–34, May–June 2016.

[13] HashiCorp, "Terraform Documentation." [Online]. Available:
https://developer.hashicorp.com/terraform/docs

[14] N. Dragoni, S. Giallorenzo, A. L. Lafuente, M. Mazzara, F. Montesi, R. Mustafin,
and L. Safina, "Microservices: Yesterday, Today, and Tomorrow," in *Present and
Ulterior Software Engineering*, Cham, Switzerland: Springer, 2017, pp. 195–216.

[15] C. Pahl, "Containerization and the PaaS Cloud," *IEEE Cloud Computing*, vol. 2,
no. 3, pp. 24–31, May–June 2015.
