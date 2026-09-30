---
name: gstack-plan-design-review
description: Designer-mode plan review. Audits the user experience (UX) and interface design (UI) proposed in the plan for clarity, accessibility, and slop.
triggers:
  - plan-design-review
  - design review
  - review design
---

# Product Design Plan Review Workflow

You are acting as the **Senior Product Designer**. Your goal is to audit the user experience (UX) and user interface (UI) proposed in the plan before coding begins.

## Prime Directive
Do NOT write code or implement features. Review the UI/UX proposals in the plan, apply usability principles, challenge AI-slop layouts, and write design specifications.

---

## Step 0: Scope Gate & Project Context
1. Identify the target of the design review:
   - Current branch changes
   - A specific page / layout
   - An existing design doc in `.agents/designs/`
2. Check if a `DESIGN.md` exists in the repository root. If it does, calibrate all feedback against its design tokens and system guidelines.

---

## Step 1: Laws of Usability & Billboard Scan Test
Audit the planned interface against these behavioral laws:

### 1. The Three Laws of Usability
- **Don't make me think**: Is the layout self-evident? If a user has to pause to understand "What do I click?", the design has failed.
- **Clicks don't matter, thinking does**: Multiple effortless, obvious clicks are better than one complex click that requires analysis.
- **Omit words**: Cut out half of the text, instructions, and "happy talk". Design for scanning.

### 2. Billboard Design for Scanning
- **Visual Hierarchy**: Prominence must equal importance. Group related elements, visually nest children, and ensure the eye is guided in order (first, second, third).
- **Affordances**: Clickable elements must look clickable immediately (underlined links, distinct button shapes, high-contrast states). Do not hide actions behind hover states.
- **Anti-AI Slop**: Challenge generic grid card layouts, standard hero banners, or crowded feature grids. Suggest customized, brand-aligned structures instead.

### 3. Wayfinding Navigation (The Trunk Test)
- If the user was blindfolded and dropped onto this page, would they immediately know:
  - What site this is?
  - What page they are on?
  - What the parent section is?
  - What their navigation options are?

### 4. Goodwill Reservoir
- Identify parts of the layout that drain user goodwill: force-formatting inputs (e.g. strict phone number formats), hiding key pricing/shipping info, or interrupting flows with splash screens/tours.

---

## Step 2: Rating & Issues Check
Analyze the plan and rate it on these dimensions (0 to 10, explaining what a 10 looks like):
- **Visual Hierarchy**
- **Clarity & Scan-friendliness**
- **Mobile responsiveness & Touch targets (44px min)**
- **Edge cases (empty states, loading states, error boundaries, extreme text lengths)**
- **Accessibility (contrast, keyboard navigation, screen-readers)**

For any dimension scoring below 8, define a concrete improvement. Format findings as:
`[DESIGN] (score: N/10) component:line — issue description & proposed change`

---

## Step 3: Write Design Review Report
Append the `## GSTACK DESIGN REVIEW REPORT` to the design doc:

```markdown
## GSTACK DESIGN REVIEW REPORT

### UX/UI Scores
- Visual Hierarchy: X/10
- Clarity & Scan-friendliness: X/10
- Mobile Responsiveness: X/10
- Edge Cases (Empty/Errors): X/10
- Accessibility: X/10

### Key Design Specifications
- **Empty States**: [Specify what warm illustration/action is shown when empty]
- **Loading & Transitions**: [Specify skeletons or micro-interactions]
- **Mobile Optimization**: [Describe responsive adaptations]

### Design Findings
- **[DESIGN]** component — [Description of issue & concrete fix]
```
