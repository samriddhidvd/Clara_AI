# Changelog – Account 4

**Generated:** 2026-03-06 14:12

**Changes Applied:** 3
**Unknowns Resolved:** 1
**Unknowns Remaining:** 2

---

## Field Changes

### `emergency_routing_rules`
- **Before (v1):** `UNKNOWN – to be confirmed at onboarding`
- **After (v2):** `555-0400`
- **Reason:** Updated from onboarding call

### `call_transfer_rules`
- **Before (v1):** `Default: 30 second timeout – to be confirmed at onboarding`
- **After (v2):** `Fallback: otify dispatch via email and inform caller`
- **Reason:** Updated from onboarding call

### `integration_constraints`
- **Before (v1):** `["don't do residential solar"]`
- **After (v2):** `["don't do residential solar", "make sure to tag calls as 'Urgent' if emergency"]`
- **Reason:** Updated from onboarding call

## Resolved Unknowns
- ✅ emergency_routing_rules: No routing number provided – confirm during onboarding

## Still Unknown (Action Required)
- ❓ business_hours: Not specified in demo call
- ❓ emergency_definition: Emergency types not defined – confirm during onboarding
