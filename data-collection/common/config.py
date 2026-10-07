"""
Shared configuration for HireGuard data collection.

Everything scraped from BrighterMonday Kenya and Fuzu Kenya, and everything
loaded from EMSCAD, gets mapped into this single unified schema so the
downstream stylometric feature extraction pipeline (Chapter 3, Section 3.2.2)
can run over one consistent dataframe regardless of source.
"""

# Unified column schema used across all three data sources.
UNIFIED_COLUMNS = [
    "source",              # "emscad" | "brightermonday" | "fuzu"
    "source_id",           # original ID / URL slug from the source
    "title",
    "location",
    "department",
    "salary_range",
    "company_profile",
    "description",
    "requirements",
    "benefits",
    "employment_type",
    "required_experience",
    "required_education",
    "industry",
    "function",
    "telecommuting",
    "has_company_logo",
    "has_questions",
    "contact_email",
    "contact_email_domain",
    "is_free_email_provider",
    "posted_date",
    "url",
    "scraped_at",
    "fraudulent",          # 1 / 0 / "" (blank = needs manual annotation)
]

# Free/generic webmail providers. A posting listing one of these instead of
# a corporate domain is a documented fraud indicator (Naudé et al., 2023;
# Vidros et al., 2017) -- see Section 2.2.2 of the proposal.
FREE_EMAIL_PROVIDERS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com",
    "aol.com", "icloud.com", "protonmail.com", "mail.com", "yandex.com",
    "gmx.com", "zoho.com",
}

# Vague / over-promising vocabulary flagged in Section 2.2.1 -- useful for
# the manual annotation guide and later as a sanity check during feature
# engineering, not as a scraping filter.
URGENCY_OVERPROMISE_TERMS = [
    "urgent", "urgently", "guaranteed", "guarantee", "immediate start",
    "no experience needed", "earn daily", "earn weekly", "easy money",
    "work from home", "unlimited income", "act now", "limited slots",
]

REQUEST_HEADERS = {
    "User-Agent": (
        "HireGuardResearchBot/0.1 "
        "(Strathmore University FYP - Stylometric Fraud Detection Research; "
        "contact: melissa.ndeti@strathmore.edu)"
    ),
    "Accept-Language": "en-KE,en;q=0.9",
}

# Seconds to wait between requests. Keep this polite -- these are live
# production sites, not a sandbox. Increase if you see 429s.
REQUEST_DELAY_SECONDS = 3.0
REQUEST_TIMEOUT_SECONDS = 15
MAX_RETRIES = 3
