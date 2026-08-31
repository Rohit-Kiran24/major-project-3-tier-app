# RESEARCH PAPER — IEEE FORMAT

> **Required sections (per circular B.2):** Abstract, Keywords, Introduction,
> Literature Review, Methodology, References.
>
> **Formatting instructions for Word/LaTeX:**
> - Use the official IEEE Conference template (`IEEEtran`, A4, two-column)
> - Body: Times New Roman 10 pt · Title: 24 pt · Authors: 11 pt
> - Section headings: Roman numerals (I, II, III…), small caps, centred
> - Margins: top 0.75", bottom 1", left/right 0.625", column gap 0.25"
> - Download: https://www.ieee.org/conferences/publishing/templates.html
>
> Fill `[[ ]]` placeholders before submission.

---

## Architecture and Automation of a Production-Grade Three-Tier Web Application on AWS Using Terraform and DevSecOps

**`[[Author 1]]`**, **`[[Author 2]]`**, **`[[Author 3]]`**, **`[[Supervisor Name]]`**

*Department of Computer Science & Engineering*
*CVR College of Engineering, Hyderabad, Telangana, India*
`[[email addresses]]`

---

### Abstract

Monolithic and two-tier web deployments place application logic and persistent data
within a single trust boundary, so compromise of the public-facing layer yields direct
network reachability to the database. Such systems are additionally provisioned through
manual, console-driven workflows that produce configuration drift and
non-reproducible environments. This paper presents the design and automated
provisioning of a production-grade three-tier web application on Amazon Web Services,
expressed entirely as Infrastructure as Code. The architecture partitions a custom
Virtual Private Cloud into public, private and isolated subnet tiers across two
Availability Zones. Isolation of the data tier is enforced at the **routing** layer
rather than the firewall layer: the isolated subnets' route table contains no default
route, so no security-group misconfiguration can establish an internet path to the
database. Inter-tier access control is expressed as a sequential security-group chain
in which each tier references the preceding tier's security-group identifier rather
than a CIDR range, making isolation invariant under IP re-addressing and Auto Scaling
events. Database credentials are generated at provisioning time, stored in AWS Secrets
Manager, and retrieved at runtime through an EC2 instance-profile IAM role, so no
credential appears in source code, configuration or container images. The workload is
a real-time WebSocket chat application, selected deliberately because its stateful
nature stresses horizontal scaling more severely than stateless request/response
workloads; cross-instance message delivery is achieved through an ElastiCache Redis
publish/subscribe backplane combined with load-balancer session affinity. The
infrastructure comprises eight reusable Terraform modules validated by a DevSecOps
pipeline performing policy-as-code scanning, unit testing and container vulnerability
scanning on every commit. We further report an empirical observation of practical
significance: five latent defects capable of preventing successful deployment passed
every automated validation gate, including `terraform validate`, 140 infrastructure
unit tests and policy scanning. We characterise these defects and argue that current
IaC validation tooling verifies *configurational correctness* while providing little
assurance of *operational viability*.

**Keywords—** Cloud Computing; Infrastructure as Code; Terraform; Amazon Web Services;
Three-Tier Architecture; DevSecOps; Zero-Trust Networking; Auto Scaling; Policy as
Code; WebSocket Scalability.

---

## I. INTRODUCTION

Web application architectures have progressed from monolithic single-server
deployments through two-tier client–server models to multi-tier designs that separate
presentation, application and data concerns. The security motivation for this
separation is well established: an attacker who compromises a presentation-layer
component should not thereby obtain network reachability to persistent data.

Cloud computing [1] makes fine-grained tiering economically practical, since each tier
maps to an independently governed network segment with its own scaling policy and
access-control posture. Concurrently, Infrastructure as Code (IaC) [2] has replaced
manual provisioning with declarative specifications placed under version control,
bringing review, testing and rollback to infrastructure management.

Despite this maturity, three problems persist in practice.

First, **isolation is commonly asserted at the firewall layer**. Published three-tier
reference designs typically restrict database access using security-group rules. Since
a security group permits or denies traffic along an existing path, a single
misconfigured rule can re-expose the data tier. The stronger guarantee — removing the
path itself — is less frequently applied.

Second, **security smells remain prevalent in deployed IaC**. Rahman *et al.* [6]
analysed over 15,000 IaC scripts and found hardcoded secrets and overly permissive
network rules among the most common defect categories, indicating that the availability
of secret-management services has not eliminated the practice of embedding credentials.

Third, **IaC validation practice remains immature**. Guerriero *et al.* [7] report from
industrial interviews that practitioners rely largely on manual review and on failures
observed during actual deployment, with limited automated testing of infrastructure
definitions.

This paper makes four contributions:

1. A three-tier AWS architecture in which data-tier isolation is a **routing-level
   invariant** rather than a firewall policy, and a demonstration that this property is
   robust to security-group misconfiguration.
2. A **zero-trust security-group chaining** scheme in which no inter-tier rule
   references a CIDR range, rendering tier isolation invariant under Auto Scaling and
   network re-addressing.
3. A **cost-parameterised** implementation in which egress strategy and database
   redundancy are Boolean toggles, allowing one codebase to yield either an economical
   demonstration environment or a production-grade deployment, with the cost delta
   quantified.
4. An **empirical characterisation of the IaC validation gap**: five classes of latent
   defect that pass formatting, validation, policy scanning and unit testing yet
   prevent successful deployment.

The remainder of the paper is organised as follows. Section II reviews related work.
Section III describes the methodology, covering architecture, security design,
credential management, stateful scaling and the verification pipeline. Section IV
presents results and discussion. Section V concludes and outlines future work.

---

## II. LITERATURE REVIEW

### A. Cloud Architecture and Tiering

Mell and Grance [1] provide the canonical definition of cloud computing through five
essential characteristics. The AWS Well-Architected Framework [11] codifies design
guidance across six pillars and recommends multi-Availability-Zone deployment with
network segmentation for production workloads.

Pahl [15] analyses containerisation as an isolation and packaging mechanism, motivating
container-based deployment for artefact consistency across environments. Dragoni *et
al.* [14] survey microservice architectures. We observe that microservices address
*application* decomposition whereas tiering addresses *network and trust*
decomposition; the concerns are orthogonal, and a three-tier network may host either a
monolithic or a microservice application.

### B. Infrastructure as Code

Morris [2] establishes IaC principles of reproducibility, disposability and
idempotence. Jiang and Adams [9] conduct an empirical study across open-source
repositories, finding that infrastructure code co-evolves tightly with application code
and exhibits comparable churn — evidence that it warrants equivalent engineering
rigour.

Rahman and Williams [10] identify source-code properties correlated with defective IaC
scripts, supporting static analysis as a defect-reduction strategy. Guerriero *et al.*
[7] document industrial adoption patterns and report a pronounced deficiency in IaC
testing practice. Our Section IV findings provide concrete corroboration of that
deficiency.

### C. Zero-Trust Networking and Secrets Management

NIST SP 800-207 [5] formalises Zero Trust Architecture around the principle that trust
is never conferred implicitly by network location. Applied at the network layer, this
implies that residence within a VPC must not by itself confer reachability to a
resource.

Rahman *et al.* [6] catalogue seven recurring security smells in IaC, of which
hardcoded secrets and permissive `0.0.0.0/0` rules are the most directly relevant. Our
design responds to both: credentials are injected at runtime from a managed secret
store, and no inter-tier rule employs a CIDR range.

### D. DevOps, DevSecOps and Continuous Delivery

Humble and Farley [3] establish deployment pipelines with automated verification gates.
Bass *et al.* [4] treat deployability as an architectural quality attribute rather than
an operational afterthought. Zhu *et al.* [12] characterise constituent DevOps
practices in industrial settings.

Shahin *et al.* [8] present a systematic review of continuous integration, delivery and
deployment and observe that security verification is frequently absent from pipelines.
This motivates our integration of policy-as-code (Checkov) and container vulnerability
scanning (Trivy) as mandatory pipeline stages.

### E. Synthesis and Identified Gaps

The reviewed literature establishes tiering, IaC and zero-trust as individually mature
domains, but leaves four gaps that this work addresses: (i) isolation enforced at the
firewall rather than the routing layer; (ii) brittleness of CIDR-based inter-tier rules
under elastic scaling; (iii) immaturity of IaC validation beyond syntactic checking
[7]; and (iv) the absence of cost as a first-class design parameter in reference
architectures, which limits reproducibility by resource-constrained teams.

---

## III. METHODOLOGY

### A. System Architecture

The system implements three tiers within a custom VPC of CIDR `10.0.0.0/16` spanning
two Availability Zones in the ap-south-1 region.

**TABLE I. SUBNET ALLOCATION AND ROUTING POSTURE**

| Tier | Subnets | CIDR | Route table | Internet reachability |
|------|---------|------|-------------|-----------------------|
| Presentation (public) | 2 | 10.0.1.0/24, 10.0.2.0/24 | → Internet Gateway | Inbound + outbound |
| Application (private) | 2 | 10.0.3.0/24, 10.0.4.0/24 | → NAT | Outbound only |
| Data (isolated) | 2 | 10.0.5.0/24, 10.0.6.0/24 | local only | **None** |

The presentation tier hosts an Application Load Balancer; the application tier hosts an
EC2 Auto Scaling Group and an ElastiCache Redis cluster; the data tier hosts an RDS
PostgreSQL instance.

### B. Routing-Level Isolation

The data tier's route table is created containing no `0.0.0.0/0` entry. AWS supplies
only an implicit `local` route for intra-VPC communication. Consequently the database
can neither initiate outbound internet connections nor receive inbound ones, because no
route exists to carry such traffic.

The significant property is that this invariant is **independent of firewall
configuration**. A security group grants or denies traffic along a path that routing
provides; it cannot create a path. An erroneous rule permitting `0.0.0.0/0` on port
5432 therefore does not expose the database. This yields a strictly stronger guarantee
than firewall-based isolation and requires no additional cost or complexity.

### C. Zero-Trust Security-Group Chaining

Access control is expressed as a sequential chain:

`Internet → ALB-SG → App-SG → {DB-SG, Redis-SG}`

Each rule references the preceding tier's **security-group identifier**. The only rule
admitting a CIDR range is the intentional public ingress to the ALB on ports 80 and
443.

The motivation is that a CIDR rule expresses trust in an *address range*, whereas a
security-group reference expresses trust in a *role*. Instances launched by the Auto
Scaling Group receive new private addresses at each scale event; a CIDR-based rule
would require widening to the entire subnet, reproducing precisely the permissive-rule
smell identified in [6]. The security-group reference remains correct under arbitrary
scaling and re-addressing.

### D. Runtime Credential Injection

At provisioning time a 24-character password is generated and written to AWS Secrets
Manager together with connection metadata. Special characters are excluded to avoid
URL-encoding ambiguity in the PostgreSQL connection URI. An IAM role is attached to
application instances through an instance profile, with a policy granting
`secretsmanager:GetSecretValue` and `secretsmanager:DescribeSecret` scoped to the
specific secret ARN rather than a wildcard.

At container start-up the application retrieves the secret via boto3, authenticated by
the instance-profile credentials, and constructs the database connection string in
memory. No credential is present in source code, Terraform variable files, user-data or
the container image. We note for completeness that the generated password resides in
Terraform state, which is consequently stored in an encrypted S3 backend with
restricted access and DynamoDB-based locking.

### E. Stateful Workload and Cross-Instance Delivery

A real-time WebSocket chat application was selected deliberately: unlike stateless
request/response workloads, it maintains long-lived connections and shared broadcast
state, so horizontal scaling can silently break functional correctness.

With multiple instances behind a load balancer, clients connected to different
instances occupy disjoint process memory, and a naive emit reaches only locally
connected clients. Two mechanisms resolve this:

1. **Session affinity.** ALB `lb_cookie` stickiness (24-hour duration) pins a client to
   one instance for the lifetime of its connection, preventing mid-connection
   migration.
2. **Publish/subscribe backplane.** Flask-SocketIO is configured with an ElastiCache
   Redis message queue. Each emit is published to Redis; all instances subscribe and
   deliver to their locally connected clients, making delivery independent of the
   originating instance.

Messages are persisted to PostgreSQL before broadcast, so history survives instance
replacement.

### F. Modular Infrastructure Decomposition

The infrastructure is decomposed into eight Terraform modules — `vpc`,
`security-groups`, `secrets-manager`, `rds`, `elasticache`, `alb`, `asg` and
`monitoring` — composed by a root configuration with an explicit dependency chain.

A noteworthy resolution concerns an apparent circular dependency: the
`secrets-manager` module supplies the database password to `rds` while consuming the
resulting hostname from `rds`. This is not cyclic, because Terraform resolves
dependencies at resource rather than module granularity; the effective ordering is
`random_password → aws_db_instance → secret_version`. The absence of a cycle was
confirmed by graph construction.

### G. DevSecOps Verification Pipeline

**TABLE II. VERIFICATION LAYERS AND THEIR SCOPE**

| Layer | Instrument | Property verified |
|-------|-----------|-------------------|
| Formatting | `terraform fmt` | Canonical style |
| Configuration | `terraform validate` | Parsing, typing, reference resolution |
| Policy as code | Checkov | Compliance with encoded security rules |
| Module structure | pytest (140 tests) | Declaration of required resources, variables, outputs, security settings |
| Application | pytest (13 tests) | Routing, authentication, persistence |
| Container image | Trivy | Known CVEs at HIGH and CRITICAL severity |

Continuous integration executes all layers on every push and pull request. Continuous
deployment is triggered manually with an explicit `plan`/`apply`/`destroy` selection,
preventing an accidental merge from incurring cost or destroying state.

### H. Cost Parameterisation

Two Boolean variables permit one codebase to produce environments at different cost
points: `use_nat_gateway` selects between a managed NAT Gateway and a NAT instance, and
`rds_multi_az` controls database redundancy.

**TABLE III. INDICATIVE MONTHLY COST, ap-south-1 (USD)**

| Configuration | Egress | RDS | Instances | Total (approx.) |
|---------------|--------|-----|-----------|-----------------|
| Demonstration | NAT instance ≈ 8.50 | Single-AZ ≈ 13 | 1 | **≈ 63** |
| Production | NAT Gateway ≈ 33 | Multi-AZ ≈ 26 | 2 | **≈ 125** |

The NAT substitution alone reduces egress cost by approximately 74 % with equivalent
functionality for this workload, at the cost of introducing a single point of failure
for outbound connectivity.

---

## IV. RESULTS AND DISCUSSION

### A. Stage-I Verification Status

The complete configuration passes `terraform fmt`, `terraform validate` and
policy scanning, and 153 automated tests execute successfully in continuous
integration (13 application, 140 infrastructure). Graph construction confirms an
acyclic dependency structure.

### B. The Validation Gap: Five Latent Defects

Manual architectural review, conducted after all automated gates reported success,
identified five defects capable of preventing successful deployment.

**TABLE IV. LATENT DEFECTS UNDETECTED BY AUTOMATED VALIDATION**

| ID | Defect class | Mechanism | Impact |
|----|--------------|-----------|--------|
| D1 | Platform-dependent identifier | iptables masquerade bound to interface `enX0` (Nitro naming) on a Xen-generation instance exposing `eth0`; packages referenced absent from target AMI | Total egress failure → image pull failure → indefinite instance replacement |
| D2 | Toolchain-induced corruption | Windows autocrlf rewrote a shell template to CRLF; template rendering embeds bytes verbatim, yielding `#!/bin/bash\r` | Bootstrap failure, reproducible only on local Windows execution, never in Linux CI |
| D3 | Probe semantics conflation | Liveness endpoint performed dependency checking and returned 503 on degradation, while the load balancer matched 200 and the scaling group used ELB health checks | Transient dependency degradation triggers self-amplifying instance replacement |
| D4 | Runtime model violation | Application preloaded before green-thread monkey-patching of the standard library | Unpatched blocking sockets under a cooperative-concurrency runtime; hangs under load |
| D5 | Conditional resource leak | Elastic IP allocated unconditionally but consumed only on one configuration branch | Continuous billing for an unattached address |

None was detectable by the instrumented layers. `terraform validate` performs no
provider interaction and cannot assess operational viability. Policy scanning evaluates
only encoded rules. The infrastructure unit tests perform static assertion over
configuration text and therefore pass irrespective of runtime behaviour. Defect D2 is
particularly instructive: it manifests only under a specific developer-platform
configuration and is invisible to a Linux-hosted CI runner, illustrating that pipeline
success does not generalise across execution environments.

### C. Discussion

These observations empirically corroborate the IaC testing-maturity deficiency reported
by Guerriero *et al.* [7]. We characterise the gap as a distinction between
**configurational correctness** — that a specification parses, type-checks and complies
with encoded policy — and **operational viability** — that the specified system
functions when instantiated. Contemporary tooling addresses the former comprehensively
and the latter scarcely at all.

Defects D1 and D2 further indicate that IaC defects can be *environment-dependent*:
correctness becomes contingent on the instance generation selected and on the developer
workstation's configuration. Validation performed in a single environment is therefore
insufficient.

### D. Limitations

Stage-I reports design and static verification; live deployment measurements are not
yet available. The NAT instance constitutes a single point of failure for egress.
Policy scanning is enforcing, though 32 findings are suppressed by documented
justified skips rather than remediated. TLS termination is designed
but not enabled, pending certificate provisioning. Cost figures are indicative list
prices and require verification against current published rates.

---

## V. CONCLUSION AND FUTURE WORK

This paper presented a three-tier AWS architecture provisioned entirely through
Infrastructure as Code, in which data-tier isolation is enforced at the routing layer
and therefore robust to firewall misconfiguration, inter-tier access control is
expressed through security-group references that remain valid under elastic scaling,
and credentials are injected at runtime rather than stored. A stateful WebSocket
workload was selected to expose horizontal-scaling concerns that stateless workloads
conceal, addressed through session affinity and a Redis publish/subscribe backplane.
Cost was treated as a first-class design parameter, yielding an approximately 50 %
reduction in monthly expenditure for the demonstration configuration.

We additionally reported five classes of latent defect that passed every automated
validation gate, and argued that current IaC tooling verifies configurational
correctness while offering limited assurance of operational viability.

Future work comprises live deployment with empirical measurement of scaling latency,
failover time and availability; enabling TLS termination; migration of the deployment
pipeline to OIDC-federated credentials; reduction of the justified-skip set;
and replacement of static infrastructure assertions with behavioural testing using
`terraform test` or ephemeral-environment integration testing.

---

## REFERENCES

> ⚠️ **Verify every entry on IEEE Xplore / ACM DL / publisher site before submission.**
> Confirm authors, venue, year and page numbers. Do not submit an unverified citation.

[1] P. Mell and T. Grance, "The NIST definition of cloud computing," NIST Special
Publication 800-145, Gaithersburg, MD, USA, Sept. 2011.

[2] K. Morris, *Infrastructure as Code: Managing Servers in the Cloud*, 1st ed.
Sebastopol, CA, USA: O'Reilly Media, 2016.

[3] J. Humble and D. Farley, *Continuous Delivery: Reliable Software Releases through
Build, Test, and Deployment Automation*. Boston, MA, USA: Addison-Wesley, 2010.

[4] L. Bass, I. Weber, and L. Zhu, *DevOps: A Software Architect's Perspective*.
Boston, MA, USA: Addison-Wesley, 2015.

[5] S. Rose, O. Borchert, S. Mitchell, and S. Connelly, "Zero trust architecture," NIST
Special Publication 800-207, Gaithersburg, MD, USA, Aug. 2020.

[6] A. Rahman, C. Parnin, and L. Williams, "The seven sins: Security smells in
infrastructure as code scripts," in *Proc. IEEE/ACM 41st Int. Conf. Software
Engineering (ICSE)*, Montreal, QC, Canada, May 2019, pp. 164–175.

[7] M. Guerriero, M. Garriga, D. A. Tamburri, and F. Palomba, "Adoption, support, and
challenges of infrastructure-as-code: Insights from industry," in *Proc. IEEE Int.
Conf. Software Maintenance and Evolution (ICSME)*, Cleveland, OH, USA, Sept. 2019,
pp. 580–589.

[8] M. Shahin, M. A. Babar, and L. Zhu, "Continuous integration, delivery and
deployment: A systematic review on approaches, tools, challenges and practices," *IEEE
Access*, vol. 5, pp. 3909–3943, 2017.

[9] Y. Jiang and B. Adams, "Co-evolution of infrastructure and source code: An
empirical study," in *Proc. IEEE/ACM 12th Working Conf. Mining Software Repositories
(MSR)*, Florence, Italy, May 2015, pp. 45–55.

[10] A. Rahman and L. Williams, "Source code properties of defective infrastructure as
code scripts," *Information and Software Technology*, vol. 112, pp. 148–163, Aug. 2019.

[11] Amazon Web Services, "AWS well-architected framework," AWS Whitepaper, 2023.
[Online]. Available: https://docs.aws.amazon.com/wellarchitected/

[12] L. Zhu, L. Bass, and G. Champlin-Scharff, "DevOps and its practices," *IEEE
Software*, vol. 33, no. 3, pp. 32–34, May–June 2016.

[13] HashiCorp, "Terraform documentation." [Online]. Available:
https://developer.hashicorp.com/terraform/docs

[14] N. Dragoni *et al.*, "Microservices: Yesterday, today, and tomorrow," in *Present
and Ulterior Software Engineering*. Cham, Switzerland: Springer, 2017, pp. 195–216.

[15] C. Pahl, "Containerization and the PaaS cloud," *IEEE Cloud Computing*, vol. 2,
no. 3, pp. 24–31, May–June 2015.
