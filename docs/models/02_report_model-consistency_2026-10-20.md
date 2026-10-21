# Model consistency check – UML models v1 (2026-10-20)

**Script:** `02_check_model-consistency_2026-10-20.py`, which reads the PlantUML sources and `01_Requirements/EkteMat_backlog_v1.xlsx`.

**Run:**

```
python3 02_check_model-consistency_2026-10-20.py ../01_Requirements/EkteMat_backlog_v1.xlsx \
  02_uml_use-case-diagram_2026-10-20.puml 02_uml_class-diagram_2026-10-20.puml \
  02_uml_sequence-recurring-lunch-ehf_2026-10-20.puml 02_uml_state-machine-order_2026-10-20.puml
```

**Scope:** 27 use cases, 13 sequence participants, 28 classifiers in the class diagram (19 classes and 9 enums), 33 Must/Should stories and 9 Order states.

| Check | Rule | Result |
|---|---|---|
| C1 | Every use case traces to at least 1 Must/Should user story | **1 violation** |
| C2 | Every class used in the sequence diagram exists in the class diagram | **3 violations** |
| C3 (extra) | Every Must/Should story is covered by at least 1 use case | 0 – all 33 covered |
| C4 (extra) | Order states and the `OrderStatus` enum match one to one | 0 – 9 states = 9 values |

## Violations

| # | Check | Element | Problem | Why it happens | Proposed fix |
|---|---|---|---|---|---|
| V1 | C1 | UC05 Accept quote online | No user story behind it | The step comes from the TO-BE BPMN ("Accept quote online"). The backlog assumed acceptance by e-mail, so no story covers it | Add **US-40** "As a customer I want to accept a quote online so that my booking is confirmed without e-mail" (Must, since the TO-BE process depends on it). Otherwise remove UC05 and keep acceptance outside the system |
| V2 | C2 | `web : OrderingUI` (boundary) | Not in the class diagram | Boundary class from the entity–control–boundary (ECB) style. The class diagram is a pure domain model | Keep it out of the domain model, and add it to a separate analysis/design class diagram with `<<boundary>>` |
| V3 | C2 | `inv : InvoicingService` (control) | Not in the class diagram | Control class that orchestrates month-end invoicing (US-23, US-24) | Same as V2: put it in the design class diagram as `<<control>>` |
| V4 | C2 | `fiken : FikenAPI` (external) | Not in the class diagram | Fiken is an external system, shown as an actor in the use case diagram | Model `FikenAPI` as an `<<interface>>` in the design model (it is the adapter we call), or show Fiken as an actor in the sequence diagram |

Actors with no class type (`Scheduler`, `Fjordtek finance`) were skipped by C2. `henrik : CompanyUser` matched the `CompanyUser` class.

**Decision needed from the team:** C2 assumes the sequence diagram uses only domain classes. If we accept ECB-style sequence diagrams, V2–V4 become warnings and only V1 has to be fixed.
