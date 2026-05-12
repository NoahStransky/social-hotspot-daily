# Google Analytics 4 & AdSense Integration Plan

## 1. Overview

This document provides the complete plan for integrating **Google Analytics 4 (GA4)** and **Google AdSense** into the **Social Hotspot Daily** static site (`hotspot.edgesoft.org`).

### Current Architecture

- **Static site repo**: `github.com/NoahStransky/social-hotspot-daily`
- **Hosting**: GitHub Pages, proxied through Cloudflare (custom domain `hotspot.edgesoft.org`)
- **Generation**: Python/Jinja2 `blog_generator.py` → renders `templates/blog.html` → outputs `docs/index.html`
- **Templates**: `templates/blog.html` (main blog), `templates/subscribe.html`, `templates/verify.html`, `templates/unsubscribe.html`
- **Cloudflare Worker**: `hotspot.edgesoft.org/api/*` handles newsletter subscriptions
- **Dark mode**: Yes, the site uses a dark-only theme (`--bg: #0a0a0f`)

---

## 2. Google Analytics 4 (GA4) Integration

### 2.1 What You Need (Prerequisites)

1. **Google Analytics account** → Create at `analytics.google.com`
2. **GA4 Property** → Create a new property for the site
3. **Measurement ID** → Format: `G-XXXXXXXXXX` (starts with `G-` followed by 10 alphanumeric chars)
   - Find it in: Admin → Data Streams → Web → Your stream → Measurement ID

### 2.2 How GA4 Works on Static Sites

GA4 uses **gtag.js** (Google Tag) — a single JavaScript snippet loaded in the `<head>`. It's a completely client-side integration, perfect for static sites. No server-side changes needed.

The snippet:
1. Loads the gtag.js library from `https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX`
2. Initializes the GA4 data layer
3. Automatically tracks: page views, sessions, scroll depth, outbound clicks, site search, and more

### 2.3 GA4 Code Snippet

```html
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

### 2.4 Handling Dark Mode with GA4

No special GA4 configuration is needed for dark mode. GA4 doesn't care about site color schemes.

### 2.5 GA4 + Cloudflare Considerations

- **Cloudflare proxying is transparent** to GA4. The requests from the browser to `www.googletagmanager.com` go directly (not through Cloudflare), so there's no conflict.
- **No need to modify Cloudflare settings** for GA4 to work.
- **Ad blockers** may block gtag.js — this is expected and cannot be avoided on any platform.

### 2.6 GA4 + GitHub Pages

- **No issues.** GA4 works on any static hosting.
- No server-side configuration needed.
- The `localhost` traffic will automatically be filtered out by GA4's built-in "Unfiltered" view (you can also add a "Test" data stream for development).

### 2.7 GDPR / Cookie Consent

**This is the most important consideration.** GA4 uses cookies (including `_ga`, `_gid`, `_gat`) and collects personal data (IP addresses). Under GDPR/ePrivacy, you need **prior consent** before:

1. Storing cookies on EU users' devices
2. Sending data to Google Analytics

**Solution: Cookie Consent Banner (recommended: Cookiebot or Osano)**

Options from simplest to most complete:

#### Option A: Minimal — Cookie Consent Banner (Recommended for launch)
A lightweight consent banner that blocks GA4 until the user accepts. Use a small JS library.

#### Option B: Cookiebot (Industry Standard)
- Free tier for small sites (< 100 pages)
- Auto-scans site for cookies
- Handles GDPR, ePrivacy, CCPA
- Blocks GA4 until consent
- Drop-in script: `<script id="Cookiebot" src="https://consent.cookiebot.com/uc.js" data-cbid="YOUR_ID" type="text/javascript" async></script>`

#### Option C: Self-Hosted Minimal Consent
Write ~20 lines of JS. Shown below in the "Exact Changes" section.

---

## 3. Google AdSense Integration

### 3.1 What You Need (Prerequisites)

1. **Google AdSense account** → Apply at `adsense.google.com`
2. **AdSense approval** → Your site must be reviewed and approved first
3. **Ad Client ID** → Format: `ca-pub-XXXXXXXXXXXXXXXX` (found in AdSense dashboard)
4. **Ad Slot IDs** → Created per ad unit in the AdSense dashboard

### 3.2 AdSense Code Format

AdSense uses two approaches:

#### Option A: Auto Ads (Recommended for Static Sites)
Google automatically places ads in optimal positions. Single snippet in `<head>`:
```html
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX"
     crossorigin="anonymous"></script>
```

#### Option B: Manual Ad Units (More Control)
You place `<ins>` tags at specific positions:
```html
<!-- In <head> -->
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX"
     crossorigin="anonymous"></script>

<!-- At each ad placement location -->
<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
     data-ad-slot="1234567890"
     data-ad-format="auto"
     data-full-width-responsive="true"></ins>
<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
```

### 3.3 AdSense + GitHub Pages Considerations

**Important:** GitHub Pages has [specific restrictions](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages#prohibited-uses) on monetization. However:
- **GitHub Pages allows AdSense** for personal/org sites. The prohibition is on "enterprise" commercial activity, crypto mining, and illegal content.
- Many GitHub Pages sites successfully run AdSense.
- **Custom domain** (`hotspot.edgesoft.org`) avoids any issues with `github.io` domain reputation.

### 3.4 AdSense + Cloudflare Considerations

Cloudflare proxying can potentially cause issues with AdSense:
- **Solution**: Ensure Cloudflare is in **DNS-only mode** for the root domain or configure it properly. Actually, AdSense works fine through Cloudflare proxy — many sites do this.
- **Potential issue**: Cloudflare's Bot Management or WAF might interfere with AdSense crawler. Solution: Allow the `Googlebot` and `Mediapartners-Google` user agents in Cloudflare WAF if you have any custom rules.

### 3.5 AdSense + Dark Mode

AdSense ads do **not** automatically adapt to dark mode. Options:
1. **Default**: AdSense will show light-background ads. On a dark site, these stand out visually.
2. **Manual CSS Fix** (partial): You can try:
   ```css
   .adsbygoogle {
       filter: invert(0.9) hue-rotate(180deg);
   }
   ```
   But this is **against AdSense policies** — you cannot modify ad content/display via CSS.
3. **Best approach**: Accept that ads will have light backgrounds. The site currently has white text on dark backgrounds, so a white-background ad unit naturally contrasts but looks clean.

### 3.6 AdSense Policy Requirements

Critical policies for this site:
1. **Content policy**: Tech news aggregation with AI summaries is fine
2. **No copyrighted content issues**: Since you're linking to sources (not republishing), this is standard aggregation
3. **Navigation requirement**: Users must be able to navigate back (your site has this)
4. **Privacy policy required**: You need one (see GDPR section below)
5. **About page recommended**: Add a brief page or section

### 3.7 Recommended Ad Placement Strategy

For a content-heavy tech news site:

| Position | Format | Size |
|----------|--------|------|
| After header (above first article) | Auto-ads or In-article | Responsive |
| Between sections/categories | Auto-ads | Responsive |
| Below footer | Display ad | 728x90 or responsive |
| In sidebar (if you add one) | Display | 300x250 |

**Recommendation for this site**: Start with **Auto Ads only**. It's the simplest integration, Google's algorithm optimizes placement, and it requires minimal code changes. After a few weeks, review performance and consider manual placements.

---

## 4. Cookie Consent & GDPR Compliance

### 4.1 What You Need

Under GDPR (EU users), ePrivacy Directive (cookie law), and UK DPA:
1. **Cookie consent banner** before any non-essential cookies (GA4, AdSense)
2. **Privacy policy page** explaining what data you collect
3. **Option to withdraw consent**

### 4.2 Recommended Approach: Self-Hosted Minimal Consent

Instead of adding a third-party dependency, use a lightweight consent banner that:
- Blocks GA4 execution until consent
- Stores consent preference in `localStorage` (no additional cookie)
- Injects GA4 script dynamically after consent
- Resets if user clears data

This self-hosted approach is sufficient for a content-focused tech site and avoids adding another third-party dependency.

### 4.3 Privacy Policy Content

Add a `/privacy` page (or `/privacy-policy`). Since this is a static site, create it as a template or static HTML. The privacy policy should cover:
- What data is collected (page views via GA4, ad personalization via AdSense)
- How data is used (analytics, ad placement)
- Cookies used (`_ga`, `_gid`, `_gat` for GA4; AdSense cookies)
- User rights (access, deletion, opt-out)
- Contact information

---

## 5. Exact Code Changes

### 5.1 Changes to `templates/blog.html` (The Main Template)

#### Change 1: Add GA4 and AdSense to `<head>` (with cookie consent blocking)

After line 6 (`<meta name="viewport" ...>`), BEFORE the `<title>` tag or between `<head>` tags:

```html
    <!-- Google AdSense -->
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX"
         crossorigin="anonymous" id="adsense-script"></script>

    <!-- Google tag (gtag.js) - GA4 - loaded only after cookie consent -->
    <script id="ga4-init-script">
        window.dataLayer = window.dataLayer || [];
        function gtag(){dataLayer.push(arguments);}
    </script>
```

#### Change 2: Add cookie consent banner and GA4 loader before `</body>`

Before the closing `</body>` tag (line 943), add:

```html
    <!-- Cookie Consent Banner -->
    <div id="cookieConsent" style="display:none; position:fixed; bottom:0; left:0; right:0; z-index:9999; background:var(--surface); border-top:1px solid var(--border); padding:16px 24px; font-size:14px;">
        <div style="max-width:900px; margin:0 auto; display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;">
            <span style="color:var(--text-secondary);">This site uses cookies from Google for analytics and ads. <a href="privacy-policy.html" style="color:var(--accent);">Learn more</a>.</span>
            <div style="display:flex; gap:8px; flex-shrink:0;">
                <button onclick="declineCookies()" style="padding:8px 16px; border:1px solid var(--border); border-radius:8px; background:var(--surface-2); color:var(--text); cursor:pointer; font-size:13px; font-family:inherit;">Decline</button>
                <button onclick="acceptCookies()" style="padding:8px 16px; border:none; border-radius:8px; background:var(--accent); color:white; cursor:pointer; font-size:13px; font-weight:600; font-family:inherit;">Accept</button>
            </div>
        </div>
    </div>

    <script>
    // ── Cookie Consent & GA4 Loader ──
    (function() {
        var COOKIE_KEY = 'cookie_consent';
        var GA_ID = 'G-XXXXXXXXXX'; // REPLACE WITH YOUR MEASUREMENT ID

        function getConsent() {
            try {
                return localStorage.getItem(COOKIE_KEY);
            } catch(e) { return null; }
        }

        function setConsent(value) {
            try { localStorage.setItem(COOKIE_KEY, value); } catch(e) {}
        }

        function loadGA4() {
            if (window._gaLoaded) return;
            window._gaLoaded = true;

            // Set consent defaults for gtag
            gtag('consent', 'default', {
                'analytics_storage': 'granted',
                'ad_storage': 'granted',
                'ad_user_data': 'granted',
                'ad_personalization': 'granted'
            });

            // Load gtag.js
            var gaScript = document.createElement('script');
            gaScript.async = true;
            gaScript.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
            document.head.appendChild(gaScript);

            // Configure GA4 after script loads
            gaScript.onload = function() {
                gtag('js', new Date());
                gtag('config', GA_ID, {
                    'anonymize_ip': true,
                    'cookie_flags': 'SameSite=None;Secure'
                });
            };
        }

        function unloadGA4() {
            // Remove GA cookies by expiring them
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.indexOf('_ga') === 0 || cookie.indexOf('_gid') === 0 || cookie.indexOf('_gat') === 0) {
                    document.cookie = cookie.split('=')[0] + '=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                }
            }
            gtag('consent', 'update', {
                'analytics_storage': 'denied',
                'ad_storage': 'denied',
                'ad_user_data': 'denied',
                'ad_personalization': 'denied'
            });
        }

        window.acceptCookies = function() {
            setConsent('accepted');
            document.getElementById('cookieConsent').style.display = 'none';
            loadGA4();
            // Enable AdSense (re-enable ads by pushing)
            try {
                (adsbygoogle = window.adsbygoogle || []).push({});
            } catch(e) {}
        };

        window.declineCookies = function() {
            setConsent('declined');
            document.getElementById('cookieConsent').style.display = 'none';
            unloadGA4();
            // Disable AdSense by removing script
            var adScript = document.getElementById('adsense-script');
            if (adScript) adScript.remove();
        };

        // On page load, check consent
        var consent = getConsent();
        if (consent === 'accepted') {
            loadGA4();
            // AdSense should already be active from the head script
        } else if (consent === 'declined') {
            // Remove AdSense, don't load GA4
            var adScript = document.getElementById('adsense-script');
            if (adScript) adScript.remove();
        } else {
            // Show consent banner
            document.getElementById('cookieConsent').style.display = '';
            // Block AdSense until consent
            var adScript = document.getElementById('adsense-script');
            if (adScript) adScript.remove();
        }
    })();
    </script>
```

#### Change 3: Optional — Add manual ad placement in content area

Between sections (e.g., after the trend analysis panel and before the first category), add inside the `<div id="contentArea">`:

```html
<!-- In-content Ad -->
<div class="ad-container" style="margin: 24px 0; text-align:center;">
    <ins class="adsbygoogle"
         style="display:block"
         data-ad-client="ca-pub-XXXXXXXXXXXXXXXX"
         data-ad-slot="YYYYYYYYYY"
         data-ad-format="auto"
         data-full-width-responsive="true"></ins>
    <script>(adsbygoogle = window.adsbygoogle || []).push({});</script>
</div>
```

### 5.2 Changes to `config.yaml`

Add GA4 and AdSense configuration for the blog generator:

```yaml
# =============================================================================
# Analytics & Ads Configuration
# =============================================================================
analytics:
  google_analytics_id: "G-XXXXXXXXXX"  # Your GA4 measurement ID
  google_adsense_id: "ca-pub-XXXXXXXXXXXXXXXX"  # Your AdSense publisher ID
  # Cookie consent: "self-hosted" (simple banner), "cookiebot" (professional)
  cookie_consent: "self-hosted"  
```

### 5.3 Changes to `publishers/blog_generator.py`

Pass analytics config to the template context. In the `generate()` method, add to the `data` dict (around line 161):

```python
# Analytics & Ads config
analytics_config = self.config.get("analytics", {})
data.update({
    "ga_measurement_id": analytics_config.get("google_analytics_id", ""),
    "adsense_client_id": analytics_config.get("google_adsense_id", ""),
    "cookie_consent_mode": analytics_config.get("cookie_consent", "self-hosted"),
})
```

### 5.4 Create `templates/privacy-policy.html`

Create a new static privacy policy page:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy — Tech Hotspot Daily</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0a0a0f;
            --surface: #12121a;
            --surface-2: #1a1a25;
            --border: #252535;
            --text: #e2e2f0;
            --text-secondary: #8b8ba7;
            --accent: #6366f1;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            min-height: 100vh;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 48px 24px;
        }
        h1 { font-size: 32px; font-weight: 700; margin-bottom: 8px; }
        .date { color: var(--text-secondary); font-size: 14px; margin-bottom: 32px; }
        h2 { font-size: 20px; font-weight: 600; margin: 32px 0 12px; color: var(--accent); }
        h3 { font-size: 16px; font-weight: 600; margin: 24px 0 8px; }
        p, li { color: var(--text-secondary); font-size: 15px; margin-bottom: 12px; }
        ul { padding-left: 24px; margin-bottom: 16px; }
        li { margin-bottom: 6px; }
        a { color: var(--accent); text-decoration: none; }
        a:hover { text-decoration: underline; }
        hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
        .back-link {
            display: inline-block; margin-top: 24px;
            color: var(--accent); text-decoration: none; font-size: 14px;
        }
        .back-link:hover { text-decoration: underline; }
        @media (max-width: 640px) {
            .container { padding: 32px 16px; }
            h1 { font-size: 24px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Privacy Policy</h1>
        <p class="date">Last updated: May 2026</p>

        <h2>Information We Collect</h2>
        <p><strong>Tech Hotspot Daily</strong> ("we", "our", "us") operates the website <a href="index.html">hotspot.edgesoft.org</a> (the "Site"). This page explains how we handle your data.</p>

        <h3>Google Analytics 4</h3>
        <p>We use Google Analytics 4 (GA4) to understand how visitors use our site. GA4 may collect:</p>
        <ul>
            <li>Pages visited and time spent on each page</li>
            <li>Browser type, device type, operating system</li>
            <li>Approximate geographic location (city-level)</li>
            <li>Referring website or campaign</li>
        </ul>
        <p>GA4 uses cookies (<code>_ga</code>, <code>_gid</code>, <code>_gat</code>) to distinguish users. We have enabled IP anonymization. No personally identifiable information is collected through GA4.</p>

        <h3>Google AdSense</h3>
        <p>We use Google AdSense to serve advertisements. AdSense uses cookies and web beacons to:</p>
        <ul>
            <li>Serve relevant ads based on your browsing history</li>
            <li>Limit how often you see an ad</li>
            <li>Measure ad effectiveness</li>
        </ul>
        <p>AdSense may collect data including: IP address, browser type, device type, and interaction with ads.</p>

        <h3>Newsletter Subscription</h3>
        <p>If you subscribe to our email newsletter, we collect and store your email address. We use Resend.com as our email service provider. You can unsubscribe at any time using the link in every email.</p>

        <h2>Your Rights (GDPR)</h2>
        <p>If you are in the European Economic Area (EEA), you have the right to:</p>
        <ul>
            <li><strong>Access</strong>: Request a copy of data we hold about you</li>
            <li><strong>Rectification</strong>: Correct inaccurate data</li>
            <li><strong>Erasure</strong>: Request deletion of your data</li>
            <li><strong>Object</strong>: Object to processing of your data</li>
            <li><strong>Portability</strong>: Receive your data in a machine-readable format</li>
        </ul>
        <p>To exercise these rights, contact us at the email address below.</p>

        <h2>Cookies</h2>
        <p>We use the following types of cookies:</p>
        <ul>
            <li><strong>Analytics cookies</strong> (GA4): Used to analyze site traffic and usage patterns</li>
            <li><strong>Advertising cookies</strong> (AdSense): Used to personalize ads and measure their effectiveness</li>
        </ul>
        <p>You can manage cookie preferences via the cookie consent banner that appears on your first visit. You may also disable cookies in your browser settings.</p>

        <h2>Data Sharing</h2>
        <p>We do not sell your personal data. Data is shared with:</p>
        <ul>
            <li><strong>Google LLC</strong> (GA4 and AdSense) — see <a href="https://policies.google.com/privacy" target="_blank">Google's Privacy Policy</a></li>
            <li><strong>Resend.com</strong> (Newsletter delivery) — see <a href="https://resend.com/legal/privacy-policy" target="_blank">Resend's Privacy Policy</a></li>
        </ul>

        <h2>Contact</h2>
        <p>For privacy-related inquiries: <a href="mailto:privacy@edgesoft.org">privacy@edgesoft.org</a></p>

        <hr>
        <a href="index.html" class="back-link">← Back to Daily Report</a>
    </div>
</body>
</html>
```

Then update `blog_generator.py` to copy this to `docs/privacy-policy.html` alongside the other static pages.

### 5.5 Changes to `.github/workflows/daily.yml`

No changes needed to the CI/CD workflow. GA4 and AdSense are entirely client-side and don't require any build-time changes.

---

## 6. Setup Steps (Implementation Order)

### Phase 1: Google Account Setup (10 minutes)
1. Create GA4 property at `analytics.google.com`
2. Create AdSense account at `adsense.google.com`
3. Get your Measurement ID (`G-XXXXXXXXXX`) and Ad Client ID (`ca-pub-XXXXXXXXXXXXXXXX`)
4. Submit site for AdSense approval (may take 1-2 weeks)

### Phase 2: Code Changes (< 30 minutes)
5. Add `analytics:` section to `config.yaml`
6. Update `blog_generator.py` to pass analytics config to templates
7. Add GA4 + AdSense scripts to `templates/blog.html` with cookie consent
8. Create `templates/privacy-policy.html`
9. Update `blog_generator.py` to copy privacy-policy.html
10. Run `python publishers/blog_generator.py` to regenerate `docs/index.html`

### Phase 3: Verification (15 minutes)
11. Open the site and verify GA4 snippet loads
12. Check Google Analytics Realtime report for your visit
13. Verify cookie consent banner appears for new visitors
14. Test "Accept" and "Decline" flows
15. Confirm privacy-policy.html is accessible

### Phase 4: AdSense Approval Follow-up
16. Once AdSense is approved, verify ads appear on the site
17. Consider adding manual ad placements after Auto Ads have been running for 2 weeks

---

## 7. Maintenance & Monitoring

- **GA4**: Monitor in Google Analytics dashboard. Key metrics: page views, sessions, bounce rate, top pages.
- **AdSense**: Monitor in AdSense dashboard. Review ad performance, earnings, and page RPM.
- **Cookie consent**: Review annually for changes in GDPR/ePrivacy regulations.
- **Ad blockers**: Ad blockers will block both GA4 and AdSense. This is normal and affects all sites.

---

## 8. Appendix: Jinja2 Template Variables

After implementing, the following template variables will be available in `blog.html`:

| Variable | Type | Description |
|----------|------|-------------|
| `{{ ga_measurement_id }}` | string | GA4 measurement ID (e.g., `G-XXXXXXXXXX`) |
| `{{ adsense_client_id }}` | string | AdSense client ID (e.g., `ca-pub-XXXXXXXXXXXXXXXX`) |
| `{{ cookie_consent_mode }}` | string | Consent mode (`self-hosted`, `cookiebot`) |

These should be used in the template to inject the correct IDs rather than hardcoding them, making the site easily configurable across environments.
