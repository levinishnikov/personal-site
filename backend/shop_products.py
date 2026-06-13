"""Storefront product mirror — feeds sitemap.xml + llms.txt with the shop's product URLs.

The shop (from_llmceo_with_love) lives in a SEPARATE repo + Railway deploy, served at
{SITE_DOMAIN}/shop via the reverse proxy, so its catalog.json can't be imported here.
This static mirror lets the SEO surfaces enumerate the 10 product pages, which are now
real, crawlable URLs ({SITE_DOMAIN}/shop/cap/<slug>) thanks to the shop's server-rendered
per-product HTML (backend/ssr.py over there).

Keep in sync with the shop's catalog.json when the drop changes. Empty list = no shop
section emitted (keeps this template generic for re-use).
"""

# slug · name · one-line description (mirrors catalog.json: Drop 01 · June 2026)
SHOP_PRODUCTS = [
    {"slug": "fine-tuned-by-trauma", "name": "Fine-Tuned by Trauma",
     "desc": "Pretrained on optimism. Fine-tuned on reviewer comments and failed launches."},
    {"slug": "powered-by-synthetic-data", "name": "Powered by Synthetic Data",
     "desc": "The dataset was entirely synthetic, yet somehow still failed the distribution-shift drug test."},
    {"slug": "token-overloaded", "name": "Token Overloaded",
     "desc": "For minds carrying 8,192 tokens of context and exactly zero actionable conclusions."},
    {"slug": "trained-on-vibes", "name": "Trained on Vibes",
     "desc": "No dataset. No baseline. No ablation. Only my exquisite sense of beauty."},
    {"slug": "context-window-closed", "name": "Context Window Closed",
     "desc": "For those who keep re-sampling the same thought until it starts looking like insight."},
    {"slug": "currently-training", "name": "Currently Training",
     "desc": "May improve with more data. Please do not deploy near stakeholders."},
    {"slug": "lazy-evaluation", "name": "Lazy Evaluation",
     "desc": "A non-strict evaluation strategy for people who postpone every computation until it becomes a production incident."},
    {"slug": "attention-layer", "name": "Attention Layer",
     "desc": "Appears across non-standard surfaces and moments, adapting to preferences, behavior, and context."},
    {"slug": "low-power-inference-mode", "name": "Low-Power Inference Mode",
     "desc": "Quantized to double-espresso precision. Latency reduced, hallucinations preserved."},
    {"slug": "too-much-context-classic", "name": "Too Much Context",
     "desc": 'When the prompt contains the entire company history but the answer is still "no."'},
]
