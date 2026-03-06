# Changelog – Account 2

**Generated:** 2026-03-06 14:12

**Changes Applied:** 4
**Unknowns Resolved:** 0
**Unknowns Remaining:** 1

---

## Field Changes

### `business_hours`
- **Before (v1):** `7am to 4pm, Mon-Fri, Pacific Time Pacific`
- **After (v2):** `actually 7am to 5pm, not 4pm`
- **Reason:** Updated from onboarding call

### `emergency_routing_rules`
- **Before (v1):** `te`
- **After (v2):** `555-0200`
- **Reason:** Updated from onboarding call

### `call_transfer_rules`
- **Before (v1):** `Default: 30 second timeout – to be confirmed at onboarding`
- **After (v2):** `Fallback: Client: Apologize and say dispatch will call back in 5 mins`
- **Reason:** Updated from onboarding call

### `integration_constraints`
- **Before (v1):** `[]`
- **After (v2):** `['Never create sprinkler jobs in ServiceTrade']`
- **Reason:** Updated from onboarding call

## Still Unknown (Action Required)
- ❓ emergency_definition: Emergency types not defined – confirm during onboarding
