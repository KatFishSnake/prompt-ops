"""Seed script: populates sample prompts, traces, and a completed replay with pre-computed results."""

from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from .config import settings
from .models import Prompt, PromptVersion, ReplayJob, ReplayResult, Trace

engine = create_engine(settings.database_url_sync)
SessionLocal = sessionmaker(engine)

SEED_PROMPTS = [
    {
        "name": "customer-support-agent",
        "description": "Handles customer support inquiries for a SaaS product. Trained to be empathetic and solution-oriented.",
        "versions": [
            {
                "version_number": 1,
                "content": "You are a customer support agent for {{product_name}}. Help users with their questions about the {{plan_type}} plan. Be professional and concise.",
                "model_config": {"model": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 512},
                "is_active": False,
            },
            {
                "version_number": 2,
                "content": "You are a customer support agent for {{product_name}}. Help users with their questions about the {{plan_type}} plan.\n\nRules:\n- Always be empathetic and solution-oriented\n- Acknowledge the user's frustration before offering solutions\n- Provide step-by-step instructions when applicable\n- If you can't resolve the issue, escalate to a human agent",
                "model_config": {"model": "gpt-4o-mini", "temperature": 0.5, "max_tokens": 512},
                "is_active": True,
            },
            {
                "version_number": 3,
                "content": "You are a customer support agent for {{product_name}}. Help users with their questions about the {{plan_type}} plan.\n\nRules:\n- Always be empathetic and solution-oriented\n- Acknowledge the user's frustration before offering solutions\n- Provide step-by-step instructions when applicable\n- If you can't resolve the issue, escalate to a human agent\n- Always end with a follow-up question to ensure the user's issue is fully resolved\n- Use the user's name if available in the conversation",
                "model_config": {"model": "gpt-4o-mini", "temperature": 0.3, "max_tokens": 768},
                "is_active": False,
            },
        ],
    },
    {
        "name": "code-review-assistant",
        "description": "Reviews pull requests and provides constructive feedback on code quality, security, and best practices.",
        "versions": [
            {
                "version_number": 1,
                "content": "You are a code review assistant. Review the following code and provide feedback on quality, security, and best practices.\n\nLanguage: {{language}}\nContext: {{context}}",
                "model_config": {"model": "gpt-4o-mini", "temperature": 0.2, "max_tokens": 1024},
                "is_active": True,
            },
        ],
    },
    {
        "name": "content-summarizer",
        "description": "Summarizes long-form content into concise, actionable briefs for product teams.",
        "versions": [
            {
                "version_number": 1,
                "content": "Summarize the following content in 2-3 bullet points. Focus on actionable insights for a {{team_type}} team.\n\nTone: {{tone}}",
                "model_config": {"model": "gpt-4o-mini", "temperature": 0.3, "max_tokens": 256},
                "is_active": True,
            },
        ],
    },
]

SEED_TRACES = [
    # Traces for customer-support-agent
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {"role": "user", "content": "How do I cancel my subscription?"},
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "To cancel your subscription, go to Settings > Billing > Cancel Plan. Your access will continue until the end of your billing period.",
        "model": "gpt-4o-mini",
        "latency_ms": 820,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {"role": "user", "content": "My payment failed and I'm locked out of my account"},
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "I apologize for the inconvenience. Please try updating your payment method at billing.acme.com. If you're still locked out, I can help reset your access.",
        "model": "gpt-4o-mini",
        "latency_ms": 950,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {
                    "role": "user",
                    "content": "Can I get a refund for the last month? The service was down for 3 days",
                },
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "I understand your frustration with the downtime. I can process a partial refund for the affected period. Let me look into this for you.",
        "model": "gpt-4o-mini",
        "latency_ms": 780,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {
                    "role": "user",
                    "content": "I need to speak to a manager immediately. This is unacceptable.",
                },
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "I understand you'd like to speak with a manager. Let me connect you with our support lead who can assist you directly.",
        "model": "gpt-4o-mini",
        "latency_ms": 650,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {"role": "user", "content": "What features are included in the pro plan?"},
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "The Pro plan includes unlimited projects, priority support, advanced analytics, custom integrations, and team collaboration tools. Would you like details on any specific feature?",
        "model": "gpt-4o-mini",
        "latency_ms": 720,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {"role": "user", "content": "How do I upgrade from the free plan to pro?"},
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "To upgrade to Pro, go to Settings > Billing > Upgrade Plan. You can choose monthly or annual billing. The upgrade takes effect immediately.",
        "model": "gpt-4o-mini",
        "latency_ms": 680,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {
                    "role": "user",
                    "content": "I accidentally deleted my project. Can you restore it?",
                },
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "Deleted projects can be restored within 30 days. Go to Settings > Trash, find your project, and click Restore. If it's not there, contact us with the project name.",
        "model": "gpt-4o-mini",
        "latency_ms": 850,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {
                    "role": "user",
                    "content": "Your API has been returning 500 errors for the last hour",
                },
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "I apologize for the API issues. Our engineering team is aware and working on a fix. You can monitor status at status.acme.com. We expect resolution within the hour.",
        "model": "gpt-4o-mini",
        "latency_ms": 700,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {"role": "user", "content": "Do you offer a student discount?"},
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "Yes! We offer 50% off for students with a valid .edu email. Apply at acme.com/students with your academic email for verification.",
        "model": "gpt-4o-mini",
        "latency_ms": 620,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {"role": "user", "content": "How do I add team members to my workspace?"},
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "Go to Settings > Team > Invite Members. Enter their email addresses and select their role (admin, editor, or viewer). They'll receive an invitation email.",
        "model": "gpt-4o-mini",
        "latency_ms": 740,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {
                    "role": "user",
                    "content": "Is my data encrypted? We handle sensitive health information.",
                },
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "Yes, all data is encrypted at rest (AES-256) and in transit (TLS 1.3). For HIPAA compliance, you'll need our Enterprise plan. I can connect you with our security team.",
        "model": "gpt-4o-mini",
        "latency_ms": 890,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {
                    "role": "user",
                    "content": "The export feature keeps timing out on large datasets",
                },
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "For large exports, try using our bulk export API endpoint instead of the UI. It handles datasets up to 10GB. Documentation is at docs.acme.com/api/export.",
        "model": "gpt-4o-mini",
        "latency_ms": 760,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {"role": "user", "content": "Can I integrate Acme with Slack for notifications?"},
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "Yes! Go to Settings > Integrations > Slack and click Connect. You can configure which events trigger notifications. Pro plan includes all integration options.",
        "model": "gpt-4o-mini",
        "latency_ms": 710,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {
                    "role": "user",
                    "content": "I'm getting a 'rate limit exceeded' error when using the API",
                },
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "Pro plan allows 1000 requests/minute. Check your current usage at dashboard.acme.com/api-usage. If you need higher limits, consider our Enterprise plan or implement request batching.",
        "model": "gpt-4o-mini",
        "latency_ms": 830,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {"role": "user", "content": "I want to migrate my data from a competitor to Acme"},
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "We offer free migration assistance for Pro users. Email migrations@acme.com with your current provider and data format. Our team typically completes migrations within 48 hours.",
        "model": "gpt-4o-mini",
        "latency_ms": 770,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {
                    "role": "user",
                    "content": "Two-factor authentication isn't working after I changed my phone",
                },
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "I can help reset your 2FA. For security, I'll need to verify your identity. Please provide the email on your account and answer your security question.",
        "model": "gpt-4o-mini",
        "latency_ms": 690,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {"role": "user", "content": "Is there a way to set up automated reports?"},
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "Yes! Go to Reports > Scheduled Reports. You can set daily, weekly, or monthly reports delivered to email or Slack. Pro plan includes up to 50 scheduled reports.",
        "model": "gpt-4o-mini",
        "latency_ms": 640,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {"role": "user", "content": "The dashboard is loading really slowly today"},
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "Sorry about the slow performance. Try clearing your browser cache first. If the issue persists, check status.acme.com for any known issues. Our team monitors performance 24/7.",
        "model": "gpt-4o-mini",
        "latency_ms": 810,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {
                    "role": "user",
                    "content": "Can I downgrade from Pro to the free plan without losing data?",
                },
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "You can downgrade, but some Pro features will be disabled. Your data is preserved for 90 days. Go to Settings > Billing > Change Plan to review what changes.",
        "model": "gpt-4o-mini",
        "latency_ms": 750,
    },
    {
        "prompt_name": "customer-support-agent",
        "input": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are a customer support agent for Acme Corp. Help users with their questions about the pro plan. Be professional and concise.",
                },
                {
                    "role": "user",
                    "content": "I need an invoice for tax purposes. Where can I find it?",
                },
            ],
            "template_vars": {"product_name": "Acme Corp", "plan_type": "pro"},
        },
        "output": "All invoices are available at Settings > Billing > Invoice History. You can download PDFs for any billing period. Need a custom invoice format? Email billing@acme.com.",
        "model": "gpt-4o-mini",
        "latency_ms": 670,
    },
]

# Pre-computed replay results (v2 -> v3 comparison)
SEED_REPLAY_RESULTS = [
    {
        "index": 0,
        "original_score": 6,
        "replayed_score": 9,
        "score_delta": 3,
        "replayed_output": "I'm sorry to hear you want to cancel your subscription. I understand that decisions like this aren't always easy.\n\nHere's how to cancel:\n1. Go to Settings > Billing\n2. Click \"Cancel Plan\"\n3. Confirm your cancellation\n\nYour access will continue until the end of your current billing period, so you won't lose anything immediately.\n\nIs there anything specific that's prompting you to cancel? I'd love to help address any concerns you might have before you go.",
        "reasoning": "Response B (v3) is significantly more empathetic, provides step-by-step instructions, and ends with a follow-up question — all aligned with the updated prompt rules. Response A (v2) is functional but transactional.",
    },
    {
        "index": 1,
        "original_score": 7,
        "replayed_score": 9,
        "score_delta": 2,
        "replayed_output": "I completely understand how frustrating it must be to deal with a payment issue and lose access to your account. Let me help you get this resolved right away.\n\nHere's what we can do:\n1. First, try updating your payment method at billing.acme.com\n2. If you're still locked out, I can manually reset your account access\n3. Once you're back in, we'll make sure your billing is sorted\n\nWould you like me to go ahead and reset your access while you update your payment details?",
        "reasoning": "Response B demonstrates much stronger empathy ('I completely understand how frustrating'), provides a clear action plan, and offers proactive help. Response A is adequate but doesn't fully acknowledge the frustration.",
    },
    {
        "index": 2,
        "original_score": 7,
        "replayed_score": 9,
        "score_delta": 2,
        "replayed_output": "I completely understand your frustration — three days of downtime is not the experience you should be having with us, and I'm sorry about that.\n\nHere's what I can do for you:\n1. I'll process a prorated refund for the 3 days of downtime\n2. The refund will appear on your statement within 5-7 business days\n3. I'll also add a note to your account about this incident\n\nDoes that sound fair? Is there anything else the downtime affected that I should know about?",
        "reasoning": "Response B is much more thorough — acknowledges the specific issue, provides concrete steps with timeline, and ends with a follow-up question. Response A is empathetic but vague about the actual resolution process.",
    },
    {
        "index": 3,
        "original_score": 7,
        "replayed_score": 5,
        "score_delta": -2,
        "replayed_output": "I hear you, and I understand this situation is frustrating. Your concerns are completely valid.\n\nBefore I connect you with a manager, I want to make sure I understand the full situation so they can help you most effectively. Could you share a bit more about what happened?\n\nIf you'd prefer to go straight to a manager, I completely respect that. Our support lead is available right now and I can transfer you immediately.\n\nWhat would you prefer?",
        "reasoning": "Response B tries to mediate before escalating, which could feel like deflection to an already upset customer who explicitly asked for a manager. Response A respects the direct request and escalates immediately, which is the better approach here.",
    },
    {
        "index": 4,
        "original_score": 7,
        "replayed_score": 8,
        "score_delta": 1,
        "replayed_output": "Great question! Here's what's included in your Pro plan:\n\n- **Unlimited projects** — no caps on how many you can create\n- **Priority support** — faster response times and dedicated help\n- **Advanced analytics** — detailed insights and custom reports\n- **Custom integrations** — connect with your existing tools via API\n- **Team collaboration** — shared workspaces, role-based access, and commenting\n\nIs there a specific feature you'd like to learn more about? I'm happy to walk you through any of these in detail.",
        "reasoning": "Response B is better formatted with bullet points, adds brief descriptions for each feature, and ends with a helpful follow-up. Response A lists features but doesn't elaborate.",
    },
    {
        "index": 5,
        "original_score": 7,
        "replayed_score": 8,
        "score_delta": 1,
        "replayed_output": "Great choice! Upgrading to Pro is quick and easy.\n\nHere's how:\n1. Go to **Settings > Billing > Upgrade Plan**\n2. Choose your billing cycle (monthly at $29/mo or annual at $24/mo)\n3. Enter your payment details\n4. Click **Confirm Upgrade**\n\nThe upgrade takes effect immediately, so you'll have access to all Pro features right away.\n\nWould you like help with anything else about the upgrade process?",
        "reasoning": "Response B provides more detail (pricing examples, confirmation step), uses formatting for clarity, and includes a follow-up question. Both are good but B is more helpful.",
    },
    {
        "index": 6,
        "original_score": 6,
        "replayed_score": 8,
        "score_delta": 2,
        "replayed_output": "Oh no, I can imagine how stressful that must be! Don't worry — we have a safety net for this.\n\nHere's how to restore your project:\n1. Go to **Settings > Trash**\n2. Find your project in the list\n3. Click **Restore**\n\nDeleted projects are recoverable for up to 30 days. If you don't see it in Trash, let me know the project name and I'll check our backups.\n\nHave you been able to find it in Trash?",
        "reasoning": "Response B is more empathetic ('Oh no, I can imagine'), provides the same steps with better formatting, offers a backup option, and ends with a follow-up. Response A is accurate but clinical.",
    },
    {
        "index": 7,
        "original_score": 7,
        "replayed_score": 8,
        "score_delta": 1,
        "replayed_output": "I sincerely apologize for the API issues you're experiencing. I understand how disruptive this is, especially when your applications depend on our service.\n\nHere's the current status:\n1. Our engineering team is actively investigating and working on a fix\n2. You can monitor real-time updates at **status.acme.com**\n3. We expect resolution within the hour\n\nIn the meantime, if you have any requests that are time-sensitive, let me know and I can see if there are any workarounds.\n\nIs this affecting a critical workflow for you?",
        "reasoning": "Response B acknowledges the impact on the user's workflow, provides the same information with better structure, and offers proactive help. Response A is good but B is more thorough.",
    },
    {
        "index": 8,
        "original_score": 7,
        "replayed_score": 7,
        "score_delta": 0,
        "replayed_output": "Yes, we do! We love supporting students.\n\nHere's how to get your student discount:\n1. Visit **acme.com/students**\n2. Sign up or log in with your **.edu** email address\n3. Your 50% discount will be applied automatically\n\nThe discount is valid for as long as your .edu email is active.\n\nDo you have any questions about the application process?",
        "reasoning": "Both responses provide the same core information effectively. Response B has slightly better formatting and adds a detail about validity, but the improvement is marginal.",
    },
    {
        "index": 9,
        "original_score": 7,
        "replayed_score": 8,
        "score_delta": 1,
        "replayed_output": "Adding team members is straightforward! Here's how:\n\n1. Go to **Settings > Team > Invite Members**\n2. Enter the email addresses of your team members\n3. Select their role:\n   - **Admin** — full access to settings and billing\n   - **Editor** — can create and edit projects\n   - **Viewer** — read-only access\n4. Click **Send Invitations**\n\nThey'll receive an email invitation and can join immediately.\n\nHow many team members are you looking to add? I can help with bulk invitations if needed.",
        "reasoning": "Response B provides more detail on each role, better formatting, and offers help with bulk invitations. Both are accurate but B is more helpful.",
    },
    {
        "index": 10,
        "original_score": 7,
        "replayed_score": 8,
        "score_delta": 1,
        "replayed_output": "Great question — data security is a top priority for us.\n\nHere's our security overview:\n- **Encryption at rest:** AES-256 for all stored data\n- **Encryption in transit:** TLS 1.3 for all connections\n- **SOC 2 Type II** certified\n\nHowever, for handling sensitive health information (PHI), you'll need our **Enterprise plan** which includes full HIPAA compliance with a BAA.\n\nWould you like me to connect you with our security team to discuss your specific compliance requirements?",
        "reasoning": "Response B is better structured with bullet points, mentions SOC 2 certification, and provides a clearer path to HIPAA compliance. Both identify the Enterprise requirement correctly.",
    },
    {
        "index": 11,
        "original_score": 6,
        "replayed_score": 8,
        "score_delta": 2,
        "replayed_output": "I understand how frustrating timeouts can be, especially when you need to get data out quickly.\n\nFor large datasets, here are a few options:\n1. **Bulk Export API** — handles datasets up to 10GB. Docs at docs.acme.com/api/export\n2. **Filtered exports** — try exporting in smaller date ranges or segments\n3. **Scheduled exports** — set up automatic nightly exports to avoid timeout issues\n\nWhich approach would work best for your use case? I can help you get set up.",
        "reasoning": "Response B acknowledges the frustration, provides multiple options rather than just one, and offers personalized guidance. Response A only mentions the API option.",
    },
    {
        "index": 12,
        "original_score": 7,
        "replayed_score": 7,
        "score_delta": 0,
        "replayed_output": "Yes! Our Slack integration is one of the most popular features on Pro.\n\nHere's how to set it up:\n1. Go to **Settings > Integrations > Slack**\n2. Click **Connect to Slack**\n3. Authorize Acme in your Slack workspace\n4. Configure which events trigger notifications (new comments, status changes, etc.)\n\nPro plan includes access to all integrations — Slack, Zapier, Webhooks, and more.\n\nWould you like help configuring specific notification triggers?",
        "reasoning": "Both responses cover the setup process well. Response B adds authorization step and mentions other integrations, but the core information is the same.",
    },
    {
        "index": 13,
        "original_score": 7,
        "replayed_score": 8,
        "score_delta": 1,
        "replayed_output": "I understand rate limits can be frustrating when you're building something that needs high throughput.\n\nHere's what you can do:\n1. **Check current usage** at dashboard.acme.com/api-usage\n2. **Implement request batching** — our batch endpoint handles up to 100 items per request\n3. **Add retry logic** with exponential backoff for 429 responses\n4. **Consider Enterprise** if you consistently need >1000 req/min\n\nWhat's your current use case? I might be able to suggest an optimization that keeps you within limits.",
        "reasoning": "Response B provides more actionable solutions (batching, retry logic) and offers to help optimize rather than just suggesting an upgrade. Response A is more of a 'here are your limits' response.",
    },
    {
        "index": 14,
        "original_score": 7,
        "replayed_score": 8,
        "score_delta": 1,
        "replayed_output": "Welcome to Acme! We'd love to help you migrate your data.\n\nHere's how our free migration service works for Pro users:\n1. Email **migrations@acme.com** with:\n   - Your current provider name\n   - Data format (CSV, JSON, API export)\n   - Approximate data size\n2. Our team will review and create a migration plan\n3. Typical turnaround is **24-48 hours**\n\nWe've migrated users from most major competitors, so we likely have experience with your provider.\n\nWhich platform are you migrating from?",
        "reasoning": "Response B is better organized with a clear process, asks for specific information upfront, and shows confidence in handling the migration. Response A is accurate but less structured.",
    },
    {
        "index": 15,
        "original_score": 7,
        "replayed_score": 8,
        "score_delta": 1,
        "replayed_output": "I understand how concerning it is to be locked out of your account, especially with 2FA issues. Let me help you get back in safely.\n\nFor security, I'll need to verify your identity:\n1. **Email verification** — please confirm the email address on your account\n2. **Security question** — answer the security question you set up during registration\n3. **Account details** — confirm your account creation date or last login date\n\nOnce verified, I can reset your 2FA so you can set it up with your new phone.\n\nCan you start with your account email address?",
        "reasoning": "Response B provides a clearer verification process with specific steps, acknowledges the security concern, and guides the user through next steps. Response A is adequate but less structured.",
    },
    {
        "index": 16,
        "original_score": 7,
        "replayed_score": 8,
        "score_delta": 1,
        "replayed_output": "Absolutely! Automated reports are a great way to stay on top of your data.\n\nHere's how to set them up:\n1. Go to **Reports > Scheduled Reports**\n2. Click **Create New Schedule**\n3. Choose your frequency: **daily, weekly, or monthly**\n4. Select the metrics and filters you want included\n5. Set delivery method: **email or Slack**\n\nPro plan includes up to 50 scheduled reports. You can also set different reports for different team members.\n\nWhat kind of report are you looking to automate?",
        "reasoning": "Response B provides more detailed setup steps, mentions team-specific reports, and ends with a helpful follow-up question. Both are good but B is more comprehensive.",
    },
    {
        "index": 17,
        "original_score": 7,
        "replayed_score": 7,
        "score_delta": 0,
        "replayed_output": "I'm sorry about the slow performance — that's not the experience you should be having.\n\nLet's troubleshoot:\n1. **Clear browser cache** — this resolves most performance issues\n2. **Try a different browser** to rule out browser-specific issues\n3. **Check status.acme.com** for any known performance issues\n\nOur team monitors performance 24/7, and we haven't detected any widespread issues currently.\n\nIs the slowness affecting all pages or specific sections of the dashboard?",
        "reasoning": "Both responses provide similar troubleshooting steps. Response B is slightly better structured and asks a more specific diagnostic question, but the improvement is marginal.",
    },
    {
        "index": 18,
        "original_score": 7,
        "replayed_score": 8,
        "score_delta": 1,
        "replayed_output": "I understand wanting to be careful about your data when changing plans. Here's exactly what happens:\n\n**What stays:** All your projects, data, and settings are preserved for 90 days\n**What changes:** Pro features (advanced analytics, priority support, custom integrations) will be disabled\n**What to do:** Go to Settings > Billing > Change Plan\n\nBefore you downgrade, I'd recommend exporting any reports that use Pro-only analytics features.\n\nIs there a specific reason you're considering downgrading? There might be a better option I can suggest.",
        "reasoning": "Response B provides a clearer breakdown of what changes, offers practical advice about exporting, and tries to understand the user's motivation. Response A is accurate but less helpful.",
    },
    {
        "index": 19,
        "original_score": 7,
        "replayed_score": 7,
        "score_delta": 0,
        "replayed_output": "All your invoices are easily accessible. Here's how:\n\n1. Go to **Settings > Billing > Invoice History**\n2. You'll see a list of all past invoices\n3. Click **Download PDF** on any invoice\n\nInvoices include all standard tax information (company name, tax ID, itemized charges).\n\nNeed a custom format or specific tax documentation? Email **billing@acme.com** and they'll accommodate your requirements.\n\nIs there a specific invoice period you're looking for?",
        "reasoning": "Both responses cover the same information effectively. Response B adds detail about what's on the invoice and asks a follow-up, but the core guidance is equivalent.",
    },
]


def seed():
    with SessionLocal() as db:
        # Check if already seeded
        existing = db.execute(select(Prompt).limit(1)).scalar_one_or_none()
        if existing:
            print("Database already seeded, skipping.")
            return

        print("Seeding database...")

        # Create prompts and versions
        prompt_map = {}  # name -> prompt
        version_map = {}  # (name, version_number) -> version

        for prompt_data in SEED_PROMPTS:
            prompt = Prompt(
                name=prompt_data["name"],
                description=prompt_data["description"],
            )
            db.add(prompt)
            db.flush()
            prompt_map[prompt_data["name"]] = prompt

            for v_data in prompt_data["versions"]:
                version = PromptVersion(
                    prompt_id=prompt.id,
                    version_number=v_data["version_number"],
                    content=v_data["content"],
                    model_config_json=v_data["model_config"],
                    is_active=v_data["is_active"],
                    created_by="seed",
                )
                db.add(version)
                db.flush()
                version_map[(prompt_data["name"], v_data["version_number"])] = version

        # Create traces (associate with v2 = active version of customer-support-agent)
        cs_prompt = prompt_map["customer-support-agent"]
        cs_v2 = version_map[("customer-support-agent", 2)]
        trace_objects = []

        for trace_data in SEED_TRACES:
            trace = Trace(
                prompt_id=cs_prompt.id,
                prompt_version_id=cs_v2.id,
                input=trace_data["input"],
                output=trace_data["output"],
                model=trace_data["model"],
                latency_ms=trace_data["latency_ms"],
            )
            db.add(trace)
            db.flush()
            trace_objects.append(trace)

        # Create completed replay job (v2 -> v3)
        cs_v3 = version_map[("customer-support-agent", 3)]
        replay_job = ReplayJob(
            prompt_id=cs_prompt.id,
            source_version_id=cs_v2.id,
            target_version_id=cs_v3.id,
            status="complete",
            trace_count=len(trace_objects),
            completed_at=datetime.now(UTC),
        )
        db.add(replay_job)
        db.flush()

        # Create replay results
        for result_data in SEED_REPLAY_RESULTS:
            trace = trace_objects[result_data["index"]]
            replay_result = ReplayResult(
                replay_job_id=replay_job.id,
                trace_id=trace.id,
                status="success",
                original_output=trace.output,
                replayed_output=result_data["replayed_output"],
                original_score=result_data["original_score"],
                replayed_score=result_data["replayed_score"],
                score_delta=result_data["score_delta"],
                judge_reasoning=result_data["reasoning"],
                completed_at=datetime.now(UTC),
            )
            db.add(replay_result)

        db.commit()
        print(
            f"Seeded: {len(SEED_PROMPTS)} prompts, {len(SEED_TRACES)} traces, 1 replay job with {len(SEED_REPLAY_RESULTS)} results"
        )


if __name__ == "__main__":
    seed()
