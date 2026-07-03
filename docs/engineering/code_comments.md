# Code comments standard

City GO code should explain product intent, boundaries, and non-obvious decisions. It should not add comments that merely repeat the code.

## Required

Add a module docstring or leading comment when a file defines:

- route eligibility policy;
- data quality gates;
- production smoke checks;
- public/admin visibility rules;
- city catalogue counters;
- import, recompute, or audit scripts;
- workflow logic.

Add function comments when a function:

- separates similar product concepts, such as catalogue visibility vs route eligibility;
- applies fail-closed behavior;
- intentionally accepts weak or partial output instead of forcing success;
- changes production data;
- is used by CI, smoke, admin checks, or recompute scripts.

## Avoid

Do not add comments that only restate syntax, simple variable assignments, obvious mappings, or simple UI rendering.

## Current notes

- `/cities/available` counters are catalogue counters and must not be reused as route-eligible counters.
- Public route controls must hide route-blocked categories even when those categories remain part of the city catalogue.
- Production smoke must stay dependency-free and must validate route quality, not only HTTP availability.
- Route assembly must prefer honest weak or partial routes over fake success with large budget overflow.
