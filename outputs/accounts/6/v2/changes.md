# Changelog – Account 6

**Generated:** 2026-03-06 14:12

**Changes Applied:** 3
**Unknowns Resolved:** 0
**Unknowns Remaining:** 1

---

## Field Changes

### `emergency_routing_rules`
- **Before (v1):** `555-1000.`
- **After (v2):** `555-9999`
- **Reason:** Updated from onboarding call

### `call_transfer_rules`
- **Before (v1):** `Default: 30 second timeout – to be confirmed at onboarding`
- **After (v2):** `Fallback: 911 immediately if there is a fire risk, otherwise we will call them back in 15 minutes`
- **Reason:** Updated from onboarding call

### `integration_constraints`
- **Before (v1):** `[]`
- **After (v2):** `["Never schedule new breaker installations without an on-site quote first, tag all such jobs as 'Needs Review'", "tag all such jobs as 'Needs Review'"]`
- **Reason:** Updated from onboarding call

## Still Unknown (Action Required)
- ❓ emergency_definition: Emergency types not defined – confirm during onboarding
