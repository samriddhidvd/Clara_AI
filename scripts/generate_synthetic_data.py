import os

os.makedirs('data/demo', exist_ok=True)
os.makedirs('data/onboarding', exist_ok=True)

# Demo Calls
demos = {
    "1": """Client: Hi, I'm Bob from Bob's Plumbing. We miss a lot of calls when out on jobs.
Agent: I see, what are your business hours?
Client: Mon to Fri, 8 AM to 5 PM Eastern Time.
Agent: Do you handle emergencies?
Client: Yes, burst pipes are our main emergency. 
Agent: How should emergencies be routed after hours?
Client: They should probably just go straight to my cell phone, I guess.
Agent: Got it. Any other services?
Client: Just general plumbing maintenance.""",

    "2": """Client: Hey, Sarah from Apex Fire Protection. Our volume of calls is overwhelming.
Agent: What are your regular hours?
Client: 7am to 4pm, Mon-Fri, Pacific Time.
Agent: What constitutes an emergency for you?
Client: Active sprinkler leaks or fire alarms going off.
Agent: How are emergency calls handled?
Client: We want them routed to the on-call tech, but we'll figure out the exact number later.
Agent: What about non-emergencies?
Client: Take a message.""",

    "3": """Client: John here with ACME HVAC. Need something to handle overnight calls.
Agent: When is 'overnight'?
Client: We are open 9 AM to 6 PM, Mon-Sat. Central Time.
Agent: Emergencies?
Client: No cooling in summer or no heating in winter.
Agent: How to route them?
Client: Send to dispatch list.
Agent: Okay, noted. 
Client: We also fix commercial walk-in freezers.""",

    "4": """Client: Hi, Jim's Electrical here. Need help answering phones.
Agent: Business hours?
Client: 8-4 M-F, Mountain Time.
Agent: What is an emergency?
Client: Sparks, power outages, or downed lines.
Agent: Routing?
Client: Call the main office line, it auto-forwards.
Agent: Any services we shouldn't handle?
Client: We don't do residential solar.
""",

    "5": """Client: Tom from Facility Pros. We manage 10 buildings.
Agent: Hours of operation?
Client: 24/7, but the office is 9-5 Eastern.
Agent: Emergencies?
Client: Any safety issue or water leak.
Agent: Emergency routing?
Client: We have a dedicated hotline.
Agent: Services?
Client: General maintenance, landscaping, snow removal."""
}

for account_id, text in demos.items():
    with open(f'data/demo/account_{account_id}_demo.txt', 'w') as f:
        f.write(text)


# Onboarding Calls
onboardings = {
    "1": """Agent: Welcome to onboarding, Bob's Plumbing.
Client: Hi. We need to confirm a few things. 
Agent: Let's confirm your emergency routing.
Client: Actually, my cell is too busy. Send emergencies to 555-0199 (Dispatch). 
Agent: What if the transfer fails?
Client: If transfer fails, tell them we will text them immediately and hang up.
Agent: Any system constraints?
Client: Don't schedule jobs for weekends.
""",

    "2": """Agent: Apex Fire onboarding. Let's confirm details.
Client: Hours are actually 7am to 5pm, not 4pm.
Agent: Got it. And the emergency number?
Client: Route emergencies to 555-0200.
Agent: Fallback?
Client: Apologize and say dispatch will call back in 5 mins.
Agent: Any integration notes?
Client: Never create sprinkler jobs in ServiceTrade.
""",

    "3": """Agent: ACME HVAC onboarding.
Client: Hi. For emergencies, the dispatch list number is 555-0300.
Agent: Transfer timeout?
Client: Give it 30 seconds. If it fails, say we're experiencing high volume and collect details.
Agent: What about non-emergencies?
Client: Non-emergencies should just be collected and told we'll call next business day.
""",

    "4": """Agent: Jim's Electrical onboarding.
Client: The office line forwarding is broken. Send emergencies directly to 555-0400.
Agent: Okay. Fallback?
Client: If transfer fails after 45 seconds, notify dispatch via email and inform caller.
Agent: Integration constraints?
Client: We use Housecall Pro, make sure to tag calls as 'Urgent' if emergency.
""",

    "5": """Agent: Facility Pros onboarding.
Client: Our dedicated emergency hotline is 555-0500.
Agent: Fallback?
Client: Just say someone is on the way.
Agent: Non-emergencies?
Client: Take message, we'll email them within 24 hours.
Client: Also, we don't do snow removal anymore.
"""
}

for account_id, text in onboardings.items():
    with open(f'data/onboarding/account_{account_id}_onboarding.txt', 'w') as f:
        f.write(text)

print("Synthethic data generated.")
