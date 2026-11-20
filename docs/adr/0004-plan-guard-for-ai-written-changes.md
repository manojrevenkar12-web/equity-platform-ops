# 0004: A guard on Terraform plans, stricter for AI-written changes

**Status:** accepted

**Context.** A third of infrastructure changes are written with an AI assistant. Reviewing every change by hand
costs 20 hours a week and still lets tired reviewers miss things; merging AI-written changes on green CI applies
most of the harmful ones, because CI checks syntax, not intent.

**Decision.** Read the plan (`terraform show -json`), not the diff: rules block what is never right, send what
needs judgement to a person, and apply the rest. AI-written changes (by the `Co-Authored-By` trailer) go to a
person whenever they touch IAM or score above a lower risk threshold.

**Result (development orgs).** 1 of 62 harmful changes applied, against 19 with every change reviewed and 48
with AI changes on green CI; review time 4.5 hours a week.

**What the AI tier is worth.** Without it, 2 of 62 harmful changes applied and review takes 0.9 hours a week. One
change in 24 org-weeks for 3.6 hours a week is a close call; it is kept because the changes it catches are
access changes (cross-project impersonation), the kind that is expensive when it is missed. Revisit after a
quarter of real data.

**Limits.** The rules miss what they do not describe; the subtle harmful kinds in the world exist to show that.

**Held-out orgs (run once).** 5 of 71 harmful changes applied on the platform, 7 of 71 without the AI tier, 25 of
71 with every change reviewed by a person and 46 of 71 with AI changes on green CI. The tier stopped two more
there, for about 4 hours of review a week.
