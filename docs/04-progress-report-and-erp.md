# PROJECT PROGRESS REPORT + ERP COMMUNICATION DRAFTS

> **Circular requirement B.3:** *"Project Progress Report containing proof of two
> communications with the Project Supervisor through the ERP Portal, duly signed by the
> Project Supervisor."*

**⚠️ Act on this first.** The other two documents you can write in a night. This one
requires **two ERP communications that already exist** plus **your supervisor's
physical signature**. If you have not yet logged two ERP messages, do it today — with
the review on 13-08 you need time for your supervisor to respond and sign.

**Checklist:**
- [ ] Communication 1 logged on ERP · date: ____________
- [ ] Supervisor responded · date: ____________
- [ ] Communication 2 logged on ERP · date: ____________
- [ ] Supervisor responded · date: ____________
- [ ] Screenshots/printouts of both taken from the ERP portal
- [ ] Progress report printed and **signed by supervisor**

---

## PART A — PROGRESS REPORT (fill and print)

### PROJECT PROGRESS REPORT — MAJOR PROJECT STAGE-I

**Department of Computer Science & Engineering, CVR College of Engineering**

| Field | Detail |
|-------|--------|
| Project Title | Architecture and Automation of a Production-Grade Three-Tier Web Application on AWS Using Terraform and DevSecOps |
| Batch Number | `[[BATCH NO.]]` |
| Team Members | `[[Name 1 — Roll No.]]`, `[[Name 2 — Roll No.]]`, `[[Name 3 — Roll No.]]` |
| Project Supervisor | `[[SUPERVISOR NAME]]` |
| Semester / Regulation | IV-I, R22 (2023 batch) |
| Report Period | `[[start date]]` to 13-08-2026 |

---

### 1. Work Completed in This Period

**Problem formulation and literature study**
- Reviewed 15 sources spanning cloud architecture, Infrastructure as Code, zero-trust
  networking and DevSecOps
- Identified five research/technical gaps, each mapped to a specific design response
- Finalised problem statement, nine objectives and explicit scope boundaries

**Architecture design**
- Designed a three-tier VPC: public, private and isolated subnets across two
  Availability Zones (10.0.0.0/16)
- Designed routing-level data-tier isolation — the isolated route table contains no
  default route
- Designed a zero-trust security-group chain using SG-to-SG references rather than CIDR
  ranges
- Designed runtime credential injection via AWS Secrets Manager with IAM
  instance-profile authorisation

**Implementation**
- Implemented 8 reusable Terraform modules: `vpc`, `security-groups`,
  `secrets-manager`, `rds`, `elasticache`, `alb`, `asg`, `monitoring`
- Implemented the Flask + Flask-SocketIO application with authentication, multi-room
  chat, persistent history and a Redis pub/sub backplane for cross-instance delivery
- Built a multi-stage Docker image running as a non-root user
- Built GitHub Actions CI (fmt → validate → Checkov → pytest → Docker build → Trivy)
  and a manually-triggered CD workflow

**Verification**
- 153 automated tests passing — 13 application, 140 infrastructure module tests
- `terraform validate` passing; dependency graph confirmed acyclic
- CI green on every push to `main`

**Defect analysis**
- Conducted manual architectural review after automated verification passed
- Identified and corrected five latent defects that would each have prevented a
  successful deployment, none detectable by the automated pipeline
- Documented the finding as an empirical instance of the IaC validation gap reported in
  the literature

**Repository:** `https://github.com/Rohit-Kiran24/major-project-3-tier-app`

---

### 2. Individual Contributions

> Fill honestly — evaluators cross-check this against what each member says in the viva.

| Member | Contribution in This Period |
|--------|----------------------------|
| `[[Name 1]]` | `[[e.g. VPC and routing design; security-group chain; identified Gaps 1 and 2]]` |
| `[[Name 2]]` | `[[e.g. Flask/SocketIO application; Redis backplane design; identified Gap 5]]` |
| `[[Name 3]]` | `[[e.g. CI/CD pipeline; Checkov/Trivy integration; defect analysis; identified Gap 3]]` |

---

### 3. Deviations from the Original Plan

| Planned | Actual | Reason |
|---------|--------|--------|
| Deploy to AWS in Stage-I | Deferred to Stage-II | Architectural review identified five deployment-blocking defects; deploying before correcting them would have incurred cost and produced misleading results |
| `[[add any others]]` | | |

---

### 4. Work Planned for the Next Period (Stage-II)

1. Bootstrap S3 remote state backend and DynamoDB lock table
2. Execute `terraform plan`, review, then `apply` to provision the live environment
3. Functional validation of all use cases against the deployed system
4. Load testing; record auto-scaling behaviour and response times
5. Failure injection — terminate an instance and measure ASG replacement time
6. Enable HTTPS via ACM; migrate the CD pipeline to GitHub OIDC federation
7. Resolve Checkov findings and remove `--soft-fail`
8. Measure and compare actual cost across both configurations
9. Complete Stage-II report and finalise the research paper

---

### 5. Difficulties Encountered / Support Required

- `[[e.g. AWS Free Tier limits on RDS Multi-AZ — request guidance on demonstration budget]]`
- `[[e.g. Access to a college AWS account, or approval to use personal billing]]`
- `[[e.g. Guidance on target conference/journal for the research paper]]`

---

**Date:** ______________

**Signature of Team Members:**

1. ______________________  2. ______________________  3. ______________________

**Signature of Project Supervisor:** ______________________

`[[SUPERVISOR NAME]]`

---

## PART B — ERP COMMUNICATION DRAFTS

Adapt these to your ERP portal's message format. Keep them **specific** — a supervisor
can sign off a detailed update quickly, whereas a vague one invites a meeting you don't
have time for.

---

### Communication 1 — Problem formulation and literature review

**Subject:** Major Project Stage-I — Problem Formulation and Literature Review Update

> Respected Sir/Madam,
>
> This is to update you on the progress of our Major Project Stage-I, titled
> *"Architecture and Automation of a Production-Grade Three-Tier Web Application on AWS
> Using Terraform and DevSecOps."*
>
> We have completed the literature review, covering 15 sources across cloud
> architecture, Infrastructure as Code, zero-trust networking and DevSecOps. Key
> references include NIST SP 800-145 and SP 800-207, Rahman et al. (ICSE 2019) on
> security smells in Infrastructure-as-Code, and Guerriero et al. (ICSME 2019) on
> industrial IaC adoption and testing practice.
>
> From this review we identified five gaps that shape our design:
> 1. Data-tier isolation is typically enforced at the firewall layer rather than the
>    routing layer, so a single misconfiguration can re-expose the database.
> 2. CIDR-based inter-tier firewall rules break under auto scaling.
> 3. IaC validation in practice stops at syntax checking.
> 4. Cost is treated as an operational afterthought rather than a design parameter.
> 5. Stateful real-time workloads are under-represented in tiering literature.
>
> Accordingly we have finalised our problem statement and nine objectives, each with a
> verifiable outcome. We have also deliberately scoped out Kubernetes orchestration,
> multi-region deployment and mobile clients, so as to isolate network architecture as
> the variable under study.
>
> We request your review of our problem statement and objectives, and any suggestions
> on additional literature we should consider.
>
> Thank you,
> `[[Team member names, Roll numbers, Batch]]`

---

### Communication 2 — Architecture, implementation and defect analysis

**Subject:** Major Project Stage-I — Architecture Design and Implementation Status

> Respected Sir/Madam,
>
> Further to our previous communication, we submit our progress on architecture design
> and implementation.
>
> **Architecture.** We have designed a three-tier VPC (10.0.0.0/16) with public,
> private and isolated subnets across two Availability Zones. The central security
> property is that the isolated subnets' route table contains no default route, so the
> database has no internet path in either direction — and this holds even if a security
> group is later misconfigured, since a firewall cannot create a route. Inter-tier
> access control uses security-group references rather than CIDR ranges, so isolation
> remains correct across auto-scaling events.
>
> **Implementation.** We have implemented eight reusable Terraform modules and the
> complete application (Flask, Flask-SocketIO, PostgreSQL, Redis), containerised with a
> multi-stage Docker build. A GitHub Actions CI pipeline performs format checking,
> Terraform validation, Checkov policy scanning, unit testing, image building and Trivy
> vulnerability scanning on every push. 153 automated tests currently pass.
>
> **Defect analysis.** After the automated pipeline was fully green, we conducted a
> manual architectural review and identified five latent defects that would each have
> prevented a successful deployment — including a NAT configuration bound to the wrong
> network-interface naming convention for our instance generation, and a health-check
> design that would have caused the Auto Scaling Group to terminate healthy instances
> during a transient dependency failure. None of these was detectable by the automated
> pipeline. We have corrected all five and documented this as an empirical instance of
> the IaC validation gap noted in the literature.
>
> **Next period.** We plan to bootstrap remote state, deploy the live environment, and
> carry out load testing, failure injection and cost measurement in Stage-II.
>
> We request your guidance on `[[e.g. the AWS account/budget arrangement for live
> deployment]]` and your approval to proceed to deployment.
>
> Thank you,
> `[[Team member names, Roll numbers, Batch]]`

---

## PART C — SUBMISSION BUNDLE

What you physically carry on 13-08-2026:

| # | Document | Source | Status |
|---|----------|--------|--------|
| 1 | Project Report (bound, per college guidelines) | `01-project-report-stage1.md` | ☐ |
| 2 | Research Paper (IEEE two-column PDF) | `02-research-paper-ieee.md` | ☐ |
| 3 | Project Progress Report (**supervisor-signed**) | Part A above | ☐ |
| 4 | ERP communication printouts (both, signed) | Part B above | ☐ |
| 5 | PPT (on laptop + pen drive + emailed) | `03-presentation-guide.md` | ☐ |
| 6 | Backup demo video | recorded locally | ☐ |
