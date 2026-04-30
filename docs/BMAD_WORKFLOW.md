# BMAD — Workflow & usage dans ce repo

Ce dépôt contient des **skills BMAD** (fichiers `SKILL.md`) utilisés pour structurer le travail (requirements, architecture, stories, QA, docs).

## Où sont les skills

- `Trading_app_version4/.claude/skills/bmad-*` : skills BMAD “produit / delivery”
- `~/.cursor/skills-cursor/*` : skills Cursor (canvas, rules, hooks, etc.)

## Quand utiliser BMAD

BMAD est surtout utile quand :
- La demande est **ambigüe** ou nécessite de **clarifier** (ex: PRD / Product Brief).
- On veut produire des artefacts “livrables” : **PRD**, **UX spec**, **Architecture**, **Epics & stories**, **Test plan**, **Docs**.
- On veut une **revue critique structurée** (edge cases, adversarial review).

Pour un **petit fix** ou une feature simple, on peut coder directement sans BMAD.

## Skills BMAD utiles (exemples)

- **Produit / cadrage**
  - `bmad-product-brief`, `bmad-create-prd`, `bmad-edit-prd`, `bmad-validate-prd`
- **UX / design**
  - `bmad-create-ux-design`, `bmad-agent-ux-designer`
- **Architecture**
  - `bmad-create-architecture`, `bmad-agent-architect`
- **Delivery**
  - `bmad-create-epics-and-stories`, `bmad-create-story`, `bmad-dev-story`
- **QA**
  - `bmad-testarch-test-design`, `bmad-qa-generate-e2e-tests`, `bmad-agent-qa`
- **Revue / critique**
  - `bmad-code-review`, `bmad-review-edge-case-hunter`, `bmad-review-adversarial-general`

## Comment je l’utilise en pratique (avec toi)

Tu peux me dire explicitement :
- “**Utilise BMAD** pour cadrer cette feature” (je choisis le bon skill, je produis les artefacts).
- “**Code direct**” (je code en suivant l’architecture et les patterns du repo).

## Notes

- BMAD n’est pas “obligatoire” : c’est un outil d’**organisation** et de **qualité**.
- Les décisions finales (scope, trade-offs) restent celles du projet : BMAD sert à rendre tout plus clair et actionnable.

